from string import Formatter

from sqlalchemy.orm import Session

from app.adapters.llm import LLMAdapter, LLMRequest, LLMResponse
from app.models.agent_skill import AgentSkillStatus
from app.models.content_task import ContentTask, ContentTaskType
from app.models.product import Product
from app.models.prompt_template import PromptTemplate
from app.services.content_drafts import create_content_draft
from app.services.skill_registry import list_agent_skills


PROMPT_BY_TASK_TYPE: dict[str, str] = {
    ContentTaskType.PRODUCT_CARD.value: "ecommerce.aeo_product_description.v1",
    ContentTaskType.SEO_ARTICLE.value: "ecommerce.aeo_product_description.v1",
    ContentTaskType.RESEARCH.value: "ecommerce.aeo_product_description.v1",
    ContentTaskType.VIDEO_BRIEF.value: "ecommerce.video_brief.v1",
}


class MissingPromptTemplate(ValueError):
    pass


def generate_initial_draft(
    db: Session,
    task: ContentTask,
    prompt_template: PromptTemplate,
    llm_adapter: LLMAdapter,
    research_report: str,
    article_checkpoint_context: str = "",
) -> LLMResponse:
    product = db.get(Product, task.product_id) if task.product_id else None
    skill_context = _build_skill_context(db)
    variables = _build_prompt_variables(
        task,
        product,
        skill_context,
        research_report,
        article_checkpoint_context,
    )
    rendered_template = render_prompt_template(prompt_template.user_template, variables)
    prompt_parts = [
        f"Active agent skills:\n{skill_context}",
        f"Task prompt:\n{rendered_template}",
    ]
    if article_checkpoint_context:
        prompt_parts.append(f"Article Studio checkpoints:\n{article_checkpoint_context}")
    prompt = "\n\n".join(prompt_parts)
    response = llm_adapter.generate_text(
        LLMRequest(
            system_prompt=prompt_template.system_prompt,
            prompt=prompt,
            model=prompt_template.model,
            metadata={
                "task_id": task.id,
                "task_type": task.task_type,
                "prompt_template_key": prompt_template.key,
                "skills": variables["skills_used"],
            },
        )
    )
    create_content_draft(
        db,
        task,
        kind="initial",
        body=response.text,
        provider=response.provider,
        model=response.model,
        prompt_template=prompt_template,
        title=_draft_title(task, product),
        metadata_json={"skills_used": variables["skills_used"]},
    )
    return response


def generate_critique(
    db: Session,
    task: ContentTask,
    prompt_template: PromptTemplate,
    llm_adapter: LLMAdapter,
    draft: str,
) -> LLMResponse:
    prompt = render_prompt_template(prompt_template.user_template, {"draft": draft})
    response = llm_adapter.generate_text(
        LLMRequest(
            system_prompt=prompt_template.system_prompt,
            prompt=prompt,
            model=prompt_template.model,
            metadata={"task_id": task.id, "prompt_template_key": prompt_template.key},
        )
    )
    create_content_draft(
        db,
        task,
        kind="critique",
        body=response.text,
        provider=response.provider,
        model=response.model,
        prompt_template=prompt_template,
    )
    return response


def generate_rewrite(
    db: Session,
    task: ContentTask,
    prompt_template: PromptTemplate,
    llm_adapter: LLMAdapter,
    draft: str,
    critique: str,
    article_checkpoint_context: str = "",
) -> LLMResponse:
    rendered_template = render_prompt_template(
        prompt_template.user_template,
        {
            "draft": draft,
            "critique": critique,
            "article_checkpoint_context": article_checkpoint_context,
        },
    )
    prompt = rendered_template
    if article_checkpoint_context:
        prompt = "\n\n".join(
            [
                rendered_template,
                "Article Studio checkpoints to apply during rewrite:",
                article_checkpoint_context,
            ]
        )
    response = llm_adapter.generate_text(
        LLMRequest(
            system_prompt=prompt_template.system_prompt,
            prompt=prompt,
            model=prompt_template.model,
            metadata={"task_id": task.id, "prompt_template_key": prompt_template.key},
        )
    )
    create_content_draft(
        db,
        task,
        kind="final",
        body=response.text,
        provider=response.provider,
        model=response.model,
        prompt_template=prompt_template,
        metadata_json={
            "article_checkpoint_context_included": bool(article_checkpoint_context),
        },
    )
    return response


def render_prompt_template(template: str, variables: dict[str, str | list[str]]) -> str:
    fields = {field for _, field, _, _ in Formatter().parse(template) if field}
    safe_variables = {field: variables.get(field, "") for field in fields}
    return template.format(**safe_variables)


def _build_prompt_variables(
    task: ContentTask,
    product: Product | None,
    skill_context: str,
    research_report: str,
    article_checkpoint_context: str = "",
) -> dict[str, str | list[str]]:
    subject = product.title if product else task.topic or "Untitled content task"
    skills_used = _skill_names_from_context(skill_context)
    return {
        "product": _format_product(product) if product else subject,
        "specifications": product.raw_description if product and product.raw_description else "",
        "research_report": research_report,
        "article_checkpoint_context": article_checkpoint_context,
        "subject": subject,
        "goal": "Create useful marketing content that is ready for human approval.",
        "audience": "Electronics buyers comparing products before purchase.",
        "platform": "website, YouTube, Shorts, Telegram",
        "skill_context": skill_context,
        "skills_used": skills_used,
    }


def _build_skill_context(db: Session) -> str:
    skills = list_agent_skills(db, limit=100, status=AgentSkillStatus.ACTIVE.value)
    if not skills:
        return "No active skills are synced yet."
    return "\n\n".join(
        f"Skill: {skill.name}\nDescription: {skill.description}\nVersion: {skill.version or 'n/a'}"
        for skill in skills
    )


def _skill_names_from_context(skill_context: str) -> list[str]:
    return [
        line.removeprefix("Skill: ").strip()
        for line in skill_context.splitlines()
        if line.startswith("Skill: ")
    ]


def _format_product(product: Product | None) -> str:
    if product is None:
        return ""
    values = {
        "title": product.title,
        "brand": product.brand,
        "model": product.model,
        "category": product.category,
        "sku": product.sku,
        "gtin": product.gtin,
        "mpn": product.mpn,
        "price": str(product.price) if product.price is not None else None,
        "currency": product.currency,
        "availability": product.availability,
        "source_url": product.source_url,
        "raw_description": product.raw_description,
    }
    return "\n".join(f"{key}: {value}" for key, value in values.items() if value)


def _draft_title(task: ContentTask, product: Product | None) -> str:
    if product is not None:
        return product.title
    return task.topic or f"{task.task_type} draft"
