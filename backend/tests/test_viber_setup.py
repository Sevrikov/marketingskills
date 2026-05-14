import pytest

from app.config import Settings
from app.services.viber_setup import (
    ViberSetupError,
    build_viber_webhook_payload,
    validate_viber_webhook_url,
)


def test_build_viber_webhook_payload_uses_safe_default_privacy_flags():
    payload = build_viber_webhook_payload(
        "https://example.com/api/webhooks/viber",
        "message, conversation_started, failed",
    )

    assert payload == {
        "url": "https://example.com/api/webhooks/viber",
        "event_types": ["message", "conversation_started", "failed"],
        "send_name": False,
        "send_photo": False,
    }


def test_viber_webhook_url_must_be_public_https():
    for url in [
        "http://example.com/api/webhooks/viber",
        "https://localhost/api/webhooks/viber",
        "https://127.0.0.1/api/webhooks/viber",
    ]:
        with pytest.raises(ViberSetupError):
            validate_viber_webhook_url(url)


def test_viber_webhook_payload_rejects_unknown_event_type():
    with pytest.raises(ViberSetupError, match="Unsupported"):
        build_viber_webhook_payload("https://example.com/api/webhooks/viber", "message,typo")


def test_viber_settings_expose_webhook_setup_defaults():
    settings = Settings()

    assert settings.viber_webhook_event_types == (
        "message,conversation_started,subscribed,unsubscribed,failed"
    )
    assert settings.viber_webhook_secret_required is False
