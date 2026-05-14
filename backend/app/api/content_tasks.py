from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.adapters.cms import CMSAdapter
from app.adapters.factory import (
    build_cms_adapter,
    build_image_generation_adapter,
    build_llm_adapter,
    build_notification_adapter,
)
from app.adapters.gemini import GeminiConfigurationError
from app.adapters.image_generation import ImageGenerationAdapter
from app.adapters.llm import LLMAdapter
from app.adapters.notifications import NotificationAdapter
from app.config import Settings, get_settings
from app.db.session import get_db
from app.queue.base import TaskQueue
from app.queue.factory import build_task_queue
from app.schemas.approval import ApprovalPayload, ApprovalResult
from app.schemas.article_asset import (
    ArticleAssetGeneratePayload,
    ArticleAssetRead,
    ArticleAssetStatusUpdate,
    ArticleAssetUploadPayload,
)
from app.schemas.article_review_checkpoint import ArticleCheckpointRead, ArticleCheckpointUpsert
from app.schemas.content_task import (
    ContentTaskCreate,
    ContentTaskRead,
    ContentTaskStatusUpdate,
)
from app.schemas.content_draft import ContentDraftRead, DraftVersionDecisionPayload
from app.schemas.content_research_report import ContentResearchReportRead
from app.schemas.media_brief import MediaBriefRead
from app.schemas.publish_package import PublishPackageRead
from app.schemas.notification import ApprovalNotificationResult, NotificationDeliveryRead
from app.schemas.publication_preview import PublicationPreviewRead
from app.schemas.publication_preview import PublicationPublishRequest
from app.schemas.task_event import TaskEventRead
from app.services.approvals import TaskNotReadyForApproval, approve_task, request_task_rewrite
from app.services.article_assets import (
    MissingArticleAssetSlots,
    MissingArticleDraftForAssets,
    attach_article_asset_upload,
    generate_article_asset_image,
    generate_article_assets,
    get_article_asset,
    list_article_assets,
    update_article_asset_status,
)
from app.services.article_review_checkpoints import (
    delete_article_checkpoint,
    list_article_checkpoints,
    upsert_article_checkpoint,
)
from app.services.article_rewrites import (
    ArticleRewriteNotReady,
    MissingArticleCheckpointContext,
    MissingRewriteSourceDraft,
    rewrite_from_article_checkpoints,
)
from app.services.content_drafts import (
    get_content_draft,
    list_content_drafts,
    set_draft_version_decision,
)
from app.services.content_research import list_content_research_reports
from app.services.content_tasks import (
    InvalidTaskTransition,
    create_content_task,
    get_content_task,
    list_task_events,
    list_content_tasks,
    update_content_task_status,
)
from app.services.publish_packages import (
    MissingFinalDraft,
    TaskNotApprovedForExport,
    export_publish_package,
    get_publish_package,
    list_publish_packages,
)
from app.services.publication_previews import (
    CMSProviderMismatch,
    PackageNotReadyForPublication,
    PublicationConfirmationRequired,
    PublicationPreviewNotReady,
    RealPublishingDisabled,
    create_publication_preview,
    get_publication_preview,
    list_publication_previews,
    publish_publication_preview,
)
from app.services.media_briefs import (
    PackageNotReadyForMediaBrief,
    create_media_brief,
    list_media_briefs,
)
from app.services.draft_generation import MissingPromptTemplate
from app.services.notifications import TaskNotReadyForNotification, send_approval_notification
from app.services.runtime_settings import effective_settings
from app.models.article_review_checkpoint import ArticleCheckpointType
from app.models.content_task import ContentTaskStatus

router = APIRouter(prefix="/api/tasks", tags=["content tasks"])


def get_task_queue() -> TaskQueue:
    return build_task_queue(get_settings())


def get_notification_adapter() -> NotificationAdapter:
    return build_notification_adapter(get_settings())


def get_cms_adapter() -> CMSAdapter:
    return build_cms_adapter(get_settings())


def get_llm_adapter() -> LLMAdapter:
    return build_llm_adapter(get_settings())


def get_image_generation_adapter() -> ImageGenerationAdapter:
    return build_image_generation_adapter(get_settings())


def get_effective_notification_adapter(db: Session = Depends(get_db)) -> NotificationAdapter:
    return build_notification_adapter(effective_settings(db))


def get_effective_cms_adapter(db: Session = Depends(get_db)) -> CMSAdapter:
    return build_cms_adapter(effective_settings(db))


def get_effective_llm_adapter(db: Session = Depends(get_db)) -> LLMAdapter:
    return build_llm_adapter(effective_settings(db))


def get_effective_image_generation_adapter(db: Session = Depends(get_db)) -> ImageGenerationAdapter:
    return build_image_generation_adapter(effective_settings(db))


def get_effective_settings(
    db: Session = Depends(get_db),
    base_settings: Settings = Depends(get_settings),
) -> Settings:
    return effective_settings(db, base=base_settings)


@router.post("", response_model=ContentTaskRead, status_code=status.HTTP_201_CREATED)
def create_task_endpoint(payload: ContentTaskCreate, db: Session = Depends(get_db)):
    return create_content_task(db, payload)


@router.get("", response_model=list[ContentTaskRead])
def list_tasks_endpoint(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return list_content_tasks(db, limit=limit, offset=offset)


@router.get("/{task_id}", response_model=ContentTaskRead)
def get_task_endpoint(task_id: str, db: Session = Depends(get_db)):
    task = get_content_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.get("/{task_id}/events", response_model=list[TaskEventRead])
def list_task_events_endpoint(task_id: str, db: Session = Depends(get_db)):
    task = get_content_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return list_task_events(db, task_id)


@router.get("/{task_id}/drafts", response_model=list[ContentDraftRead])
def list_task_drafts_endpoint(task_id: str, db: Session = Depends(get_db)):
    task = get_content_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return list_content_drafts(db, task_id)


@router.post("/{task_id}/drafts/{draft_id}/version-decision", response_model=ContentDraftRead)
def set_task_draft_version_decision_endpoint(
    task_id: str,
    draft_id: str,
    payload: DraftVersionDecisionPayload,
    db: Session = Depends(get_db),
):
    task = get_content_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    draft = get_content_draft(db, draft_id)
    if draft is None or draft.task_id != task.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    if draft.kind != "final":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only final drafts can receive version decisions.",
        )
    return set_draft_version_decision(db, task, draft, payload)


@router.get("/{task_id}/research", response_model=list[ContentResearchReportRead])
def list_task_research_endpoint(task_id: str, db: Session = Depends(get_db)):
    task = get_content_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return list_content_research_reports(db, task_id)


@router.get("/{task_id}/packages", response_model=list[PublishPackageRead])
def list_task_packages_endpoint(task_id: str, db: Session = Depends(get_db)):
    task = get_content_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return list_publish_packages(db, task_id)


@router.get("/{task_id}/article-checkpoints", response_model=list[ArticleCheckpointRead])
def list_task_article_checkpoints_endpoint(task_id: str, db: Session = Depends(get_db)):
    task = get_content_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return list_article_checkpoints(db, task_id)


@router.put(
    "/{task_id}/article-checkpoints/{checkpoint_type}",
    response_model=ArticleCheckpointRead,
)
def upsert_task_article_checkpoint_endpoint(
    task_id: str,
    checkpoint_type: ArticleCheckpointType,
    payload: ArticleCheckpointUpsert,
    db: Session = Depends(get_db),
):
    task = get_content_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return upsert_article_checkpoint(db, task, checkpoint_type, payload)


@router.delete("/{task_id}/article-checkpoints/{checkpoint_type}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task_article_checkpoint_endpoint(
    task_id: str,
    checkpoint_type: ArticleCheckpointType,
    db: Session = Depends(get_db),
):
    task = get_content_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    delete_article_checkpoint(db, task, checkpoint_type)
    return None


@router.get("/{task_id}/article-assets", response_model=list[ArticleAssetRead])
def list_task_article_assets_endpoint(task_id: str, db: Session = Depends(get_db)):
    task = get_content_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return list_article_assets(db, task_id)


@router.post("/{task_id}/article-assets/generate", response_model=list[ArticleAssetRead])
def generate_task_article_assets_endpoint(task_id: str, db: Session = Depends(get_db)):
    task = get_content_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    try:
        return generate_article_assets(db, task)
    except (MissingArticleDraftForAssets, MissingArticleAssetSlots) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/{task_id}/article-assets/{asset_id}/status", response_model=ArticleAssetRead)
def update_task_article_asset_status_endpoint(
    task_id: str,
    asset_id: str,
    payload: ArticleAssetStatusUpdate,
    db: Session = Depends(get_db),
):
    task = get_content_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    asset = get_article_asset(db, asset_id)
    if asset is None or asset.task_id != task.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article asset not found")
    return update_article_asset_status(db, task, asset, payload)


@router.post("/{task_id}/article-assets/{asset_id}/upload", response_model=ArticleAssetRead)
def upload_task_article_asset_endpoint(
    task_id: str,
    asset_id: str,
    payload: ArticleAssetUploadPayload,
    db: Session = Depends(get_db),
):
    task = get_content_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    asset = get_article_asset(db, asset_id)
    if asset is None or asset.task_id != task.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article asset not found")
    return attach_article_asset_upload(db, task, asset, payload)


@router.post("/{task_id}/article-assets/{asset_id}/generate-image", response_model=ArticleAssetRead)
def generate_task_article_asset_image_endpoint(
    task_id: str,
    asset_id: str,
    payload: ArticleAssetGeneratePayload,
    db: Session = Depends(get_db),
    adapter: ImageGenerationAdapter = Depends(get_effective_image_generation_adapter),
):
    task = get_content_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    asset = get_article_asset(db, asset_id)
    if asset is None or asset.task_id != task.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article asset not found")
    try:
        return generate_article_asset_image(db, task, asset, payload, adapter)
    except GeminiConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/{task_id}/rewrite-from-checkpoints", response_model=ContentDraftRead)
def rewrite_task_from_checkpoints_endpoint(
    task_id: str,
    db: Session = Depends(get_db),
    adapter: LLMAdapter = Depends(get_effective_llm_adapter),
):
    task = get_content_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    try:
        return rewrite_from_article_checkpoints(db, task, adapter)
    except (
        ArticleRewriteNotReady,
        MissingArticleCheckpointContext,
        MissingRewriteSourceDraft,
        MissingPromptTemplate,
        InvalidTaskTransition,
    ) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/{task_id}/export-package", response_model=PublishPackageRead)
def export_task_package_endpoint(task_id: str, db: Session = Depends(get_db)):
    task = get_content_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    try:
        return export_publish_package(db, task)
    except (TaskNotApprovedForExport, MissingFinalDraft) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/{task_id}/notify-approval", response_model=ApprovalNotificationResult)
def notify_task_approval_endpoint(
    task_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_effective_settings),
    adapter: NotificationAdapter = Depends(get_effective_notification_adapter),
):
    task = get_content_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    try:
        deliveries = send_approval_notification(db, task, adapter, settings)
    except TaskNotReadyForNotification as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return ApprovalNotificationResult(
        task_id=task.id,
        provider=adapter.provider,
        channel=deliveries[0].channel if deliveries else "unknown",
        deliveries=[
            NotificationDeliveryRead(
                provider=delivery.provider,
                channel=delivery.channel,
                status=delivery.status,
                recipient=delivery.recipient,
                message_id=delivery.message_id,
                metadata=delivery.metadata,
            )
            for delivery in deliveries
        ],
    )


@router.get("/packages/{package_id}/publication-previews", response_model=list[PublicationPreviewRead])
def list_package_publication_previews_endpoint(
    package_id: str,
    db: Session = Depends(get_db),
):
    package = get_publish_package(db, package_id)
    if package is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
    return list_publication_previews(db, package_id)


@router.post("/packages/{package_id}/publication-preview", response_model=PublicationPreviewRead)
def create_package_publication_preview_endpoint(
    package_id: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_effective_settings),
    adapter: CMSAdapter = Depends(get_effective_cms_adapter),
):
    package = get_publish_package(db, package_id)
    if package is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
    try:
        return create_publication_preview(db, package, adapter, settings)
    except PackageNotReadyForPublication as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/publication-previews/{preview_id}/publish",
    response_model=PublicationPreviewRead,
)
def publish_publication_preview_endpoint(
    preview_id: str,
    payload: PublicationPublishRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_effective_settings),
    adapter: CMSAdapter = Depends(get_effective_cms_adapter),
):
    preview = get_publication_preview(db, preview_id)
    if preview is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication preview not found",
        )
    try:
        return publish_publication_preview(
            db,
            preview,
            adapter,
            settings,
            confirmation_phrase=payload.confirmation_phrase,
        )
    except (
        CMSProviderMismatch,
        PublicationConfirmationRequired,
        PublicationPreviewNotReady,
        RealPublishingDisabled,
    ) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/packages/{package_id}/media-briefs", response_model=list[MediaBriefRead])
def list_package_media_briefs_endpoint(
    package_id: str,
    db: Session = Depends(get_db),
):
    package = get_publish_package(db, package_id)
    if package is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
    return list_media_briefs(db, package_id)


@router.post("/packages/{package_id}/media-brief", response_model=MediaBriefRead)
def create_package_media_brief_endpoint(
    package_id: str,
    db: Session = Depends(get_db),
):
    package = get_publish_package(db, package_id)
    if package is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Package not found")
    try:
        return create_media_brief(db, package)
    except PackageNotReadyForMediaBrief as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/{task_id}/status", response_model=ContentTaskRead)
def update_task_status_endpoint(
    task_id: str,
    payload: ContentTaskStatusUpdate,
    db: Session = Depends(get_db),
):
    task = get_content_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    try:
        return update_content_task_status(db, task, payload)
    except InvalidTaskTransition as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/{task_id}/enqueue")
def enqueue_task_endpoint(
    task_id: str,
    db: Session = Depends(get_db),
    queue: TaskQueue = Depends(get_task_queue),
):
    task = get_content_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if task.status == ContentTaskStatus.DRAFT.value:
        try:
            task = update_content_task_status(
                db,
                task,
                ContentTaskStatusUpdate(
                    status=ContentTaskStatus.QUEUED,
                    current_step="queued",
                ),
            )
        except InvalidTaskTransition as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if task.status != ContentTaskStatus.QUEUED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only draft or queued tasks can be enqueued. Current status: {task.status}.",
        )

    job = queue.enqueue_content_task(task.id)
    return {
        "task_id": task.id,
        "job_id": job.id,
        "queue": job.queue_name,
        "status": task.status,
    }


@router.post("/{task_id}/approve", response_model=ApprovalResult)
def approve_task_endpoint(
    task_id: str,
    payload: ApprovalPayload,
    db: Session = Depends(get_db),
):
    task = get_content_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    try:
        approved_task = approve_task(db, task, payload)
    except TaskNotReadyForApproval as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidTaskTransition as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ApprovalResult(
        task_id=approved_task.id,
        status=approved_task.status,
        decision="approved",
        reviewer=payload.reviewer,
    )


@router.post("/{task_id}/request-rewrite", response_model=ApprovalResult)
def request_rewrite_endpoint(
    task_id: str,
    payload: ApprovalPayload,
    db: Session = Depends(get_db),
):
    task = get_content_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    try:
        rewritten_task = request_task_rewrite(db, task, payload)
    except TaskNotReadyForApproval as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidTaskTransition as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ApprovalResult(
        task_id=rewritten_task.id,
        status=rewritten_task.status,
        decision="rewrite_requested",
        reviewer=payload.reviewer,
    )
