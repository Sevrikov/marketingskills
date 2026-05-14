from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.agent_skill import AgentSkillRead, SkillSyncResponse
from app.services.skill_registry import (
    get_agent_skill,
    get_agent_skill_by_name,
    list_agent_skills,
    sync_agent_skills,
)

router = APIRouter(prefix="/api/skills", tags=["agent skills"])


@router.get("", response_model=list[AgentSkillRead])
def list_skills_endpoint(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default="active", alias="status"),
    db: Session = Depends(get_db),
):
    return list_agent_skills(db, limit=limit, offset=offset, status=status_filter)


@router.get("/by-name/{name}", response_model=AgentSkillRead)
def get_skill_by_name_endpoint(name: str, db: Session = Depends(get_db)):
    skill = get_agent_skill_by_name(db, name)
    if skill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    return skill


@router.get("/{skill_id}", response_model=AgentSkillRead)
def get_skill_endpoint(skill_id: str, db: Session = Depends(get_db)):
    skill = get_agent_skill(db, skill_id)
    if skill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    return skill


@router.post("/sync", response_model=SkillSyncResponse)
def sync_skills_endpoint(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    result = sync_agent_skills(db, settings.skill_registry_root)
    return SkillSyncResponse(
        scanned=result.scanned,
        upserted=result.upserted,
        archived=result.archived,
    )
