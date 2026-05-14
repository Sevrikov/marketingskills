from decimal import Decimal

from app.adapters.price_monitor import (
    PriceExtractionResult,
    PriceMonitorAdapter,
    PriceMonitorRequest,
)


class MockPriceMonitorAdapter(PriceMonitorAdapter):
    provider = "mock-price-monitor"

    def capture(self, request: PriceMonitorRequest) -> PriceExtractionResult:
        currency = request.expected_currency or "UAH"
        return PriceExtractionResult(
            status="captured",
            price=Decimal("999.00"),
            currency=currency,
            availability="in_stock",
            title=f"Mock monitored page for {request.url}",
            sku="mock-sku",
            confidence=Decimal("0.900"),
            raw={
                "provider": self.provider,
                "url": request.url,
                "extractor_type": request.extractor_type,
            },
        )
