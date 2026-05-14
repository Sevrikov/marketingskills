from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SourceSearchRequest:
    query: str
    task_id: str | None = None
    max_results: int = 5
    include_raw_content: str | bool = "markdown"
    search_depth: str = "basic"
    topic: str = "general"
    country: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class SourceDocument:
    title: str
    url: str | None = None
    snippet: str | None = None
    content: str | None = None
    score: float | None = None
    source_type: str = "web"
    raw: dict[str, Any] | None = None


@dataclass(frozen=True)
class SourceSearchResult:
    provider: str
    query: str
    documents: list[SourceDocument]
    answer: str | None = None
    external_id: str | None = None
    usage: dict[str, Any] | None = None
    raw: dict[str, Any] | None = None


class SourceProvider(ABC):
    @abstractmethod
    def search(self, request: SourceSearchRequest) -> SourceSearchResult:
        """Collect source documents for a research task."""
