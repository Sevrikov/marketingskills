from app.adapters.gemini import GeminiLLMAdapter
from app.adapters.gemini_image_generation import GeminiImageGenerationAdapter
from app.adapters.gemini_research import GeminiResearchAdapter
from app.adapters.image_generation import ImageGenerationAdapter
from app.adapters.llm import LLMAdapter
from app.adapters.cms import CMSAdapter
from app.adapters.media import MediaAdapter
from app.adapters.mock_image_generation import MockImageGenerationAdapter
from app.adapters.mock_llm import MockLLMAdapter
from app.adapters.mock_cms import MockCMSAdapter
from app.adapters.mock_media import MockMediaAdapter
from app.adapters.mock_notifications import MockNotificationAdapter
from app.adapters.mock_price_monitor import MockPriceMonitorAdapter
from app.adapters.mock_research import MockResearchAdapter
from app.adapters.mock_search_console import MockSearchConsoleAdapter
from app.adapters.mock_source_provider import MockSourceProvider
from app.adapters.mock_storage import MockStorageAdapter
from app.adapters.notifications import NotificationAdapter
from app.adapters.playwright_price_monitor import PlaywrightPriceMonitorAdapter
from app.adapters.price_monitor import PriceMonitorAdapter
from app.adapters.research import ResearchAdapter
from app.adapters.search_console import SearchConsoleAdapter
from app.adapters.source_provider import SourceProvider
from app.adapters.storage import StorageAdapter
from app.adapters.tavily_source_provider import TavilySourceProvider
from app.adapters.viber_notifications import ViberNotificationAdapter
from app.config import Settings


def build_llm_adapter(settings: Settings) -> LLMAdapter:
    if settings.llm_provider == "gemini":
        return GeminiLLMAdapter(settings)
    return MockLLMAdapter()


def build_research_adapter(settings: Settings) -> ResearchAdapter:
    if settings.research_provider == "gemini":
        return GeminiResearchAdapter(settings)
    return MockResearchAdapter()


def build_source_provider(settings: Settings) -> SourceProvider:
    if settings.source_provider == "tavily":
        return TavilySourceProvider(settings)
    return MockSourceProvider()


def build_price_monitor_adapter(settings: Settings) -> PriceMonitorAdapter:
    if settings.price_monitor_provider == "playwright":
        return PlaywrightPriceMonitorAdapter(settings)
    return MockPriceMonitorAdapter()


def build_notification_adapter(settings: Settings) -> NotificationAdapter:
    if settings.notification_provider == "viber":
        return ViberNotificationAdapter(settings)
    return MockNotificationAdapter()


def build_storage_adapter(settings: Settings) -> StorageAdapter:
    return MockStorageAdapter()


def build_cms_adapter(settings: Settings) -> CMSAdapter:
    if settings.cms_provider == "mock":
        return MockCMSAdapter()
    return MockCMSAdapter()


def build_media_adapter(settings: Settings) -> MediaAdapter:
    return MockMediaAdapter()


def build_image_generation_adapter(settings: Settings) -> ImageGenerationAdapter:
    if settings.image_generation_provider == "gemini":
        return GeminiImageGenerationAdapter(settings)
    return MockImageGenerationAdapter()


def build_search_console_adapter(settings: Settings) -> SearchConsoleAdapter:
    return MockSearchConsoleAdapter()
