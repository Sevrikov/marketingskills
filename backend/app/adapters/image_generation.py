from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ImageGenerationRequest:
    asset_id: str
    slot: str
    asset_type: str
    prompt: str
    dimensions: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class ImageGenerationResult:
    provider: str
    storage_uri: str
    model: str | None = None
    prompt: str | None = None
    metadata: dict[str, Any] | None = None


class ImageGenerationAdapter(ABC):
    provider: str

    @abstractmethod
    def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        """Generate or prepare an image asset and return its storage URI."""
