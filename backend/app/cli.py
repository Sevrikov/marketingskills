import argparse
import json
import time

from app.adapters.factory import (
    build_notification_adapter,
    build_price_monitor_adapter,
    build_research_adapter,
)
from app.adapters.research import ResearchRequest
from app.config import get_settings
from app.db.base import Base
from app.db.session import SessionLocal
from app.models import (  # noqa: F401
    agent_skill,
    article_asset,
    article_review_checkpoint,
    content_draft,
    content_opportunity,
    content_research_report,
    content_task,
    media_brief,
    market_digest_batch,
    monitored_source,
    notification_policy,
    price_change_event,
    price_group,
    price_market_index,
    price_snapshot,
    price_trend_event,
    product,
    product_content_profile,
    prompt_template,
    publish_package,
    publication_preview,
    runtime_setting,
    scheduled_job,
    scheduled_job_run,
    task_event,
)
from app.seed.load_prompts import load_seed_prompts
from app.services.gemini_quota import GeminiQuotaGovernor
from app.services.price_monitor import run_due_price_monitor_checks, run_market_digest_batch
from app.services.scheduler import run_due_scheduled_jobs
from app.services.skill_registry import sync_agent_skills
from app.services.viber_setup import (
    build_viber_webhook_payload,
    remove_viber_webhook,
    set_viber_webhook,
)


def init_db() -> None:
    from app.db.session import engine

    Base.metadata.create_all(bind=engine)
    print("Database tables created.")


def seed_prompts() -> None:
    db = SessionLocal()
    try:
        created = load_seed_prompts(db)
    finally:
        db.close()
    print(f"Seed prompts created: {created}")


def sync_skills() -> None:
    db = SessionLocal()
    try:
        result = sync_agent_skills(db, get_settings().skill_registry_root)
    finally:
        db.close()
    print(
        "Skill sync: "
        f"scanned={result.scanned} upserted={result.upserted} archived={result.archived}"
    )


def smoke_gemini_research(query: str) -> None:
    settings = get_settings()
    if not settings.enable_google_smoke_tests:
        raise SystemExit("Refusing real Google call: set ENABLE_GOOGLE_SMOKE_TESTS=true.")
    if settings.research_provider != "gemini":
        raise SystemExit("Refusing real Google call: set RESEARCH_PROVIDER=gemini.")
    if not settings.google_api_key:
        raise SystemExit("Refusing real Google call: GOOGLE_API_KEY is not configured.")

    models = _gemini_smoke_models(settings)
    errors: list[str] = []
    report = None
    selected_model = None
    for model in models:
        settings.gemini_research_model = model
        adapter = build_research_adapter(settings)
        try:
            report = adapter.run_research(
                ResearchRequest(
                    query=query,
                    mode="smoke_test",
                    task_id="manual-smoke-test",
                    metadata={"purpose": "connectivity_check", "model": model},
                )
            )
            selected_model = report.normalized.get("model", model)
            break
        except Exception as exc:
            errors.append(f"{model}: {exc}")

    if report is None or selected_model is None:
        raise SystemExit("Gemini smoke test failed for all models:\n" + "\n".join(errors))

    print(f"Provider: {report.provider}")
    print(f"Model: {selected_model}")
    print(f"Title: {report.title}")
    print(f"External ID: {report.external_id or 'n/a'}")
    print(f"Markdown chars: {len(report.markdown)}")
    print(f"Sources: {len(report.sources)}")
    for index, source in enumerate(report.sources[:5], start=1):
        print(f"{index}. {source.title} | {source.url or 'no-url'}")


def gemini_quota_status() -> None:
    governor = GeminiQuotaGovernor(get_settings())
    snapshot = governor.snapshot()
    limits = governor.daily_limits()
    models = snapshot.get("models", {})
    if not models:
        print("No Gemini calls recorded for today.")
        return

    for model, state in sorted(models.items()):
        limit = limits.get(model)
        success = state.get("success", 0)
        usage = f"{success} / {limit}" if limit is not None else str(success)
        print(
            f"{model}: success={usage} failed={state.get('failed', 0)} "
            f"last_status={state.get('last_status') or 'n/a'} "
            f"blocked_until={state.get('blocked_until') or 'n/a'}"
        )


def viber_webhook_payload(webhook_url: str | None) -> None:
    settings = get_settings()
    url = webhook_url or settings.viber_webhook_public_url
    if not url:
        raise SystemExit("Pass --url or configure VIBER_WEBHOOK_PUBLIC_URL.")
    payload = build_viber_webhook_payload(url, settings.viber_webhook_event_types)
    print(json.dumps(payload, indent=2, sort_keys=True))


def viber_set_webhook(webhook_url: str | None, confirm_real_call: bool) -> None:
    if not confirm_real_call:
        raise SystemExit("Refusing real Viber call: pass --confirm-real-call.")
    settings = get_settings()
    url = webhook_url or settings.viber_webhook_public_url
    if not url:
        raise SystemExit("Pass --url or configure VIBER_WEBHOOK_PUBLIC_URL.")
    result = set_viber_webhook(settings, url)
    print(f"Viber set_webhook status={result.status} message={result.status_message}")
    print(f"Event types: {', '.join(result.event_types) if result.event_types else 'n/a'}")


def viber_remove_webhook(confirm_real_call: bool) -> None:
    if not confirm_real_call:
        raise SystemExit("Refusing real Viber call: pass --confirm-real-call.")
    result = remove_viber_webhook(get_settings())
    print(f"Viber remove webhook status={result.status} message={result.status_message}")


def run_price_monitor_once(limit: int) -> None:
    db = SessionLocal()
    try:
        summary = run_due_price_monitor_checks(
            db,
            adapter=build_price_monitor_adapter(get_settings()),
            limit=limit,
        )
    finally:
        db.close()
    print(
        "Price monitor run: "
        f"checked={summary.checked} snapshots={summary.snapshots} "
        f"changes={summary.changes} errors={summary.errors}"
    )


def run_market_digest_once(limit: int) -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        summary = run_market_digest_batch(
            db,
            adapter=build_notification_adapter(settings),
            console_url=settings.operator_console_url,
            limit=limit,
        )
    finally:
        db.close()
    print(
        "Market digest run: "
        f"batch_id={summary.batch_id or 'n/a'} events={summary.events} "
        f"deliveries={summary.deliveries} status={summary.status}"
    )


def run_scheduler_once(limit: int) -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        summary = run_due_scheduled_jobs(db, settings, limit=limit)
    finally:
        db.close()
    print(
        "Scheduler run: "
        f"checked={summary.checked} started={summary.started} "
        f"succeeded={summary.succeeded} failed={summary.failed} skipped={summary.skipped}"
    )
    for run in summary.runs:
        print(f"- {run.job_key}: {run.status}")


def run_scheduler_loop(limit: int, sleep_seconds: int, iterations: int | None) -> None:
    count = 0
    while iterations is None or count < iterations:
        run_scheduler_once(limit)
        count += 1
        if iterations is not None and count >= iterations:
            break
        time.sleep(max(sleep_seconds, 1))


def _gemini_smoke_models(settings) -> list[str]:
    configured = settings.gemini_smoke_models
    models = [model.strip() for model in configured.split(",") if model.strip()]
    if settings.gemini_research_model and settings.gemini_research_model not in models:
        models.insert(0, settings.gemini_research_model)
    return models


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db")
    subparsers.add_parser("seed-prompts")
    subparsers.add_parser("sync-skills")
    subparsers.add_parser("gemini-quota-status")

    smoke_parser = subparsers.add_parser("smoke-gemini-research")
    smoke_parser.add_argument("--query", default="Starlink Mini for travel: buyer research")

    viber_payload_parser = subparsers.add_parser("viber-webhook-payload")
    viber_payload_parser.add_argument("--url")

    viber_set_parser = subparsers.add_parser("viber-set-webhook")
    viber_set_parser.add_argument("--url")
    viber_set_parser.add_argument("--confirm-real-call", action="store_true")

    viber_remove_parser = subparsers.add_parser("viber-remove-webhook")
    viber_remove_parser.add_argument("--confirm-real-call", action="store_true")

    price_monitor_parser = subparsers.add_parser("run-price-monitor-once")
    price_monitor_parser.add_argument("--limit", type=int, default=20)

    market_digest_parser = subparsers.add_parser("run-market-digest-once")
    market_digest_parser.add_argument("--limit", type=int, default=20)

    scheduler_once_parser = subparsers.add_parser("run-scheduler-once")
    scheduler_once_parser.add_argument("--limit", type=int, default=20)

    scheduler_loop_parser = subparsers.add_parser("run-scheduler-loop")
    scheduler_loop_parser.add_argument("--limit", type=int, default=20)
    scheduler_loop_parser.add_argument("--sleep-seconds", type=int, default=60)
    scheduler_loop_parser.add_argument("--iterations", type=int)

    args = parser.parse_args()

    if args.command == "init-db":
        init_db()
    elif args.command == "seed-prompts":
        seed_prompts()
    elif args.command == "sync-skills":
        sync_skills()
    elif args.command == "smoke-gemini-research":
        smoke_gemini_research(args.query)
    elif args.command == "gemini-quota-status":
        gemini_quota_status()
    elif args.command == "viber-webhook-payload":
        viber_webhook_payload(args.url)
    elif args.command == "viber-set-webhook":
        viber_set_webhook(args.url, args.confirm_real_call)
    elif args.command == "viber-remove-webhook":
        viber_remove_webhook(args.confirm_real_call)
    elif args.command == "run-price-monitor-once":
        run_price_monitor_once(args.limit)
    elif args.command == "run-market-digest-once":
        run_market_digest_once(args.limit)
    elif args.command == "run-scheduler-once":
        run_scheduler_once(args.limit)
    elif args.command == "run-scheduler-loop":
        run_scheduler_loop(args.limit, args.sleep_seconds, args.iterations)


if __name__ == "__main__":
    main()
