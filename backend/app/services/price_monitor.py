from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.adapters.price_monitor import (
    GENERIC_PRICE_EXTRACTOR_JS,
    PriceMonitorAdapter,
    PriceMonitorRequest,
)
from app.adapters.notifications import MarketTrendDigestNotificationRequest, NotificationAdapter
from app.models.monitored_source import MonitoredSource
from app.models.market_digest_batch import MarketDigestBatch
from app.models.notification_policy import NotificationPolicy
from app.models.price_change_event import PriceChangeEvent
from app.models.price_group import PriceGroup
from app.models.price_market_index import PriceMarketIndex
from app.models.price_snapshot import PriceSnapshot
from app.models.price_trend_event import PriceTrendEvent
from app.schemas.price_monitor import (
    MonitoredSourceCreate,
    MonitoredSourceUpdate,
    NotificationPolicyCreate,
    PriceGroupCreate,
)

SIGNIFICANT_PERCENT_CHANGE = Decimal("5.0")
SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def create_monitored_source(db: Session, data: MonitoredSourceCreate) -> MonitoredSource:
    payload = data.model_dump()
    if not payload.get("extractor_script"):
        payload["extractor_script"] = GENERIC_PRICE_EXTRACTOR_JS
    if payload.get("next_check_at") is None:
        payload["next_check_at"] = _utc_now()
    source = MonitoredSource(**payload)
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def list_monitored_sources(
    db: Session,
    limit: int = 50,
    offset: int = 0,
    product_id: str | None = None,
) -> list[MonitoredSource]:
    stmt = select(MonitoredSource).order_by(MonitoredSource.created_at.desc())
    if product_id:
        stmt = stmt.where(MonitoredSource.product_id == product_id)
    stmt = stmt.limit(limit).offset(offset)
    return list(db.scalars(stmt))


def get_monitored_source(db: Session, source_id: str) -> MonitoredSource | None:
    return db.get(MonitoredSource, source_id)


def update_monitored_source(
    db: Session,
    source: MonitoredSource,
    data: MonitoredSourceUpdate,
) -> MonitoredSource:
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(source, key, value)
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def create_price_group(db: Session, data: PriceGroupCreate) -> PriceGroup:
    group = PriceGroup(**data.model_dump())
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


def list_price_groups(db: Session, limit: int = 50, offset: int = 0) -> list[PriceGroup]:
    stmt = select(PriceGroup).order_by(PriceGroup.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt))


def get_price_group(db: Session, group_id: str) -> PriceGroup | None:
    return db.get(PriceGroup, group_id)


def create_notification_policy(
    db: Session,
    data: NotificationPolicyCreate,
) -> NotificationPolicy:
    policy = NotificationPolicy(**data.model_dump())
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


def list_notification_policies(
    db: Session,
    limit: int = 50,
    offset: int = 0,
) -> list[NotificationPolicy]:
    stmt = (
        select(NotificationPolicy)
        .order_by(NotificationPolicy.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt))


def capture_price_snapshot(
    db: Session,
    source: MonitoredSource,
    adapter: PriceMonitorAdapter,
) -> PriceSnapshot:
    previous_price = source.last_price
    previous_currency = source.last_currency
    previous_availability = source.last_availability
    result = adapter.capture(
        PriceMonitorRequest(
            url=source.url,
            extractor_script=source.extractor_script,
            extractor_type=source.extractor_type,
            expected_currency=source.expected_currency,
            metadata=source.metadata_json or {},
        )
    )
    snapshot = PriceSnapshot(
        monitored_source_id=source.id,
        status=result.status,
        price=result.price,
        currency=result.currency,
        availability=result.availability,
        title=result.title,
        sku=result.sku,
        confidence=result.confidence,
        extractor_type=source.extractor_type,
        raw_json=result.raw or {},
        error_message=result.error_message,
    )
    source.last_price = result.price
    source.last_currency = result.currency
    source.last_availability = result.availability
    source.last_status = result.status
    source.last_error = result.error_message
    source.last_checked_at = _utc_now()
    source.next_check_at = source.last_checked_at + timedelta(
        minutes=max(source.check_interval_minutes, 5)
    )
    db.add(source)
    db.add(snapshot)
    db.flush()
    for event_type in _detect_change_types(
        previous_price=previous_price,
        new_price=result.price,
        previous_currency=previous_currency,
        new_currency=result.currency,
        previous_availability=previous_availability,
        new_availability=result.availability,
    ):
        db.add(
            PriceChangeEvent(
                monitored_source_id=source.id,
                price_snapshot_id=snapshot.id,
                event_type=event_type,
                old_price=previous_price,
                new_price=result.price,
                old_currency=previous_currency,
                new_currency=result.currency,
                old_availability=previous_availability,
                new_availability=result.availability,
                metadata_json={"url": source.url, "label": source.label},
            )
        )
    db.commit()
    db.refresh(snapshot)
    return snapshot


@dataclass(frozen=True)
class PriceMonitorRunSummary:
    checked: int
    snapshots: int
    changes: int
    errors: int


def run_due_price_monitor_checks(
    db: Session,
    adapter: PriceMonitorAdapter,
    limit: int = 20,
    now: datetime | None = None,
) -> PriceMonitorRunSummary:
    now = now or _utc_now()
    sources = list_due_monitored_sources(db, limit=limit, now=now)
    snapshots = 0
    errors = 0
    change_count_before = _count_change_events(db)
    for source in sources:
        try:
            capture_price_snapshot(db, source, adapter)
            snapshots += 1
        except Exception as exc:
            errors += 1
            source.last_status = "failed"
            source.last_error = str(exc)[:500]
            source.last_checked_at = now
            source.next_check_at = now + timedelta(minutes=max(source.check_interval_minutes, 5))
            db.add(source)
            db.commit()

    return PriceMonitorRunSummary(
        checked=len(sources),
        snapshots=snapshots,
        changes=_count_change_events(db) - change_count_before,
        errors=errors,
    )


def list_due_monitored_sources(
    db: Session,
    limit: int = 20,
    now: datetime | None = None,
) -> list[MonitoredSource]:
    now = now or _utc_now()
    stmt = (
        select(MonitoredSource)
        .where(MonitoredSource.is_active.is_(True))
        .where(or_(MonitoredSource.next_check_at.is_(None), MonitoredSource.next_check_at <= now))
        .order_by(MonitoredSource.next_check_at.asc(), MonitoredSource.created_at.asc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


def list_price_snapshots(
    db: Session,
    source_id: str,
    limit: int = 50,
    offset: int = 0,
) -> list[PriceSnapshot]:
    stmt = (
        select(PriceSnapshot)
        .where(PriceSnapshot.monitored_source_id == source_id)
        .order_by(PriceSnapshot.created_at.desc(), PriceSnapshot.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt))


def list_price_change_events(
    db: Session,
    source_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[PriceChangeEvent]:
    stmt = select(PriceChangeEvent).order_by(
        PriceChangeEvent.created_at.desc(),
        PriceChangeEvent.id.desc(),
    )
    if source_id:
        stmt = stmt.where(PriceChangeEvent.monitored_source_id == source_id)
    stmt = stmt.limit(limit).offset(offset)
    return list(db.scalars(stmt))


def build_market_index_for_group(
    db: Session,
    group: PriceGroup,
    window: str = "latest",
) -> PriceMarketIndex:
    previous_index = get_latest_market_index(db, group.id)
    sources = _group_sources_with_prices(db, group.id)
    prices = [source.last_price for source in sources if source.last_price is not None]
    in_stock_count = sum(1 for source in sources if source.last_availability == "in_stock")
    top_sources = [
        source
        for source in sorted(
            sources,
            key=lambda item: (
                item.market_position or 999999,
                item.source_priority,
                item.created_at,
            ),
        )[: group.top_position_limit]
        if source.last_price is not None
    ]
    index = PriceMarketIndex(
        price_group_id=group.id,
        window=window,
        source_count=len(sources),
        in_stock_count=in_stock_count,
        min_price=min(prices) if prices else None,
        max_price=max(prices) if prices else None,
        avg_price=_avg(prices),
        median_price=_median(prices),
        top_sources_avg_price=_avg([source.last_price for source in top_sources]),
        availability_rate=_rate(in_stock_count, len(sources)),
        metadata_json={
            "group_name": group.name,
            "top_position_limit": group.top_position_limit,
            "min_sources_for_signal": group.min_sources_for_signal,
        },
    )
    db.add(index)
    db.flush()
    event = _build_trend_event(group, index, previous_index)
    if event is not None:
        db.add(event)
    db.commit()
    db.refresh(index)
    return index


def get_latest_market_index(db: Session, group_id: str) -> PriceMarketIndex | None:
    stmt = (
        select(PriceMarketIndex)
        .where(PriceMarketIndex.price_group_id == group_id)
        .order_by(PriceMarketIndex.created_at.desc(), PriceMarketIndex.id.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


def list_market_indexes(
    db: Session,
    group_id: str,
    limit: int = 50,
    offset: int = 0,
) -> list[PriceMarketIndex]:
    stmt = (
        select(PriceMarketIndex)
        .where(PriceMarketIndex.price_group_id == group_id)
        .order_by(PriceMarketIndex.created_at.desc(), PriceMarketIndex.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt))


def list_price_trend_events(
    db: Session,
    group_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[PriceTrendEvent]:
    stmt = select(PriceTrendEvent).order_by(
        PriceTrendEvent.created_at.desc(),
        PriceTrendEvent.id.desc(),
    )
    if group_id:
        stmt = stmt.where(PriceTrendEvent.price_group_id == group_id)
    stmt = stmt.limit(limit).offset(offset)
    return list(db.scalars(stmt))


@dataclass(frozen=True)
class MarketTrendDigestSendSummary:
    events: int
    deliveries: int


@dataclass(frozen=True)
class MarketTrendImmediateSendSummary:
    events: int
    deliveries: int


@dataclass(frozen=True)
class MarketDigestBatchRunSummary:
    batch_id: str | None
    events: int
    deliveries: int
    status: str


def send_queued_market_trend_digest(
    db: Session,
    adapter: NotificationAdapter,
    console_url: str | None = None,
    limit: int = 10,
) -> MarketTrendDigestSendSummary:
    events = _queued_digest_trend_events(db, limit=limit)
    if not events:
        return MarketTrendDigestSendSummary(events=0, deliveries=0)

    request = MarketTrendDigestNotificationRequest(
        title="Market price trend digest",
        summary=_format_market_trend_digest(events),
        event_ids=[event.id for event in events],
        console_url=console_url,
    )
    deliveries = adapter.send_market_trend_digest(request)
    for event in events:
        event.notify_status = "sent_digest"
        metadata = dict(event.metadata_json or {})
        metadata["digest_delivery"] = [
            {
                "provider": delivery.provider,
                "channel": delivery.channel,
                "status": delivery.status,
                "recipient": delivery.recipient,
                "message_id": delivery.message_id,
            }
            for delivery in deliveries
        ]
        event.metadata_json = metadata
        db.add(event)
    db.commit()
    return MarketTrendDigestSendSummary(events=len(events), deliveries=len(deliveries))


def run_market_digest_batch(
    db: Session,
    adapter: NotificationAdapter,
    console_url: str | None = None,
    limit: int = 20,
) -> MarketDigestBatchRunSummary:
    events = _queued_digest_trend_events(db, limit=limit)
    if not events:
        return MarketDigestBatchRunSummary(
            batch_id=None,
            events=0,
            deliveries=0,
            status="empty",
        )

    title = "Market price trend digest"
    summary = _format_market_trend_digest(events)
    batch = MarketDigestBatch(
        status="created",
        event_ids=[event.id for event in events],
        event_count=len(events),
        title=title,
        summary=summary,
        delivery_json=None,
    )
    db.add(batch)
    db.flush()

    request = MarketTrendDigestNotificationRequest(
        title=title,
        summary=summary,
        event_ids=batch.event_ids,
        console_url=console_url,
    )
    deliveries = adapter.send_market_trend_digest(request)
    batch.status = "sent"
    batch.delivery_json = {
        "deliveries": [
            {
                "provider": delivery.provider,
                "channel": delivery.channel,
                "status": delivery.status,
                "recipient": delivery.recipient,
                "message_id": delivery.message_id,
            }
            for delivery in deliveries
        ]
    }
    for event in events:
        event.notify_status = "sent_digest"
        metadata = dict(event.metadata_json or {})
        metadata["digest_batch_id"] = batch.id
        event.metadata_json = metadata
        db.add(event)
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return MarketDigestBatchRunSummary(
        batch_id=batch.id,
        events=len(events),
        deliveries=len(deliveries),
        status=batch.status,
    )


def list_market_digest_batches(
    db: Session,
    limit: int = 50,
    offset: int = 0,
) -> list[MarketDigestBatch]:
    stmt = (
        select(MarketDigestBatch)
        .order_by(MarketDigestBatch.created_at.desc(), MarketDigestBatch.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt))


def send_ready_market_trend_alerts(
    db: Session,
    adapter: NotificationAdapter,
    console_url: str | None = None,
    limit: int = 10,
) -> MarketTrendImmediateSendSummary:
    events = _ready_immediate_trend_events(db, limit=limit)
    delivery_count = 0
    for event in events:
        request = MarketTrendDigestNotificationRequest(
            title="Immediate market price alert",
            summary=_format_market_trend_digest([event]),
            event_ids=[event.id],
            console_url=console_url,
        )
        deliveries = adapter.send_market_trend_digest(request)
        delivery_count += len(deliveries)
        event.notify_status = "sent_immediate"
        metadata = dict(event.metadata_json or {})
        metadata["immediate_delivery"] = [
            {
                "provider": delivery.provider,
                "channel": delivery.channel,
                "status": delivery.status,
                "recipient": delivery.recipient,
                "message_id": delivery.message_id,
            }
            for delivery in deliveries
        ]
        event.metadata_json = metadata
        db.add(event)
    db.commit()
    return MarketTrendImmediateSendSummary(events=len(events), deliveries=delivery_count)


@dataclass(frozen=True)
class NotificationPolicyEvaluationSummary:
    evaluated: int
    ready_immediate: int
    queued_digest: int
    suppressed: int


def evaluate_price_trend_notification_policies(
    db: Session,
    limit: int = 100,
) -> NotificationPolicyEvaluationSummary:
    events = _pending_trend_events(db, limit=limit)
    policies = _active_price_trend_policies(db)
    ready_immediate = 0
    queued_digest = 0
    suppressed = 0

    for event in events:
        decision = _notification_decision(event, policies)
        event.notify_status = decision
        db.add(event)
        if decision == "ready_immediate":
            ready_immediate += 1
        elif decision == "queued_digest":
            queued_digest += 1
        else:
            suppressed += 1

    db.commit()
    return NotificationPolicyEvaluationSummary(
        evaluated=len(events),
        ready_immediate=ready_immediate,
        queued_digest=queued_digest,
        suppressed=suppressed,
    )


def _detect_change_types(
    previous_price,
    new_price,
    previous_currency,
    new_currency,
    previous_availability,
    new_availability,
) -> list[str]:
    if previous_price is None and previous_availability is None:
        return []
    events: list[str] = []
    if previous_price != new_price or previous_currency != new_currency:
        events.append("price_changed")
    if previous_availability != new_availability:
        events.append("availability_changed")
    return events


def _count_change_events(db: Session) -> int:
    return len(list(db.scalars(select(PriceChangeEvent.id))))


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _group_sources_with_prices(db: Session, group_id: str) -> list[MonitoredSource]:
    stmt = (
        select(MonitoredSource)
        .where(MonitoredSource.price_group_id == group_id)
        .where(MonitoredSource.is_active.is_(True))
    )
    return list(db.scalars(stmt))


def _avg(values) -> Decimal | None:
    clean = [Decimal(value) for value in values if value is not None]
    if not clean:
        return None
    return (sum(clean) / Decimal(len(clean))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _median(values) -> Decimal | None:
    clean = sorted(Decimal(value) for value in values if value is not None)
    if not clean:
        return None
    middle = len(clean) // 2
    if len(clean) % 2:
        return clean[middle].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return ((clean[middle - 1] + clean[middle]) / Decimal("2")).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def _rate(numerator: int, denominator: int) -> Decimal | None:
    if denominator <= 0:
        return None
    return (Decimal(numerator) / Decimal(denominator)).quantize(
        Decimal("0.0001"),
        rounding=ROUND_HALF_UP,
    )


def _build_trend_event(
    group: PriceGroup,
    index: PriceMarketIndex,
    previous_index: PriceMarketIndex | None,
) -> PriceTrendEvent | None:
    if (
        previous_index is None
        or previous_index.avg_price is None
        or index.avg_price is None
        or index.source_count < group.min_sources_for_signal
    ):
        return None

    percent_change = ((index.avg_price - previous_index.avg_price) / previous_index.avg_price) * 100
    if abs(percent_change) < SIGNIFICANT_PERCENT_CHANGE:
        return None

    event_type = "mass_price_increase" if percent_change > 0 else "mass_price_drop"
    severity = "high" if abs(percent_change) >= Decimal("10.0") else "medium"
    direction = "increased" if percent_change > 0 else "decreased"
    summary = (
        f"Average market price for {group.name} {direction} by "
        f"{percent_change.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}%."
    )
    return PriceTrendEvent(
        price_group_id=group.id,
        market_index_id=index.id,
        event_type=event_type,
        severity=severity,
        affected_sources_count=index.source_count,
        percent_change=percent_change.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
        summary=summary,
        metadata_json={
            "previous_avg_price": str(previous_index.avg_price),
            "new_avg_price": str(index.avg_price),
            "source_count": index.source_count,
        },
    )


def _pending_trend_events(db: Session, limit: int) -> list[PriceTrendEvent]:
    stmt = (
        select(PriceTrendEvent)
        .where(PriceTrendEvent.notify_status == "pending")
        .order_by(PriceTrendEvent.created_at.asc(), PriceTrendEvent.id.asc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


def _queued_digest_trend_events(db: Session, limit: int) -> list[PriceTrendEvent]:
    stmt = (
        select(PriceTrendEvent)
        .where(PriceTrendEvent.notify_status == "queued_digest")
        .order_by(PriceTrendEvent.created_at.asc(), PriceTrendEvent.id.asc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


def _ready_immediate_trend_events(db: Session, limit: int) -> list[PriceTrendEvent]:
    stmt = (
        select(PriceTrendEvent)
        .where(PriceTrendEvent.notify_status == "ready_immediate")
        .order_by(PriceTrendEvent.created_at.asc(), PriceTrendEvent.id.asc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


def _format_market_trend_digest(events: list[PriceTrendEvent]) -> str:
    lines: list[str] = []
    for event in events:
        percent = f"{event.percent_change}%" if event.percent_change is not None else "n/a"
        lines.append(
            "\n".join(
                [
                    f"- {event.severity.upper()}: {event.event_type}",
                    f"  {event.summary}",
                    f"  Change: {percent}; sources: {event.affected_sources_count}",
                ]
            )
        )
    return "\n\n".join(lines)


def _active_price_trend_policies(db: Session) -> list[NotificationPolicy]:
    stmt = (
        select(NotificationPolicy)
        .where(NotificationPolicy.status == "active")
        .where(NotificationPolicy.event_scope == "price_trend")
        .order_by(NotificationPolicy.created_at.desc())
    )
    return list(db.scalars(stmt))


def _notification_decision(
    event: PriceTrendEvent,
    policies: list[NotificationPolicy],
) -> str:
    for policy in policies:
        if not _event_matches_policy(event, policy):
            continue
        if policy.delivery_mode == "immediate":
            return "ready_immediate"
        if policy.delivery_mode == "digest":
            return "queued_digest"
        return "stored_only"
    return "suppressed"


def _event_matches_policy(event: PriceTrendEvent, policy: NotificationPolicy) -> bool:
    if SEVERITY_RANK.get(event.severity, 0) < SEVERITY_RANK.get(policy.min_severity, 0):
        return False
    if event.affected_sources_count < policy.min_affected_sources:
        return False
    if event.percent_change is None:
        return False
    return abs(event.percent_change) >= policy.min_percent_change
