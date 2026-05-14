from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MediaGenerationRequest:
    prompt: str
    media_type: str
    aspect_ratio: str | None = None
    task_id: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class MediaGenerationResult:
    provider: str
    media_type: str
    status: str
    external_id: str | None = None
    file_url: str | None = None
    metadata: dict[str, Any] | None = None


class MediaAdapter(ABC):
    @abstractmethod
    def generate(self, request: MediaGenerationRequest) -> MediaGenerationResult:
        """Start or perform media generation."""
