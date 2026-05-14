from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.content_research_report import ContentResearchReport
from app.models.content_task import ContentTask
from app.schemas.pain_profile import PainProfileApprove, PainProfileGenerate, PainProfileRead
from app.services.pain_profiles import (
    approve_pain_profile,
    generate_pain_profile,
    get_pain_profile,
    list_pain_profiles,
)
from app.services.products import get_product

router = APIRouter(prefix="/api/pain-profiles", tags=["pain profiles"])


@router.get("", response_model=list[PainProfileRead])
def list_pain_profiles_endpoint(
    product_id: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    scope_type: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return list_pain_profiles(
        db,
        product_id=product_id,
        status=status_filter,
        scope_type=scope_type,
        limit=limit,
    )


@router.get("/{profile_id}", response_model=PainProfileRead)
def get_pain_profile_endpoint(profile_id: str, db: Session = Depends(get_db)):
    profile = get_pain_profile(db, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pain profile not found")
    return profile


@router.post("/generate", response_model=PainProfileRead, status_code=status.HTTP_201_CREATED)
def generate_pain_profile_endpoint(payload: PainProfileGenerate, db: Session = Depends(get_db)):
    product = get_product(db, payload.product_id) if payload.product_id else None
    if payload.product_id and product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    source_task = db.get(ContentTask, payload.source_task_id) if payload.source_task_id else None
    if payload.source_task_id and source_task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source task not found")
    if product is None and source_task and source_task.product_id:
        product = get_product(db, source_task.product_id)

    source_research_report = (
        db.get(ContentResearchReport, payload.source_research_report_id)
        if payload.source_research_report_id
        else None
    )
    if payload.source_research_report_id and source_research_report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source research report not found",
        )
    if source_research_report and source_task and source_research_report.task_id != source_task.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Source research report does not belong to source task",
        )
    if product is None and source_task is None and not payload.scope_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide product_id, source_task_id or scope_id.",
        )

    return generate_pain_profile(
        db,
        payload,
        product=product,
        source_task=source_task,
        source_research_report=source_research_report,
    )


@router.post("/{profile_id}/approve", response_model=PainProfileRead)
def approve_pain_profile_endpoint(
    profile_id: str,
    payload: PainProfileApprove | None = None,
    db: Session = Depends(get_db),
):
    profile = get_pain_profile(db, profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pain profile not found")
    return approve_pain_profile(db, profile, payload or PainProfileApprove())
