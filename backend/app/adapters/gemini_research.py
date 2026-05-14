from typing import Any

from app.adapters.gemini import GeminiConfigurationError
from app.adapters.research import ResearchAdapter, ResearchReport, ResearchRequest, ResearchSource
from app.config import Settings
from app.services.gemini_quota import (
    GeminiQuotaGovernor,
    build_gemini_candidates,
    should_try_next_gemini_model,
)


class GeminiResearchAdapter(ResearchAdapter):
    provider = "google-gemini-grounded-research"

    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self.settings = settings
        self._client = client

    def run_research(self, request: ResearchRequest) -> ResearchReport:
        if not self.settings.google_api_key and self._client is None:
            raise GeminiConfigurationError(
                "GOOGLE_API_KEY is not configured. Add it to local .env, never to git."
            )

        client = self._client or self._build_client()
        prompt = _build_research_prompt(request)
        config = self._build_config()
        quota = GeminiQuotaGovernor(self.settings)
        model_candidates = build_gemini_candidates(
            self.settings.gemini_research_model,
            self.settings.gemini_smoke_models,
        )

        errors: list[Exception] = []
        while model_candidates:
            model = quota.select_model(model_candidates)
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config,
                )
            except Exception as exc:
                quota.record_failure(model, exc)
                errors.append(exc)
                model_candidates = [candidate for candidate in model_candidates if candidate != model]
                if should_try_next_gemini_model(exc) and model_candidates:
                    continue
                raise

            markdown = getattr(response, "text", None) or ""
            quota.record_success(model, input_chars=len(prompt), output_chars=len(markdown))
            break
        else:
            if errors:
                raise errors[-1]
            raise GeminiConfigurationError("No Gemini research model candidate was available.")

        sources = _extract_sources(response)
        search_queries = _extract_search_queries(response)

        return ResearchReport(
            title=f"Gemini grounded research: {request.query}",
            markdown=markdown,
            sources=sources,
            normalized={
                "query": request.query,
                "mode": request.mode,
                "model": model,
                "search_queries": search_queries,
                "source_count": len(sources),
            },
            provider=self.provider,
            external_id=getattr(response, "response_id", None),
        )

    def _build_client(self) -> Any:
        try:
            from google import genai
        except ImportError as exc:
            raise GeminiConfigurationError(
                "google-genai package is not installed in the current runtime."
            ) from exc

        return genai.Client(api_key=self.settings.google_api_key)

    def _build_config(self) -> Any:
        try:
            from google.genai import types
        except ImportError as exc:
            raise GeminiConfigurationError(
                "google-genai package is not installed in the current runtime."
            ) from exc

        return types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.2,
            max_output_tokens=4096,
        )


def _build_research_prompt(request: ResearchRequest) -> str:
    source_corpus = (request.metadata or {}).get("source_corpus_markdown") or ""
    source_section = (
        "\n\nPrepared source corpus from the source provider:\n"
        f"{source_corpus}\n\n"
        "Use the prepared corpus as primary context. Use Google Search grounding to verify "
        "or fill gaps when needed."
        if source_corpus
        else ""
    )
    return (
        "Run a grounded marketing research task for an electronics e-commerce workflow.\n\n"
        f"Query: {request.query}\n"
        f"Mode: {request.mode}\n\n"
        "Return a concise markdown report with:\n"
        "- verified facts;\n"
        "- buyer questions and objections;\n"
        "- comparison angles;\n"
        "- content opportunities;\n"
        "- claims that need human verification.\n\n"
        "Use grounded sources when available. Separate facts from hypotheses."
        f"{source_section}"
    )


def _extract_sources(response: Any) -> list[ResearchSource]:
    sources: list[ResearchSource] = []
    seen_urls: set[str] = set()
    confidence_by_index = _extract_confidence_by_chunk_index(response)

    for candidate in getattr(response, "candidates", None) or []:
        grounding = getattr(candidate, "grounding_metadata", None)
        for index, chunk in enumerate(getattr(grounding, "grounding_chunks", None) or []):
            web = getattr(chunk, "web", None)
            if web is None:
                continue
            url = getattr(web, "uri", None)
            title = getattr(web, "title", None) or url or "Gemini grounded source"
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            sources.append(
                ResearchSource(
                    title=title,
                    url=url,
                    source_type="google_search",
                    confidence=confidence_by_index.get(index),
                )
            )

    return sources


def _extract_confidence_by_chunk_index(response: Any) -> dict[int, float]:
    confidence_by_index: dict[int, float] = {}
    for candidate in getattr(response, "candidates", None) or []:
        grounding = getattr(candidate, "grounding_metadata", None)
        for support in getattr(grounding, "grounding_supports", None) or []:
            indices = getattr(support, "grounding_chunk_indices", None) or []
            scores = getattr(support, "confidence_scores", None) or []
            for index, score in zip(indices, scores, strict=False):
                previous = confidence_by_index.get(index)
                confidence_by_index[index] = max(previous or 0.0, float(score))
    return confidence_by_index


def _extract_search_queries(response: Any) -> list[str]:
    queries: list[str] = []
    for candidate in getattr(response, "candidates", None) or []:
        grounding = getattr(candidate, "grounding_metadata", None)
        queries.extend(getattr(grounding, "web_search_queries", None) or [])
    return queries
