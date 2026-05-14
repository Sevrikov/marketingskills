from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ResearchRequest:
    query: str
    mode: str = "standard"
    product_id: str | None = None
    task_id: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class ResearchSource:
    title: str
    url: str | None = None
    source_type: str = "web"
    confidence: float | None = None


@dataclass(frozen=True)
class ResearchReport:
    title: str
    markdown: str
    sources: list[ResearchSource]
    normalized: dict[str, Any] | None = None
    provider: str = "unknown"
    external_id: str | None = None


class ResearchAdapter(ABC):
    @abstractmethod
    def run_research(self, request: ResearchRequest) -> ResearchReport:
        """Run a research task and return a report."""
