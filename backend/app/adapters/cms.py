from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PublishRequest:
    title: str
    body_html: str
    body_markdown: str | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    schema_json: dict[str, Any] | None = None
    product_card_json: dict[str, Any] | None = None
    media_assets_json: list[dict[str, Any]] | None = None
    status: str = "draft"
    destination_type: str = "generic_cms"


@dataclass(frozen=True)
class PublishResult:
    provider: str
    external_id: str
    url: str | None
    status: str
    raw: dict[str, Any] | None = None


class CMSAdapter(ABC):
    provider: str

    @abstractmethod
    def prepare_payload(self, request: PublishRequest) -> dict[str, Any]:
        """Prepare a destination-specific payload without publishing."""

    @abstractmethod
    def publish(self, request: PublishRequest) -> PublishResult:
        """Publish or export content."""
