from datetime import UTC, datetime, timedelta

import pytest

from app.adapters.gemini_research import GeminiResearchAdapter
from app.adapters.research import ResearchRequest
from app.config import Settings
from app.services.gemini_quota import GeminiQuotaError, GeminiQuotaGovernor


def test_quota_governor_blocks_model_after_daily_limit(tmp_path):
    settings = Settings(
        gemini_quota_ledger_path=str(tmp_path / "ledger.json"),
        gemini_daily_model_limits="model-a=1",
    )
    governor = GeminiQuotaGovernor(settings, now_func=_fixed_now)

    assert governor.select_model(["model-a"]) == "model-a"

    governor.record_success("model-a", input_chars=10, output_chars=2)

    with pytest.raises(GeminiQuotaError, match="local daily limit"):
        governor.select_model(["model-a"])


def test_quota_governor_blocks_quota_error_for_current_day(tmp_path):
    settings = Settings(gemini_quota_ledger_path=str(tmp_path / "ledger.json"))
    governor = GeminiQuotaGovernor(settings, now_func=_fixed_now)

    governor.record_failure("model-a", RuntimeError("429 RESOURCE_EXHAUSTED quota"))

    with pytest.raises(GeminiQuotaError, match="quota error"):
        governor.select_model(["model-a"])


def test_quota_governor_allows_model_after_unavailable_cooldown(tmp_path):
    now = datetime(2026, 5, 7, 12, 0, tzinfo=UTC)
    settings = Settings(
        gemini_quota_ledger_path=str(tmp_path / "ledger.json"),
        gemini_unavailable_cooldown_seconds=60,
    )
    governor = GeminiQuotaGovernor(settings, now_func=lambda: now)
    governor.record_failure("model-a", RuntimeError("503 UNAVAILABLE"))

    with pytest.raises(GeminiQuotaError, match="cooling down"):
        governor.select_model(["model-a"])

    later = GeminiQuotaGovernor(settings, now_func=lambda: now + timedelta(seconds=61))

    assert later.select_model(["model-a"]) == "model-a"


def test_gemini_research_falls_back_after_transient_model_error(tmp_path):
    settings = Settings(
        google_api_key="test-key",
        research_provider="gemini",
        gemini_research_model="model-a",
        gemini_smoke_models="model-a,model-b",
        gemini_quota_ledger_path=str(tmp_path / "ledger.json"),
        gemini_daily_model_limits="model-a=10,model-b=10",
        gemini_unavailable_cooldown_seconds=60,
    )
    client = FallbackGeminiClient()
    adapter = GeminiResearchAdapter(settings, client=client)

    report = adapter.run_research(ResearchRequest(query="Starlink Mini", task_id="task-1"))

    assert report.normalized["model"] == "model-b"
    assert client.calls == ["model-a", "model-b"]

    snapshot = GeminiQuotaGovernor(settings).snapshot()
    assert snapshot["models"]["model-a"]["unavailable_errors"] == 1
    assert snapshot["models"]["model-b"]["success"] == 1


def _fixed_now():
    return datetime(2026, 5, 7, 12, 0, tzinfo=UTC)


class FallbackGeminiClient:
    def __init__(self) -> None:
        self.models = FallbackGeminiModels()

    @property
    def calls(self) -> list[str]:
        return self.models.calls


class FallbackGeminiModels:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate_content(self, model, contents, config):
        self.calls.append(model)
        if model == "model-a":
            raise RuntimeError("503 UNAVAILABLE high demand")
        assert model == "model-b"
        assert "Starlink Mini" in contents
        assert config is not None
        return FallbackGeminiResponse()


class FallbackGeminiResponse:
    text = "# Fallback report"
    response_id = "response-fallback"
    candidates = []
