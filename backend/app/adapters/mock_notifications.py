from app.adapters.notifications import (
    ApprovalNotificationRequest,
    MarketTrendDigestNotificationRequest,
    NotificationAdapter,
    NotificationDelivery,
)


class MockNotificationAdapter(NotificationAdapter):
    provider = "mock-notifications"

    def send_approval_request(
        self,
        request: ApprovalNotificationRequest,
    ) -> list[NotificationDelivery]:
        return [
            NotificationDelivery(
                provider=self.provider,
                channel="mock",
                status="recorded",
                recipient="mock-reviewer",
                message_id=f"mock-approval-{request.task_id}",
                metadata={
                    "task_id": request.task_id,
                    "topic": request.topic,
                    "status": request.status,
                },
            )
        ]

    def send_market_trend_digest(
        self,
        request: MarketTrendDigestNotificationRequest,
    ) -> list[NotificationDelivery]:
        return [
            NotificationDelivery(
                provider=self.provider,
                channel="mock",
                status="recorded",
                recipient="mock-reviewer",
                message_id=f"mock-market-digest-{len(request.event_ids)}",
                metadata={
                    "title": request.title,
                    "event_ids": request.event_ids,
                    "summary_chars": len(request.summary),
                },
            )
        ]
