from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.agent_skills import router as agent_skills_router
from app.api.content_opportunities import router as content_opportunities_router
from app.api.content_tasks import router as content_tasks_router
from app.api.infographics import router as infographics_router
from app.api.pain_profiles import router as pain_profiles_router
from app.api.price_monitor import router as price_monitor_router
from app.api.product_content_profiles import router as product_content_profiles_router
from app.api.prompt_templates import router as prompt_templates_router
from app.api.products import router as products_router
from app.api.runtime_settings import router as runtime_settings_router
from app.api.scheduler import router as scheduler_router
from app.api.webhooks import router as webhooks_router
from app.adapters.factory import (
    build_cms_adapter,
    build_image_generation_adapter,
    build_llm_adapter,
    build_notification_adapter,
    build_price_monitor_adapter,
    build_research_adapter,
    build_source_provider,
)
from app.adapters.llm import LLMRequest
from app.config import get_settings
from app.db.session import get_db
from app.services.runtime_settings import effective_settings

settings = get_settings()
llm_adapter = build_llm_adapter(settings)
research_adapter = build_research_adapter(settings)
notification_adapter = build_notification_adapter(settings)
source_provider_adapter = build_source_provider(settings)
price_monitor_adapter = build_price_monitor_adapter(settings)
cms_provider_adapter = build_cms_adapter(settings)
image_generation_adapter = build_image_generation_adapter(settings)

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products_router)
app.include_router(product_content_profiles_router)
app.include_router(content_opportunities_router)
app.include_router(content_tasks_router)
app.include_router(infographics_router)
app.include_router(pain_profiles_router)
app.include_router(price_monitor_router)
app.include_router(scheduler_router)
app.include_router(prompt_templates_router)
app.include_router(agent_skills_router)
app.include_router(runtime_settings_router)
app.include_router(webhooks_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
    }


@app.get("/debug/llm-provider")
def llm_provider(db: Session = Depends(get_db)) -> dict[str, str]:
    current_settings = effective_settings(db)
    adapter = build_llm_adapter(current_settings)
    return {
        "provider": getattr(adapter, "provider", "unknown"),
        "mode": current_settings.llm_provider,
    }


@app.get("/debug/research-provider")
def research_provider(db: Session = Depends(get_db)) -> dict[str, str]:
    current_settings = effective_settings(db)
    adapter = build_research_adapter(current_settings)
    return {
        "provider": getattr(adapter, "provider", "unknown"),
        "mode": current_settings.research_provider,
    }


@app.get("/debug/notification-provider")
def notification_provider(db: Session = Depends(get_db)) -> dict[str, str]:
    current_settings = effective_settings(db)
    adapter = build_notification_adapter(current_settings)
    return {
        "provider": getattr(adapter, "provider", "unknown"),
        "mode": current_settings.notification_provider,
    }


@app.get("/debug/source-provider")
def source_provider(db: Session = Depends(get_db)) -> dict[str, str]:
    current_settings = effective_settings(db)
    adapter = build_source_provider(current_settings)
    return {
        "provider": getattr(adapter, "provider", "unknown"),
        "mode": current_settings.source_provider,
    }


@app.get("/debug/price-monitor-provider")
def price_monitor_provider(db: Session = Depends(get_db)) -> dict[str, str]:
    current_settings = effective_settings(db)
    adapter = build_price_monitor_adapter(current_settings)
    return {
        "provider": getattr(adapter, "provider", "unknown"),
        "mode": current_settings.price_monitor_provider,
    }


@app.get("/debug/cms-provider")
def cms_provider(db: Session = Depends(get_db)) -> dict[str, str]:
    current_settings = effective_settings(db)
    adapter = build_cms_adapter(current_settings)
    return {
        "provider": getattr(adapter, "provider", "unknown"),
        "mode": current_settings.cms_provider,
        "destination_type": current_settings.cms_destination_type,
    }


@app.get("/debug/image-generation-provider")
def image_generation_provider(db: Session = Depends(get_db)) -> dict[str, str | bool]:
    current_settings = effective_settings(db)
    adapter = build_image_generation_adapter(current_settings)
    return {
        "provider": getattr(adapter, "provider", "unknown"),
        "mode": current_settings.image_generation_provider,
        "real_image_generation_enabled": current_settings.enable_real_image_generation,
        "model": current_settings.gemini_image_model,
    }


@app.post("/debug/llm-echo")
def llm_echo(prompt: str) -> dict[str, str]:
    response = llm_adapter.generate_text(
        LLMRequest(
            system_prompt="You are a test adapter. Keep the response short.",
            prompt=prompt,
        )
    )
    return {
        "provider": response.provider,
        "model": response.model,
        "text": response.text,
    }
