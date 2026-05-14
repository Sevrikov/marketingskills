import hashlib
import hmac
import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.approval import ApprovalPayload
from app.services.approvals import TaskNotReadyForApproval, approve_task, request_task_rewrite
from app.services.content_tasks import InvalidTaskTransition, get_content_task, log_task_event

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/viber")
async def viber_webhook_endpoint(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_viber_content_signature: str | None = Header(default=None),
):
    body = await request.body()
    _verify_viber_signature(body, x_viber_content_signature, settings)
    payload = json.loads(body.decode("utf-8")) if body else {}

    event = payload.get("event")
    if event in {"webhook", "delivered", "seen", "failed", "subscribed", "unsubscribed"}:
        return {"status": "ignored", "event": event}

    if event != "message":
        return {"status": "ignored", "event": event or "unknown"}

    command = _extract_viber_command(payload)
    if command is None:
        return {"status": "ignored", "event": event, "reason": "no approval command"}

    action, task_id = command
    task = get_content_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    reviewer = _reviewer_name(payload)
    approval_payload = ApprovalPayload(
        reviewer=reviewer,
        comment=f"Viber command: {action}",
    )
    try:
        if action == "approve":
            updated_task = approve_task(db, task, approval_payload)
            decision = "approved"
        else:
            updated_task = request_task_rewrite(db, task, approval_payload)
            decision = "rewrite_requested"
    except (TaskNotReadyForApproval, InvalidTaskTransition) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    log_task_event(
        db,
        updated_task,
        event_type="approval_webhook_received",
        from_status=updated_task.status,
        to_status=updated_task.status,
        step="viber_webhook",
        message=f"Viber approval webhook processed: {decision}.",
        created_by=reviewer,
        metadata_json={
            "provider": "viber",
            "event": event,
            "decision": decision,
            "message_token": payload.get("message_token"),
            "sender_id": payload.get("sender", {}).get("id"),
        },
    )
    db.commit()
    return {
        "status": "processed",
        "provider": "viber",
        "task_id": updated_task.id,
        "task_status": updated_task.status,
        "decision": decision,
    }


def _verify_viber_signature(
    body: bytes,
    signature: str | None,
    settings: Settings,
) -> None:
    if not settings.viber_webhook_secret_required:
        return
    if not settings.viber_auth_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Viber auth token is not configured.",
        )
    if not signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing signature.")

    digest = hmac.new(settings.viber_auth_token.encode("utf-8"), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(digest, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature.")


def _extract_viber_command(payload: dict) -> tuple[str, str] | None:
    message = payload.get("message") or {}
    text = str(message.get("text") or "").strip()
    if ":" not in text:
        return None
    action, task_id = text.split(":", 1)
    action = action.strip().lower()
    task_id = task_id.strip()
    if action not in {"approve", "rewrite"} or not task_id:
        return None
    return action, task_id


def _reviewer_name(payload: dict) -> str:
    sender = payload.get("sender") or {}
    return sender.get("name") or sender.get("id") or "viber-reviewer"
