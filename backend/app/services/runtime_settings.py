from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models.runtime_setting import RuntimeSetting
from app.schemas.runtime_setting import RuntimeSettingField


@dataclass(frozen=True)
class RuntimeSettingSpec:
    key: str
    label: str
    section: str
    kind: str
    default: str | bool | None
    options: tuple[str, ...] = ()
    is_secret: bool = False
    description: str | None = None


SETTING_SPECS: tuple[RuntimeSettingSpec, ...] = (
    RuntimeSettingSpec("google_api_key", "Google API key", "Secrets", "secret", None, is_secret=True),
    RuntimeSettingSpec("tavily_api_key", "Tavily API key", "Secrets", "secret", None, is_secret=True),
    RuntimeSettingSpec("viber_auth_token", "Viber auth token", "Secrets", "secret", None, is_secret=True),
    RuntimeSettingSpec("llm_provider", "Content LLM provider", "Providers", "select", "mock", ("mock", "gemini")),
    RuntimeSettingSpec("research_provider", "Research provider", "Providers", "select", "mock", ("mock", "gemini")),
    RuntimeSettingSpec("source_provider", "Source provider", "Providers", "select", "mock", ("mock", "tavily")),
    RuntimeSettingSpec(
        "notification_provider",
        "Notification provider",
        "Providers",
        "select",
        "mock",
        ("mock", "viber"),
    ),
    RuntimeSettingSpec(
        "image_generation_provider",
        "Image generation provider",
        "Providers",
        "select",
        "mock",
        ("mock", "gemini"),
    ),
    RuntimeSettingSpec(
        "enable_real_image_generation",
        "Enable real image generation",
        "Safety",
        "boolean",
        False,
        description="Real Gemini image calls remain blocked until this is enabled.",
    ),
    RuntimeSettingSpec(
        "enable_google_smoke_tests",
        "Enable Google smoke tests",
        "Safety",
        "boolean",
        False,
    ),
    RuntimeSettingSpec(
        "gemini_content_model",
        "Content model",
        "Models",
        "select",
        "gemini-2.5-flash-lite",
        (
            "gemini-2.5-flash-lite",
            "gemini-3-flash-preview",
            "gemini-3.1-flash-lite-preview",
        ),
    ),
    RuntimeSettingSpec(
        "gemini_critic_model",
        "Critic/rewrite model",
        "Models",
        "select",
        "gemini-2.5-flash-lite",
        (
            "gemini-2.5-flash-lite",
            "gemini-3-flash-preview",
            "gemini-3.1-flash-lite-preview",
        ),
    ),
    RuntimeSettingSpec(
        "gemini_research_model",
        "Deep research model",
        "Models",
        "select",
        "gemini-2.5-flash-lite",
        (
            "gemini-2.5-flash-lite",
            "gemini-3-flash-preview",
            "gemini-3.1-flash-lite-preview",
        ),
    ),
    RuntimeSettingSpec(
        "gemini_image_model",
        "Image generation model",
        "Models",
        "select",
        "gemini-3.1-flash-image-preview",
        (
            "gemini-3.1-flash-image-preview",
            "gemini-2.5-flash-image",
            "gemini-3-pro-image-preview",
        ),
    ),
    RuntimeSettingSpec(
        "gemini_image_models",
        "Image fallback models",
        "Models",
        "text",
        "gemini-3.1-flash-image-preview,gemini-2.5-flash-image,gemini-3-pro-image-preview",
    ),
    RuntimeSettingSpec(
        "viber_reviewer_ids",
        "Viber reviewer IDs",
        "Viber",
        "text",
        "",
        description="Comma-separated reviewer/user ids for approval notifications.",
    ),
    RuntimeSettingSpec("viber_sender_name", "Viber sender name", "Viber", "text", "AI Content Factory"),
    RuntimeSettingSpec("viber_webhook_public_url", "Viber webhook public URL", "Viber", "text", None),
    RuntimeSettingSpec(
        "viber_webhook_event_types",
        "Viber webhook events",
        "Viber",
        "text",
        "message,conversation_started,subscribed,unsubscribed,failed",
    ),
)

SETTING_SPEC_BY_KEY = {spec.key: spec for spec in SETTING_SPECS}


def list_runtime_setting_fields(db: Session) -> list[RuntimeSettingField]:
    records = _runtime_setting_records(db)
    base = get_settings()
    return [_field_from_spec(spec, records.get(spec.key), base) for spec in SETTING_SPECS]


def update_runtime_settings(db: Session, values: dict[str, Any]) -> list[RuntimeSettingField]:
    records = _runtime_setting_records(db)
    for key, raw_value in values.items():
        spec = SETTING_SPEC_BY_KEY.get(key)
        if spec is None:
            continue
        if spec.is_secret and (raw_value is None or str(raw_value).strip() == ""):
            continue
        value = _serialize_value(spec, raw_value)
        record = records.get(key)
        if record is None:
            record = RuntimeSetting(
                key=key,
                value=value,
                is_secret=spec.is_secret,
                description=spec.description,
            )
        else:
            record.value = value
            record.is_secret = spec.is_secret
            record.description = spec.description
        db.add(record)
    db.commit()
    return list_runtime_setting_fields(db)


def effective_settings(db: Session, base: Settings | None = None) -> Settings:
    base = base or get_settings()
    update: dict[str, Any] = {}
    for key, record in _runtime_setting_records(db).items():
        spec = SETTING_SPEC_BY_KEY.get(key)
        if spec is None:
            continue
        update[key] = _deserialize_value(spec, record.value)
    return base.model_copy(update=update)


def _runtime_setting_records(db: Session) -> dict[str, RuntimeSetting]:
    stmt = select(RuntimeSetting)
    return {record.key: record for record in db.scalars(stmt)}


def _field_from_spec(
    spec: RuntimeSettingSpec,
    record: RuntimeSetting | None,
    base: Settings,
) -> RuntimeSettingField:
    env_value = getattr(base, spec.key, spec.default)
    stored_value = _deserialize_value(spec, record.value) if record else None
    configured = _is_configured(stored_value if record else env_value)
    value = None if spec.is_secret else (stored_value if record else env_value)
    masked_value = _mask_secret(stored_value or env_value) if spec.is_secret and configured else None
    return RuntimeSettingField(
        key=spec.key,
        label=spec.label,
        section=spec.section,
        kind=spec.kind,
        configured=configured,
        value=value,
        masked_value=masked_value,
        env_value=None if spec.is_secret else env_value,
        options=list(spec.options),
        description=spec.description,
        updated_at=record.updated_at if record else None,
    )


def _serialize_value(spec: RuntimeSettingSpec, value: Any) -> str:
    if spec.kind == "boolean":
        return "true" if bool(value) else "false"
    return str(value or "")


def _deserialize_value(spec: RuntimeSettingSpec, value: str) -> str | bool:
    if spec.kind == "boolean":
        return value.lower() in {"1", "true", "yes", "on"}
    return value


def _is_configured(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return value is not None and str(value).strip() != ""


def _mask_secret(value: Any) -> str | None:
    text = str(value or "")
    if not text:
        return None
    if len(text) <= 8:
        return "****"
    return f"{text[:4]}...{text[-4:]}"
