from app.adapters.cms import PublishRequest
from app.adapters.factory import (
    build_cms_adapter,
    build_image_generation_adapter,
    build_media_adapter,
    build_notification_adapter,
    build_research_adapter,
    build_search_console_adapter,
    build_source_provider,
    build_storage_adapter,
)
from app.adapters.gemini_image_generation import GeminiImageGenerationAdapter
from app.adapters.image_generation import ImageGenerationRequest
from app.adapters.gemini_research import GeminiResearchAdapter
from app.adapters.media import MediaGenerationRequest
from app.adapters.notifications import ApprovalNotificationRequest
from app.adapters.research import ResearchRequest
from app.adapters.search_console import IndexingRequest
from app.adapters.source_provider import SourceSearchRequest
from app.adapters.tavily_source_provider import TavilySourceProvider
from app.adapters.viber_notifications import ViberNotificationAdapter
from app.config import Settings


def test_mock_research_adapter_contract():
    adapter = build_research_adapter(Settings())

    report = adapter.run_research(ResearchRequest(query="Starlink Mini", task_id="task-1"))

    assert report.provider == "mock-research"
    assert report.sources
    assert report.normalized["query"] == "Starlink Mini"


def test_mock_source_provider_contract():
    provider = build_source_provider(Settings())

    result = provider.search(SourceSearchRequest(query="Starlink Mini", task_id="task-1"))

    assert result.provider == "mock-source-provider"
    assert result.documents
    assert result.documents[0].source_type == "mock_source"


def test_factory_uses_tavily_source_provider_when_requested():
    provider = build_source_provider(Settings(source_provider="tavily", tavily_api_key="test-key"))

    assert isinstance(provider, TavilySourceProvider)


def test_tavily_source_provider_parses_documents():
    provider = FakeTavilyProvider(Settings(source_provider="tavily", tavily_api_key="test-key"))

    result = provider.search(SourceSearchRequest(query="Starlink Mini", max_results=1))

    assert result.provider == "tavily"
    assert result.external_id == "request-1"
    assert result.usage == {"credits": 1}
    assert result.documents[0].title == "Result One"
    assert result.documents[0].content == "# Raw markdown"
    assert provider.payloads[0]["include_raw_content"] == "markdown"


def test_llm_adapter_defaults_to_mock_even_with_key():
    from app.adapters.factory import build_llm_adapter

    adapter = build_llm_adapter(Settings(google_api_key="test-key"))

    assert adapter.provider == "mock"


def test_llm_adapter_uses_gemini_when_requested():
    from app.adapters.factory import build_llm_adapter

    adapter = build_llm_adapter(Settings(google_api_key="test-key", llm_provider="gemini"))

    assert adapter.provider == "google-gemini"


def test_gemini_research_adapter_extracts_grounded_sources():
    adapter = GeminiResearchAdapter(
        Settings(
            google_api_key="test-key",
            research_provider="gemini",
            enable_gemini_quota_governor=False,
        ),
        client=FakeGeminiClient(),
    )

    report = adapter.run_research(ResearchRequest(query="Starlink Mini", task_id="task-1"))

    assert report.provider == "google-gemini-grounded-research"
    assert report.markdown == "# Grounded report"
    assert report.sources[0].title == "Source One"
    assert report.sources[0].url == "https://example.com/source-one"
    assert report.sources[0].confidence == 0.92
    assert report.normalized["search_queries"] == ["Starlink Mini review"]


def test_factory_uses_gemini_research_when_requested():
    adapter = build_research_adapter(
        Settings(google_api_key="test-key", research_provider="gemini")
    )

    assert adapter.provider == "google-gemini-grounded-research"


def test_mock_notification_adapter_contract():
    adapter = build_notification_adapter(Settings())

    deliveries = adapter.send_approval_request(
        ApprovalNotificationRequest(
            task_id="task-1",
            task_type="seo_article",
            topic="Approval test",
            language="ru",
            status="waiting_approval",
        )
    )

    assert deliveries[0].provider == "mock-notifications"
    assert deliveries[0].channel == "mock"
    assert deliveries[0].status == "recorded"


def test_factory_uses_viber_notifications_when_requested():
    adapter = build_notification_adapter(Settings(notification_provider="viber"))

    assert adapter.provider == "viber"


def test_viber_approval_payload_contains_reply_actions():
    adapter = ViberNotificationAdapter(
        Settings(
            notification_provider="viber",
            viber_auth_token="token",
            viber_reviewer_ids="reviewer-1",
        )
    )

    payload = adapter.build_payload(
        "reviewer-1",
        ApprovalNotificationRequest(
            task_id="task-1",
            task_type="seo_article",
            topic="Approval test",
            language="ru",
            status="waiting_approval",
            console_url="https://example.com/console?task_id=task-1",
        ),
    )

    buttons = payload["keyboard"]["Buttons"]
    assert payload["receiver"] == "reviewer-1"
    assert payload["tracking_data"] == "task-1"
    assert buttons[0]["ActionBody"] == "approve:task-1"
    assert buttons[1]["ActionBody"] == "rewrite:task-1"
    assert buttons[2]["ActionType"] == "open-url"


def test_mock_storage_adapter_contract():
    adapter = build_storage_adapter(Settings())

    stored = adapter.put_text("reports/test.md", "# Test")

    assert stored.url == "mock://storage/reports/test.md"
    assert adapter.get_text("reports/test.md") == "# Test"


def test_mock_cms_adapter_contract():
    adapter = build_cms_adapter(Settings())
    request = PublishRequest(
        title="Starlink Mini Guide",
        body_html="<h1>Starlink Mini Guide</h1>",
        status="draft",
    )

    payload = adapter.prepare_payload(request)

    assert payload["provider"] == "mock-cms"
    assert payload["operation"] == "create_draft"
    assert payload["post"]["title"] == "Starlink Mini Guide"

    result = adapter.publish(request)

    assert result.provider == "mock-cms"
    assert result.status == "draft"
    assert result.url.endswith("/starlink-mini-guide")


def test_mock_media_adapter_contract():
    adapter = build_media_adapter(Settings())

    result = adapter.generate(
        MediaGenerationRequest(
            prompt="Product hero image",
            media_type="image",
            aspect_ratio="16:9",
            task_id="task-1",
        )
    )

    assert result.provider == "mock-media"
    assert result.status == "completed"
    assert result.file_url == "mock://media/mock-image-task-1"


def test_image_generation_adapter_defaults_to_mock():
    adapter = build_image_generation_adapter(Settings())

    result = adapter.generate(
        ImageGenerationRequest(
            asset_id="asset-1",
            slot="image:hero",
            asset_type="image",
            prompt="Product hero visual",
            dimensions="16:9",
        )
    )

    assert result.provider == "mock-image"
    assert result.storage_uri.startswith("data:image/svg+xml")


def test_factory_uses_gemini_image_generation_when_requested():
    adapter = build_image_generation_adapter(
        Settings(
            google_api_key="test-key",
            image_generation_provider="gemini",
            enable_real_image_generation=True,
        )
    )

    assert adapter.provider == "google-gemini-image"


def test_gemini_image_generation_extracts_inline_image():
    adapter = GeminiImageGenerationAdapter(
        Settings(
            google_api_key="test-key",
            image_generation_provider="gemini",
            enable_real_image_generation=True,
            enable_gemini_quota_governor=False,
        ),
        client=FakeGeminiImageClient(),
    )

    result = adapter.generate(
        ImageGenerationRequest(
            asset_id="asset-1",
            slot="image:hero",
            asset_type="image",
            prompt="Product hero visual",
            dimensions="16:9",
        )
    )

    assert result.provider == "google-gemini-image"
    assert result.model == "gemini-3.1-flash-image-preview"
    assert result.storage_uri == "data:image/png;base64,aW1hZ2UtYnl0ZXM="
    assert result.metadata["inline_bytes"] == 11


def test_mock_search_console_adapter_contract():
    adapter = build_search_console_adapter(Settings())

    result = adapter.request_indexing(IndexingRequest(url="https://example.com/page"))

    assert result.provider == "mock-search-console"
    assert result.status == "recorded"
    assert result.url == "https://example.com/page"


class FakeGeminiClient:
    def __init__(self) -> None:
        self.models = FakeGeminiModels()


class FakeGeminiModels:
    def generate_content(self, model, contents, config):
        assert model == "gemini-2.5-flash-lite"
        assert "Starlink Mini" in contents
        assert config is not None
        return FakeGeminiResponse()


class FakeGeminiResponse:
    text = "# Grounded report"
    response_id = "response-1"
    candidates = [
        type(
            "Candidate",
            (),
            {
                "grounding_metadata": type(
                    "Grounding",
                    (),
                    {
                        "web_search_queries": ["Starlink Mini review"],
                        "grounding_chunks": [
                            type(
                                "Chunk",
                                (),
                                {
                                    "web": type(
                                        "Web",
                                        (),
                                        {
                                            "title": "Source One",
                                            "uri": "https://example.com/source-one",
                                        },
                                    )()
                                },
                            )(),
                            type(
                                "Chunk",
                                (),
                                {
                                    "web": type(
                                        "Web",
                                        (),
                                        {
                                            "title": "Source One duplicate",
                                            "uri": "https://example.com/source-one",
                                        },
                                    )()
                                },
                            )(),
                        ],
                        "grounding_supports": [
                            type(
                                "Support",
                                (),
                                {
                                    "grounding_chunk_indices": [0],
                                    "confidence_scores": [0.92],
                                },
                            )()
                        ],
                    },
                )()
            },
        )()
    ]


class FakeGeminiImageClient:
    def __init__(self) -> None:
        self.models = FakeGeminiImageModels()


class FakeGeminiImageModels:
    def generate_content(self, model, contents, config):
        assert model == "gemini-3.1-flash-image-preview"
        assert contents == ["Product hero visual"]
        assert config.response_modalities == ["TEXT", "IMAGE"]
        return FakeGeminiImageResponse()


class FakeGeminiImageResponse:
    parts = [
        type(
            "Part",
            (),
            {
                "text": None,
                "inline_data": type(
                    "InlineData",
                    (),
                    {
                        "mime_type": "image/png",
                        "data": b"image-bytes",
                    },
                )(),
            },
        )()
    ]


class FakeTavilyProvider(TavilySourceProvider):
    def __init__(self, settings):
        super().__init__(settings)
        self.payloads = []

    def _post(self, payload: dict) -> dict:
        self.payloads.append(payload)
        return {
            "query": payload["query"],
            "answer": "Short answer",
            "request_id": "request-1",
            "usage": {"credits": 1},
            "response_time": 1.2,
            "results": [
                {
                    "title": "Result One",
                    "url": "https://example.com/result-one",
                    "content": "Snippet",
                    "raw_content": "# Raw markdown",
                    "score": 0.8,
                    "favicon": "https://example.com/favicon.ico",
                }
            ],
        }
