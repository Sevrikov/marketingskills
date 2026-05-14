from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.prompt_template import PromptTemplateCreate, PromptTemplateRead
from app.services.prompt_templates import (
    DuplicatePromptTemplate,
    create_prompt_template,
    get_active_prompt_template_by_key,
    get_prompt_template,
    list_prompt_templates,
)

router = APIRouter(prefix="/api/prompts", tags=["prompt templates"])


@router.post("", response_model=PromptTemplateRead, status_code=status.HTTP_201_CREATED)
def create_prompt_endpoint(payload: PromptTemplateCreate, db: Session = Depends(get_db)):
    try:
        return create_prompt_template(db, payload)
    except DuplicatePromptTemplate as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=list[PromptTemplateRead])
def list_prompts_endpoint(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
):
    return list_prompt_templates(db, limit=limit, offset=offset, status=status_filter)


@router.get("/by-key/{key}", response_model=PromptTemplateRead)
def get_active_prompt_by_key_endpoint(key: str, db: Session = Depends(get_db)):
    prompt = get_active_prompt_template_by_key(db, key)
    if prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active prompt not found")
    return prompt


@router.get("/{prompt_id}", response_model=PromptTemplateRead)
def get_prompt_endpoint(prompt_id: str, db: Session = Depends(get_db)):
    prompt = get_prompt_template(db, prompt_id)
    if prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    return prompt
