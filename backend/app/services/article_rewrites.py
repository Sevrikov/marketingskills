from sqlalchemy.orm import Session

from app.adapters.llm import LLMAdapter
from app.models.content_draft import ContentDraft
from app.models.content_task import ContentTask, ContentTaskStatus
from app.schemas.content_task import ContentTaskStatusUpdate
from app.services.article_review_checkpoints import format_article_checkpoint_context
from app.services.content_drafts import list_content_drafts
from app.services.content_tasks import (
    log_task_event,
    update_content_task_status,
)
from app.services.draft_generation import MissingPromptTemplate, generate_rewrite
from app.services.prompt_templates import get_active_prompt_template_by_key


class ArticleRewriteNotReady(ValueError):
    pass


class MissingArticleCheckpointContext(ValueError):
    pass


class MissingRewriteSourceDraft(ValueError):
    pass


def rewrite_from_article_checkpoints(
    db: Session,
    task: ContentTask,
    llm_adapter: LLMAdapter,
) -> ContentDraft:
    if task.status != ContentTaskStatus.WAITING_APPROVAL.value:
        raise ArticleRewriteNotReady(
            f"Task must be waiting_approval, current status is {task.status}."
        )

    drafts = list_content_drafts(db, task.id)
    source_draft = _latest_draft_by_kind(drafts, "final") or _latest_draft_by_kind(drafts, "initial")
    if source_draft is None:
        raise MissingRewriteSourceDraft("Task has no draft to rewrite.")

    checkpoint_context = format_article_checkpoint_context(db, task.id)
    if not checkpoint_context.strip():
        raise MissingArticleCheckpointContext("Task has no Article Studio checkpoints to apply.")

    rewrite_prompt = get_active_prompt_template_by_key(db, "ecommerce.rewriter.v1")
    if rewrite_prompt is None:
        raise MissingPromptTemplate("No active rewrite prompt found.")

    critique = _latest_draft_by_kind(drafts, "critique")
    critique_text = (
        critique.body
        if critique is not None
        else "Apply the Article Studio checkpoints and keep all supported facts intact."
    )

    task = update_content_task_status(
        db,
        task,
        ContentTaskStatusUpdate(
            status=ContentTaskStatus.REWRITING,
            current_step="article_studio_rewrite",
        ),
    )
    generate_rewrite(
        db,
        task,
        rewrite_prompt,
        llm_adapter,
        draft=source_draft.body,
        critique=critique_text,
        article_checkpoint_context=checkpoint_context,
    )
    new_draft = _latest_draft_by_kind(list_content_drafts(db, task.id), "final")
    if new_draft is None:
        raise MissingRewriteSourceDraft("Rewrite did not produce a final draft.")

    log_task_event(
        db,
        task,
        event_type="article_studio_rewrite_generated",
        from_status=task.status,
        to_status=task.status,
        step="article_studio_rewrite",
        message="Article Studio rewrite generated from saved checkpoints.",
        metadata_json={
            "source_draft_id": source_draft.id,
            "new_draft_id": new_draft.id,
        },
    )
    db.commit()
    db.refresh(new_draft)

    update_content_task_status(
        db,
        task,
        ContentTaskStatusUpdate(
            status=ContentTaskStatus.WAITING_APPROVAL,
            current_step="article_studio_rewrite_ready",
        ),
    )
    return new_draft


def _latest_draft_by_kind(drafts: list[ContentDraft], kind: str) -> ContentDraft | None:
    matching = [draft for draft in drafts if draft.kind == kind]
    return matching[-1] if matching else None
