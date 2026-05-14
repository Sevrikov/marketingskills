from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.content_research_report import ContentResearchReport
from app.models.content_task import ContentTask
from app.schemas.infographic import (
    InfographicDataPackRead,
    InfographicDesignBriefRead,
    InfographicProjectCreate,
    InfographicProjectRead,
)
from app.services.infographics import (
    MissingInfographicDataPack,
    create_infographic_project,
    generate_infographic_data_pack,
    generate_infographic_design_brief,
    get_infographic_project,
    list_infographic_data_packs,
    list_infographic_design_briefs,
    list_infographic_projects,
)
from app.services.products import get_product

router = APIRouter(prefix="/api/infographics", tags=["infographics"])


@router.post(
    "/projects",
    response_model=InfographicProjectRead,
    status_code=status.HTTP_201_CREATED,
)
def create_infographic_project_endpoint(
    payload: InfographicProjectCreate,
    db: Session = Depends(get_db),
):
    _validate_project_sources(db, payload)
    return create_infographic_project(db, payload)


@router.get("/projects", response_model=list[InfographicProjectRead])
def list_infographic_projects_endpoint(
    product_id: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return list_infographic_projects(db, product_id=product_id, status=status_filter, limit=limit)


@router.get("/projects/{project_id}", response_model=InfographicProjectRead)
def get_infographic_project_endpoint(project_id: str, db: Session = Depends(get_db)):
    return _project_or_404(db, project_id)


@router.post(
    "/projects/{project_id}/generate-data-pack",
    response_model=InfographicDataPackRead,
)
def generate_infographic_data_pack_endpoint(project_id: str, db: Session = Depends(get_db)):
    project = _project_or_404(db, project_id)
    return generate_infographic_data_pack(db, project)


@router.get(
    "/projects/{project_id}/data-packs",
    response_model=list[InfographicDataPackRead],
)
def list_infographic_data_packs_endpoint(project_id: str, db: Session = Depends(get_db)):
    _project_or_404(db, project_id)
    return list_infographic_data_packs(db, project_id)


@router.post(
    "/projects/{project_id}/generate-brief",
    response_model=InfographicDesignBriefRead,
)
def generate_infographic_design_brief_endpoint(project_id: str, db: Session = Depends(get_db)):
    project = _project_or_404(db, project_id)
    try:
        return generate_infographic_design_brief(db, project)
    except MissingInfographicDataPack as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get(
    "/projects/{project_id}/design-briefs",
    response_model=list[InfographicDesignBriefRead],
)
def list_infographic_design_briefs_endpoint(project_id: str, db: Session = Depends(get_db)):
    _project_or_404(db, project_id)
    return list_infographic_design_briefs(db, project_id)


def _project_or_404(db: Session, project_id: str):
    project = get_infographic_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Infographic project not found")
    return project


def _validate_project_sources(db: Session, payload: InfographicProjectCreate) -> None:
    if payload.product_id and get_product(db, payload.product_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    source_task = db.get(ContentTask, payload.source_task_id) if payload.source_task_id else None
    if payload.source_task_id and source_task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source task not found")
    source_research = (
        db.get(ContentResearchReport, payload.source_research_report_id)
        if payload.source_research_report_id
        else None
    )
    if payload.source_research_report_id and source_research is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source research report not found",
        )
    if source_task and source_research and source_research.task_id != source_task.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Source research report does not belong to source task",
        )
