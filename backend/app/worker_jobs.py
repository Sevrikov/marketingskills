from sqlalchemy.orm import Session

from app.adapters.factory import build_llm_adapter, build_research_adapter, build_source_provider
from app.adapters.llm import LLMAdapter
from app.adapters.research import ResearchAdapter
from app.adapters.source_provider import SourceProvider
from app.db.session import SessionLocal
from app.models.content_task import ContentTaskStatus
from app.schemas.content_task import ContentTaskStatusUpdate
from app.services.content_tasks import (
    get_content_task,
    log_task_event,
    update_content_task_status,
)
from app.services.article_review_checkpoints import format_article_checkpoint_context
from app.services.content_research import get_latest_research_markdown, run_task_research
from app.services.draft_generation import (
    PROMPT_BY_TASK_TYPE,
    MissingPromptTemplate,
    generate_critique,
    generate_initial_draft,
    generate_rewrite,
)
from app.services.prompt_templates import get_active_prompt_template_by_key
from app.services.runtime_settings import effective_settings


def process_content_task(task_id: str) -> None:
    db = SessionLocal()
    try:
        _process_content_task(db, task_id)
    finally:
        db.close()


def _process_content_task(
    db: Session,
    task_id: str,
    llm_adapter: LLMAdapter | None = None,
    research_adapter: ResearchAdapter | None = None,
    source_provider: SourceProvider | None = None,
) -> None:
    task = get_content_task(db, task_id)
    if task is None:
        return

    settings = effective_settings(db)
    llm_adapter = llm_adapter or build_llm_adapter(settings)
    research_adapter = research_adapter or build_research_adapter(settings)
    source_provider = source_provider or build_source_provider(settings)

    log_task_event(
        db,
        task,
        event_type="worker_started",
        from_status=task.status,
        to_status=task.status,
        step="worker_started",
        message="Worker started processing task.",
    )
    db.commit()

    if task.status == ContentTaskStatus.QUEUED.value:
        try:
            _run_draft_pipeline(db, task.id, llm_adapter, research_adapter, source_provider)
        except Exception as exc:
            task = get_content_task(db, task_id)
            if task is not None and task.status != ContentTaskStatus.FAILED.value:
                update_content_task_status(
                    db,
                    task,
                    ContentTaskStatusUpdate(
                        status=ContentTaskStatus.FAILED,
                        current_step="draft_pipeline_failed",
                        error_message=str(exc),
                    ),
                )
            raise

    task = get_content_task(db, task_id)
    if task is None:
        return
    log_task_event(
        db,
        task,
        event_type="worker_completed",
        from_status=task.status,
        to_status=task.status,
        step="worker_completed",
        message="Worker completed processing task.",
    )
    db.commit()


def _run_draft_pipeline(
    db: Session,
    task_id: str,
    llm_adapter: LLMAdapter,
    research_adapter: ResearchAdapter,
    source_provider: SourceProvider,
) -> None:
    task = get_content_task(db, task_id)
    if task is None:
        return

    task = update_content_task_status(
        db,
        task,
        ContentTaskStatusUpdate(
            status=ContentTaskStatus.RESEARCH_RUNNING,
            current_step="marketing_research",
        ),
    )
    run_task_research(db, task, research_adapter, source_provider)
    db.commit()

    task = update_content_task_status(
        db,
        task,
        ContentTaskStatusUpdate(
            status=ContentTaskStatus.RESEARCH_COMPLETED,
            current_step="research_completed",
        ),
    )
    research_markdown = get_latest_research_markdown(db, task.id)
    article_checkpoint_context = format_article_checkpoint_context(db, task.id)

    draft_prompt_key = PROMPT_BY_TASK_TYPE.get(task.task_type)
    draft_prompt = (
        get_active_prompt_template_by_key(db, draft_prompt_key) if draft_prompt_key else None
    )
    critic_prompt = get_active_prompt_template_by_key(db, "ecommerce.content_critic.v1")
    rewrite_prompt = get_active_prompt_template_by_key(db, "ecommerce.rewriter.v1")
    if draft_prompt is None:
        raise MissingPromptTemplate(f"No active draft prompt for task type {task.task_type}.")
    if critic_prompt is None:
        raise MissingPromptTemplate("No active critic prompt found.")
    if rewrite_prompt is None:
        raise MissingPromptTemplate("No active rewrite prompt found.")

    task = update_content_task_status(
        db,
        task,
        ContentTaskStatusUpdate(
            status=ContentTaskStatus.CONTENT_GENERATING,
            current_step="initial_draft",
        ),
    )
    draft_response = generate_initial_draft(
        db,
        task,
        draft_prompt,
        llm_adapter,
        research_report=research_markdown,
        article_checkpoint_context=article_checkpoint_context,
    )
    db.commit()

    task = update_content_task_status(
        db,
        task,
        ContentTaskStatusUpdate(
            status=ContentTaskStatus.CRITICIZING,
            current_step="draft_critique",
        ),
    )
    critique_response = generate_critique(db, task, critic_prompt, llm_adapter, draft_response.text)
    db.commit()

    task = update_content_task_status(
        db,
        task,
        ContentTaskStatusUpdate(
            status=ContentTaskStatus.REWRITING,
            current_step="final_rewrite",
        ),
    )
    generate_rewrite(
        db,
        task,
        rewrite_prompt,
        llm_adapter,
        draft=draft_response.text,
        critique=critique_response.text,
        article_checkpoint_context=article_checkpoint_context,
    )
    db.commit()

    update_content_task_status(
        db,
        task,
        ContentTaskStatusUpdate(
            status=ContentTaskStatus.WAITING_APPROVAL,
            current_step="waiting_approval",
        ),
    )
