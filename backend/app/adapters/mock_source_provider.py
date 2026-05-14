from app.adapters.source_provider import (
    SourceDocument,
    SourceProvider,
    SourceSearchRequest,
    SourceSearchResult,
)


class MockSourceProvider(SourceProvider):
    provider = "mock-source-provider"

    def search(self, request: SourceSearchRequest) -> SourceSearchResult:
        return SourceSearchResult(
            provider=self.provider,
            query=request.query,
            answer=f"Mock source corpus for {request.query}",
            documents=[
                SourceDocument(
                    title="Mock market overview",
                    url="https://example.com/mock-market-overview",
                    snippet="Market overview snippet for local pipeline development.",
                    content=(
                        "This mock source describes buyer demand, comparison criteria, "
                        "and common objections for the requested research topic."
                    ),
                    score=1.0,
                    source_type="mock_source",
                ),
                SourceDocument(
                    title="Mock competitor notes",
                    url="https://example.com/mock-competitors",
                    snippet="Competitor and positioning notes.",
                    content=(
                        "This mock source lists competitor angles, feature tradeoffs, "
                        "and content opportunities for an e-commerce marketing report."
                    ),
                    score=0.9,
                    source_type="mock_source",
                ),
            ][: max(request.max_results, 0)],
            external_id=f"mock-source-search-{request.task_id or 'no-task'}",
            usage={"credits": 0},
        )
