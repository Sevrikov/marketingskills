from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ApprovalNotificationRequest:
    task_id: str
    task_type: str
    topic: str | None
    language: str
    status: str
    console_url: str | None = None
    package_url: str | None = None


@dataclass(frozen=True)
class MarketTrendDigestNotificationRequest:
    title: str
    summary: str
    event_ids: list[str]
    console_url: str | None = None


@dataclass(frozen=True)
class NotificationDelivery:
    provider: str
    channel: str
    status: str
    recipient: str
    message_id: str | None = None
    metadata: dict = field(default_factory=dict)


class NotificationAdapter(ABC):
    provider: str

    @abstractmethod
    def send_approval_request(
        self,
        request: ApprovalNotificationRequest,
    ) -> list[NotificationDelivery]:
        pass

    def send_market_trend_digest(
        self,
        request: MarketTrendDigestNotificationRequest,
    ) -> list[NotificationDelivery]:
        pass
