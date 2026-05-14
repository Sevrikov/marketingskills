import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.adapters.source_provider import (
    SourceDocument,
    SourceProvider,
    SourceSearchRequest,
    SourceSearchResult,
)
from app.config import Settings


class TavilySourceProviderError(RuntimeError):
    pass


class TavilySourceProvider(SourceProvider):
    provider = "tavily"
    endpoint = "https://api.tavily.com/search"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def search(self, request: SourceSearchRequest) -> SourceSearchResult:
        if not self.settings.tavily_api_key:
            raise TavilySourceProviderError(
                "TAVILY_API_KEY is not configured. Add it to local .env, never to git."
            )

        payload = {
            "query": request.query,
            "topic": request.topic,
            "search_depth": request.search_depth,
            "max_results": max(0, min(request.max_results, 20)),
            "include_answer": self._include_answer(),
            "include_raw_content": request.include_raw_content,
            "include_images": False,
            "include_favicon": True,
            "include_usage": True,
        }
        if request.country:
            payload["country"] = request.country

        response = self._post(payload)
        documents = [
            SourceDocument(
                title=str(item.get("title") or item.get("url") or "Untitled source"),
                url=item.get("url"),
                snippet=item.get("content"),
                content=item.get("raw_content") or item.get("content"),
                score=float(item["score"]) if item.get("score") is not None else None,
                source_type="tavily_search",
                raw={
                    "favicon": item.get("favicon"),
                    "published_date": item.get("published_date"),
                },
            )
            for item in response.get("results", [])
            if isinstance(item, dict)
        ]
        return SourceSearchResult(
            provider=self.provider,
            query=str(response.get("query") or request.query),
            answer=response.get("answer"),
            documents=documents,
            external_id=response.get("request_id"),
            usage=response.get("usage"),
            raw={"response_time": response.get("response_time")},
        )

    def _post(self, payload: dict) -> dict:
        http_request = Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.settings.tavily_api_key}",
            },
            method="POST",
        )
        try:
            with urlopen(http_request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            raise TavilySourceProviderError(
                f"Tavily HTTP error: {exc.code} {message[:300]}"
            ) from exc
        except URLError as exc:
            raise TavilySourceProviderError(f"Tavily network error: {exc.reason}") from exc

    def _include_answer(self) -> str | bool:
        value = self.settings.tavily_include_answer.strip().lower()
        if value == "false":
            return False
        if value == "true":
            return True
        return value
