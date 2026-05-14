from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IndexingRequest:
    url: str
    reason: str = "content_published"
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class IndexingResult:
    provider: str
    url: str
    status: str
    message: str | None = None
    raw: dict[str, Any] | None = None


class SearchConsoleAdapter(ABC):
    @abstractmethod
    def request_indexing(self, request: IndexingRequest) -> IndexingResult:
        """Request or record indexing workflow for a URL."""
