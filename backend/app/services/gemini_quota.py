from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from app.config import Settings


class GeminiQuotaError(RuntimeError):
    """Raised when the local Gemini quota governor blocks a call."""


class GeminiQuotaGovernor:
    def __init__(
        self,
        settings: Settings,
        now_func: Callable[[], datetime] | None = None,
    ) -> None:
        self.settings = settings
        self._now_func = now_func or (lambda: datetime.now(UTC))

    def select_model(self, candidates: list[str]) -> str:
        models = _dedupe_models(candidates)
        if not models:
            raise GeminiQuotaError("No Gemini models were configured.")
        if not self.settings.enable_gemini_quota_governor:
            return models[0]

        blocked: list[str] = []
        ledger = self._read_ledger()
        day = self._today()
        daily = ledger.setdefault("days", {}).setdefault(day, {"models": {}})

        for model in models:
            state = daily.setdefault("models", {}).setdefault(model, _empty_model_state())
            limit = self.daily_limits().get(model)
            if state.get("quota_blocked"):
                blocked.append(f"{model}: quota error already seen today")
                continue
            if limit is not None and int(state.get("success", 0)) >= limit:
                blocked.append(f"{model}: local daily limit {limit} reached")
                continue
            blocked_until = _parse_datetime(state.get("blocked_until"))
            if blocked_until and blocked_until > self._now():
                blocked.append(f"{model}: cooling down until {blocked_until.isoformat()}")
                continue
            return model

        raise GeminiQuotaError("All Gemini models are locally blocked: " + "; ".join(blocked))

    def record_success(
        self,
        model: str,
        input_chars: int = 0,
        output_chars: int = 0,
    ) -> None:
        if not self.settings.enable_gemini_quota_governor:
            return
        ledger, state = self._ledger_state(model)
        state["success"] = int(state.get("success", 0)) + 1
        state["input_chars"] = int(state.get("input_chars", 0)) + max(input_chars, 0)
        state["output_chars"] = int(state.get("output_chars", 0)) + max(output_chars, 0)
        state["last_status"] = "success"
        state["last_seen_at"] = self._now().isoformat()
        state["blocked_until"] = None
        self._write_ledger(ledger)

    def record_failure(self, model: str, exc: Exception) -> None:
        if not self.settings.enable_gemini_quota_governor:
            return
        ledger, state = self._ledger_state(model)
        state["failed"] = int(state.get("failed", 0)) + 1
        state["last_error"] = _short_error(exc)
        state["last_seen_at"] = self._now().isoformat()

        if _is_quota_error(exc):
            state["quota_errors"] = int(state.get("quota_errors", 0)) + 1
            state["quota_blocked"] = True
            state["blocked_until"] = self._end_of_day().isoformat()
            state["last_status"] = "quota_error"
        elif _is_unavailable_error(exc):
            state["unavailable_errors"] = int(state.get("unavailable_errors", 0)) + 1
            state["blocked_until"] = (
                self._now()
                + timedelta(seconds=max(self.settings.gemini_unavailable_cooldown_seconds, 1))
            ).isoformat()
            state["last_status"] = "unavailable"
        else:
            state["last_status"] = "error"

        self._write_ledger(ledger)

    def snapshot(self) -> dict[str, Any]:
        ledger = self._read_ledger()
        return ledger.get("days", {}).get(self._today(), {"models": {}})

    def daily_limits(self) -> dict[str, int]:
        limits: dict[str, int] = {}
        for part in self.settings.gemini_daily_model_limits.split(","):
            if not part.strip() or "=" not in part:
                continue
            model, raw_limit = part.split("=", 1)
            try:
                limit = int(raw_limit.strip())
            except ValueError:
                continue
            limits[model.strip()] = limit
        return limits

    def _ledger_state(self, model: str) -> tuple[dict[str, Any], dict[str, Any]]:
        ledger = self._read_ledger()
        day = self._today()
        daily = ledger.setdefault("days", {}).setdefault(day, {"models": {}})
        state = daily.setdefault("models", {}).setdefault(model, _empty_model_state())
        return ledger, state

    def _read_ledger(self) -> dict[str, Any]:
        path = self._ledger_path()
        if not path.exists():
            return {"version": 1, "days": {}}
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"version": 1, "days": {}}
        if not isinstance(loaded, dict):
            return {"version": 1, "days": {}}
        loaded.setdefault("version", 1)
        loaded.setdefault("days", {})
        return loaded

    def _write_ledger(self, ledger: dict[str, Any]) -> None:
        path = self._ledger_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(ledger, indent=2, sort_keys=True), encoding="utf-8")

    def _ledger_path(self) -> Path:
        path = Path(self.settings.gemini_quota_ledger_path)
        if path.is_absolute():
            return path
        return Path.cwd() / path

    def _today(self) -> str:
        return self._now().date().isoformat()

    def _now(self) -> datetime:
        value = self._now_func()
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _end_of_day(self) -> datetime:
        today = self._now().date()
        return datetime(today.year, today.month, today.day, tzinfo=UTC) + timedelta(days=1)


def build_gemini_candidates(primary_model: str | None, configured_models: str) -> list[str]:
    candidates = [primary_model] if primary_model else []
    candidates.extend(model.strip() for model in configured_models.split(",") if model.strip())
    return _dedupe_models(candidates)


def should_try_next_gemini_model(exc: Exception) -> bool:
    return _is_quota_error(exc) or _is_unavailable_error(exc)


def _dedupe_models(models: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for model in models:
        if not model:
            continue
        value = model.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _empty_model_state() -> dict[str, Any]:
    return {
        "success": 0,
        "failed": 0,
        "quota_errors": 0,
        "unavailable_errors": 0,
        "input_chars": 0,
        "output_chars": 0,
        "quota_blocked": False,
        "blocked_until": None,
        "last_status": None,
        "last_error": None,
        "last_seen_at": None,
    }


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _is_quota_error(exc: Exception) -> bool:
    message = str(exc)
    return "429" in message or "RESOURCE_EXHAUSTED" in message


def _is_unavailable_error(exc: Exception) -> bool:
    message = str(exc)
    return "503" in message or "UNAVAILABLE" in message


def _short_error(exc: Exception) -> str:
    message = str(exc).replace("\n", " ").strip()
    return message[:500]
