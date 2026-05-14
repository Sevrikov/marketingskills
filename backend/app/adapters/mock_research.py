from app.adapters.research import ResearchAdapter, ResearchReport, ResearchRequest, ResearchSource


class MockResearchAdapter(ResearchAdapter):
    provider = "mock-research"

    def run_research(self, request: ResearchRequest) -> ResearchReport:
        source_corpus = (request.metadata or {}).get("source_corpus_markdown") or ""
        source_note = (
            "\n\n## Collected source corpus\n\n" + source_corpus
            if source_corpus
            else ""
        )
        return ResearchReport(
            title=f"Mock research: {request.query}",
            markdown=(
                f"# Mock research report\n\n"
                f"Query: {request.query}\n\n"
                "This is a deterministic mock research report for pipeline development."
                f"{source_note}"
            ),
            sources=[
                ResearchSource(
                    title="Mock source",
                    url="https://example.com/mock-source",
                    source_type="mock",
                    confidence=1.0,
                )
            ],
            normalized={
                "query": request.query,
                "mode": request.mode,
                "facts": [],
                "hypotheses": [],
                "source_provider": (request.metadata or {}).get("source_provider"),
            },
            provider=self.provider,
            external_id=f"mock-research-{request.task_id or 'no-task'}",
        )
