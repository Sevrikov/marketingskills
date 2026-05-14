from decimal import Decimal, InvalidOperation
from typing import Any

from app.adapters.price_monitor import (
    PriceExtractionResult,
    PriceMonitorAdapter,
    PriceMonitorRequest,
)
from app.config import Settings


class PlaywrightPriceMonitorError(RuntimeError):
    pass


class PlaywrightPriceMonitorAdapter(PriceMonitorAdapter):
    provider = "playwright-price-monitor"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def capture(self, request: PriceMonitorRequest) -> PriceExtractionResult:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise PlaywrightPriceMonitorError(
                "playwright package is not installed in the current runtime."
            ) from exc

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(
                    user_agent=self.settings.price_monitor_user_agent,
                )
                page.goto(
                    request.url,
                    wait_until="networkidle",
                    timeout=self.settings.price_monitor_timeout_seconds * 1000,
                )
                raw = page.evaluate(request.extractor_script)
            finally:
                browser.close()

        if not isinstance(raw, dict):
            return PriceExtractionResult(
                status="failed",
                raw={"extractor_result": raw},
                error_message="Extractor did not return an object.",
            )
        return _result_from_raw(raw)


def _result_from_raw(raw: dict[str, Any]) -> PriceExtractionResult:
    return PriceExtractionResult(
        status="captured" if raw.get("price") is not None else "missing_price",
        price=_decimal_or_none(raw.get("price")),
        currency=str(raw["currency"]) if raw.get("currency") else None,
        availability=str(raw["availability"]) if raw.get("availability") else None,
        title=str(raw["title"]) if raw.get("title") else None,
        sku=str(raw["sku"]) if raw.get("sku") else None,
        confidence=_decimal_or_none(raw.get("confidence")),
        raw=raw,
    )


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
