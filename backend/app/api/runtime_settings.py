from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.runtime_setting import RuntimeSettingsRead, RuntimeSettingsUpdate
from app.services.runtime_settings import list_runtime_setting_fields, update_runtime_settings

router = APIRouter(prefix="/api/runtime-settings", tags=["runtime settings"])


@router.get("", response_model=RuntimeSettingsRead)
def get_runtime_settings_endpoint(db: Session = Depends(get_db)):
    fields = list_runtime_setting_fields(db)
    return RuntimeSettingsRead(
        fields=fields,
        sections=list(dict.fromkeys(field.section for field in fields)),
    )


@router.put("", response_model=RuntimeSettingsRead)
def update_runtime_settings_endpoint(
    payload: RuntimeSettingsUpdate,
    db: Session = Depends(get_db),
):
    fields = update_runtime_settings(db, payload.values)
    return RuntimeSettingsRead(
        fields=fields,
        sections=list(dict.fromkeys(field.section for field in fields)),
    )
