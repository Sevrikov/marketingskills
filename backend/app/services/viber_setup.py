import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app.config import Settings


VIBER_SET_WEBHOOK_ENDPOINT = "https://chatapi.viber.com/pa/set_webhook"
VIBER_ALLOWED_EVENT_TYPES = {
    "delivered",
    "seen",
    "failed",
    "subscribed",
    "unsubscribed",
    "conversation_started",
    "message",
}


class ViberSetupError(RuntimeError):
    pass


@dataclass(frozen=True)
class ViberWebhookSetupResult:
    status: int
    status_message: str
    event_types: list[str]
    raw: dict


def build_viber_webhook_payload(
    webhook_url: str,
    event_types: str,
    send_name: bool = False,
    send_photo: bool = False,
) -> dict:
    validate_viber_webhook_url(webhook_url)
    return {
        "url": webhook_url,
        "event_types": _parse_event_types(event_types),
        "send_name": send_name,
        "send_photo": send_photo,
    }


def set_viber_webhook(
    settings: Settings,
    webhook_url: str,
    event_types: str | None = None,
    send_name: bool = False,
    send_photo: bool = False,
) -> ViberWebhookSetupResult:
    if not settings.viber_auth_token:
        raise ViberSetupError("VIBER_AUTH_TOKEN is not configured.")

    payload = build_viber_webhook_payload(
        webhook_url,
        event_types or settings.viber_webhook_event_types,
        send_name=send_name,
        send_photo=send_photo,
    )
    response = _post_to_viber(settings.viber_auth_token, payload)
    return ViberWebhookSetupResult(
        status=int(response.get("status", -1)),
        status_message=str(response.get("status_message", "unknown")),
        event_types=list(response.get("event_types", [])),
        raw=response,
    )


def remove_viber_webhook(settings: Settings) -> ViberWebhookSetupResult:
    if not settings.viber_auth_token:
        raise ViberSetupError("VIBER_AUTH_TOKEN is not configured.")

    response = _post_to_viber(settings.viber_auth_token, {"url": ""})
    return ViberWebhookSetupResult(
        status=int(response.get("status", -1)),
        status_message=str(response.get("status_message", "unknown")),
        event_types=list(response.get("event_types", [])),
        raw=response,
    )


def validate_viber_webhook_url(webhook_url: str) -> None:
    parsed = urlparse(webhook_url)
    if parsed.scheme != "https":
        raise ViberSetupError("Viber webhook URL must use HTTPS.")
    if not parsed.netloc:
        raise ViberSetupError("Viber webhook URL must include a public host.")
    host = parsed.hostname or ""
    if host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".local"):
        raise ViberSetupError("Viber webhook URL must be public, not localhost.")
    if not parsed.path:
        raise ViberSetupError("Viber webhook URL must include the webhook path.")


def _post_to_viber(auth_token: str, payload: dict) -> dict:
    request = Request(
        VIBER_SET_WEBHOOK_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Viber-Auth-Token": auth_token,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise ViberSetupError(f"Viber set_webhook HTTP error: {exc.code}") from exc
    except URLError as exc:
        raise ViberSetupError(f"Viber set_webhook network error: {exc.reason}") from exc


def _parse_event_types(event_types: str) -> list[str]:
    values = [event.strip() for event in event_types.split(",") if event.strip()]
    if not values:
        raise ViberSetupError("At least one Viber webhook event type must be configured.")
    unsupported = sorted(set(values) - VIBER_ALLOWED_EVENT_TYPES)
    if unsupported:
        raise ViberSetupError(f"Unsupported Viber webhook event types: {', '.join(unsupported)}")
    return values
