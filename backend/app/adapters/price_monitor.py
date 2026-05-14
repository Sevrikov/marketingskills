from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


GENERIC_PRICE_EXTRACTOR_JS = r"""(() => {
  const text = document.body ? document.body.innerText : "";
  const priceMatch = text.match(/(\d[\d\s.,]*)\s*(₴|грн|UAH|\$|USD|€|EUR)/i);
  const availabilityText = text.toLowerCase();
  const availability = /в наявності|в наличии|in stock|available/.test(availabilityText)
    ? "in_stock"
    : (/немає|нет в наличии|out of stock|unavailable/.test(availabilityText) ? "out_of_stock" : "unknown");
  return {
    title: document.title || null,
    price: priceMatch ? priceMatch[1].replace(/\s/g, "").replace(",", ".") : null,
    currency: priceMatch ? priceMatch[2] : null,
    availability,
    sku: null,
    confidence: priceMatch ? 0.6 : 0.1,
    url: location.href
  };
})()"""


@dataclass(frozen=True)
class PriceMonitorRequest:
    url: str
    extractor_script: str
    extractor_type: str = "generic_js"
    expected_currency: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class PriceExtractionResult:
    status: str
    price: Decimal | None = None
    currency: str | None = None
    availability: str | None = None
    title: str | None = None
    sku: str | None = None
    confidence: Decimal | None = None
    raw: dict[str, Any] | None = None
    error_message: str | None = None


class PriceMonitorAdapter(ABC):
    @abstractmethod
    def capture(self, request: PriceMonitorRequest) -> PriceExtractionResult:
        """Open or simulate a page and return extracted price data."""
