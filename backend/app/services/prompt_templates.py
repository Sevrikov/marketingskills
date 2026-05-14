from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.prompt_template import PromptTemplate, PromptTemplateStatus
from app.schemas.prompt_template import PromptTemplateCreate


class DuplicatePromptTemplate(ValueError):
    pass


def create_prompt_template(db: Session, data: PromptTemplateCreate) -> PromptTemplate:
    prompt = PromptTemplate(**data.model_dump(mode="json"))
    db.add(prompt)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicatePromptTemplate(
            f"Prompt template {data.key} version {data.version} already exists."
        ) from exc
    db.refresh(prompt)
    return prompt


def list_prompt_templates(
    db: Session,
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
) -> list[PromptTemplate]:
    stmt = select(PromptTemplate).order_by(PromptTemplate.key.asc(), PromptTemplate.version.desc())
    if status:
        stmt = stmt.where(PromptTemplate.status == status)
    stmt = stmt.limit(limit).offset(offset)
    return list(db.scalars(stmt))


def get_prompt_template(db: Session, prompt_id: str) -> PromptTemplate | None:
    return db.get(PromptTemplate, prompt_id)


def get_active_prompt_template_by_key(db: Session, key: str) -> PromptTemplate | None:
    stmt = (
        select(PromptTemplate)
        .where(PromptTemplate.key == key)
        .where(PromptTemplate.status == PromptTemplateStatus.ACTIVE.value)
        .order_by(PromptTemplate.version.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()
