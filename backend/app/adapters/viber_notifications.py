import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.adapters.notifications import (
    ApprovalNotificationRequest,
    MarketTrendDigestNotificationRequest,
    NotificationAdapter,
    NotificationDelivery,
)
from app.config import Settings


class ViberNotificationError(RuntimeError):
    pass


class ViberNotificationAdapter(NotificationAdapter):
    provider = "viber"
    endpoint = "https://chatapi.viber.com/pa/send_message"

    def __init__(self, settings: Settings) -> None:
        self.auth_token = settings.viber_auth_token
        self.reviewer_ids = [
            reviewer_id.strip()
            for reviewer_id in settings.viber_reviewer_ids.split(",")
            if reviewer_id.strip()
        ]
        self.sender_name = settings.viber_sender_name
        self.console_base_url = settings.operator_console_url

    def send_approval_request(
        self,
        request: ApprovalNotificationRequest,
    ) -> list[NotificationDelivery]:
        if not self.auth_token:
            raise ViberNotificationError("Viber auth token is not configured.")
        if not self.reviewer_ids:
            raise ViberNotificationError("Viber reviewer ids are not configured.")

        deliveries = []
        for reviewer_id in self.reviewer_ids:
            response = self._send_message(reviewer_id, request)
            deliveries.append(
                NotificationDelivery(
                    provider=self.provider,
                    channel="viber",
                    status=response.get("status_message", "sent"),
                    recipient=reviewer_id,
                    message_id=str(response.get("message_token"))
                    if response.get("message_token") is not None
                    else None,
                    metadata={
                        "billing_status": response.get("billing_status"),
                        "chat_hostname": response.get("chat_hostname"),
                    },
                )
            )
        return deliveries

    def send_market_trend_digest(
        self,
        request: MarketTrendDigestNotificationRequest,
    ) -> list[NotificationDelivery]:
        if not self.auth_token:
            raise ViberNotificationError("Viber auth token is not configured.")
        if not self.reviewer_ids:
            raise ViberNotificationError("Viber reviewer ids are not configured.")

        deliveries = []
        for reviewer_id in self.reviewer_ids:
            response = self._send_digest_message(reviewer_id, request)
            deliveries.append(
                NotificationDelivery(
                    provider=self.provider,
                    channel="viber",
                    status=response.get("status_message", "sent"),
                    recipient=reviewer_id,
                    message_id=str(response.get("message_token"))
                    if response.get("message_token") is not None
                    else None,
                    metadata={
                        "billing_status": response.get("billing_status"),
                        "chat_hostname": response.get("chat_hostname"),
                        "event_ids": request.event_ids,
                    },
                )
            )
        return deliveries

    def build_payload(self, receiver: str, request: ApprovalNotificationRequest) -> dict:
        console_url = request.console_url or self._task_console_url(request.task_id)
        text = "\n".join(
            [
                "Content approval request",
                f"Task: {request.task_id}",
                f"Type: {request.task_type}",
                f"Language: {request.language}",
                f"Topic: {request.topic or 'No topic'}",
                "",
                "Choose an action below or open the operator console.",
            ]
        )
        return {
            "receiver": receiver,
            "min_api_version": 7,
            "sender": {"name": self.sender_name},
            "tracking_data": request.task_id,
            "type": "text",
            "text": text[:7000],
            "keyboard": {
                "Type": "keyboard",
                "DefaultHeight": False,
                "Buttons": [
                    self._reply_button("Approve", f"approve:{request.task_id}", "#2E7D32"),
                    self._reply_button("Rewrite", f"rewrite:{request.task_id}", "#B45309"),
                    self._url_button("Open console", console_url),
                ],
            },
        }

    def build_digest_payload(
        self,
        receiver: str,
        request: MarketTrendDigestNotificationRequest,
    ) -> dict:
        text = "\n\n".join(
            part for part in [request.title, request.summary, request.console_url] if part
        )
        return {
            "receiver": receiver,
            "min_api_version": 7,
            "sender": {"name": self.sender_name},
            "tracking_data": ",".join(request.event_ids[:10]),
            "type": "text",
            "text": text[:7000],
        }

    def _send_message(self, receiver: str, request: ApprovalNotificationRequest) -> dict:
        payload = json.dumps(self.build_payload(receiver, request)).encode("utf-8")
        return self._post_payload(payload)

    def _send_digest_message(
        self,
        receiver: str,
        request: MarketTrendDigestNotificationRequest,
    ) -> dict:
        payload = json.dumps(self.build_digest_payload(receiver, request)).encode("utf-8")
        return self._post_payload(payload)

    def _post_payload(self, payload: bytes) -> dict:
        http_request = Request(
            self.endpoint,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-Viber-Auth-Token": self.auth_token or "",
            },
            method="POST",
        )
        try:
            with urlopen(http_request, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise ViberNotificationError(f"Viber HTTP error: {exc.code}") from exc
        except URLError as exc:
            raise ViberNotificationError(f"Viber network error: {exc.reason}") from exc

        if result.get("status") != 0:
            raise ViberNotificationError(
                f"Viber send failed: {result.get('status_message', 'unknown error')}"
            )
        return result

    def _task_console_url(self, task_id: str) -> str:
        base_url = self.console_base_url.rstrip("/")
        return f"{base_url}/?task_id={task_id}"

    @staticmethod
    def _reply_button(text: str, action_body: str, bg_color: str) -> dict:
        return {
            "Columns": 2,
            "Rows": 1,
            "ActionType": "reply",
            "ActionBody": action_body,
            "Text": f"<font color=#ffffff>{text}</font>",
            "TextSize": "regular",
            "BgColor": bg_color,
        }

    @staticmethod
    def _url_button(text: str, url: str) -> dict:
        return {
            "Columns": 2,
            "Rows": 1,
            "ActionType": "open-url",
            "ActionBody": url,
            "Text": f"<font color=#ffffff>{text}</font>",
            "TextSize": "regular",
            "BgColor": "#2563EB",
        }
