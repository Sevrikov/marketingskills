from pydantic import BaseModel, Field


class NotificationDeliveryRead(BaseModel):
    provider: str
    channel: str
    status: str
    recipient: str
    message_id: str | None = None
    metadata: dict = Field(default_factory=dict)


class ApprovalNotificationResult(BaseModel):
    task_id: str
    provider: str
    channel: str
    deliveries: list[NotificationDeliveryRead]
