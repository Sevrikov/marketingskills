from app.adapters.search_console import IndexingRequest, IndexingResult, SearchConsoleAdapter


class MockSearchConsoleAdapter(SearchConsoleAdapter):
    provider = "mock-search-console"

    def request_indexing(self, request: IndexingRequest) -> IndexingResult:
        return IndexingResult(
            provider=self.provider,
            url=request.url,
            status="recorded",
            message="Mock indexing request recorded. No external API call was made.",
            raw={"reason": request.reason},
        )
