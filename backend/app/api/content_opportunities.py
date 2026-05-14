from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.adapters.factory import build_research_adapter, build_source_provider
from app.db.session import get_db
from app.schemas.content_opportunity import (
    ContentOpportunityCreateTaskResult,
    ContentOpportunityDiscover,
    ContentOpportunityDiscoverResult,
    ContentOpportunityRead,
)
from app.services.content_opportunities import (
    OpportunityScopeNotFound,
    create_task_from_opportunity,
    discover_content_opportunities,
    get_content_opportunity,
    list_content_opportunities,
)
from app.services.runtime_settings import effective_settings

router = APIRouter(prefix="/api/content-opportunities", tags=["content opportunities"])


@router.post("/discover", response_model=ContentOpportunityDiscoverResult)
def discover_content_opportunities_endpoint(
    payload: ContentOpportunityDiscover,
    db: Session = Depends(get_db),
):
    settings = effective_settings(db)
    try:
        query, source_provider, research_provider, opportunities = discover_content_opportunities(
            db,
            payload,
            source_provider=build_source_provider(settings),
            research_adapter=build_research_adapter(settings),
        )
    except OpportunityScopeNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ContentOpportunityDiscoverResult(
        query=query,
        provider=source_provider,
        research_provider=research_provider,
        created=len(opportunities),
        opportunities=opportunities,
    )


@router.get("", response_model=list[ContentOpportunityRead])
def list_content_opportunities_endpoint(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
):
    return list_content_opportunities(db, limit=limit, offset=offset, status=status_filter)


@router.post("/{opportunity_id}/create-task", response_model=ContentOpportunityCreateTaskResult)
def create_task_from_opportunity_endpoint(
    opportunity_id: str,
    db: Session = Depends(get_db),
):
    opportunity = get_content_opportunity(db, opportunity_id)
    if opportunity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content opportunity not found",
        )
    task_id, task_status = create_task_from_opportunity(db, opportunity)
    return ContentOpportunityCreateTaskResult(
        opportunity_id=opportunity.id,
        task_id=task_id,
        task_status=task_status,
    )
