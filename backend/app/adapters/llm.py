from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LLMRequest:
    prompt: str
    system_prompt: str | None = None
    model: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    provider: str
    raw: dict[str, Any] | None = None


class LLMAdapter(ABC):
    @abstractmethod
    def generate_text(self, request: LLMRequest) -> LLMResponse:
        """Generate text from an LLM provider."""
