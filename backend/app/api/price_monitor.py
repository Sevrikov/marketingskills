from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.adapters.factory import build_notification_adapter, build_price_monitor_adapter
from app.db.session import get_db
from app.schemas.price_monitor import (
    MonitoredSourceCreate,
    MonitoredSourceRead,
    MonitoredSourceUpdate,
    MarketDigestBatchRead,
    MarketDigestBatchRunResult,
    MarketTrendDigestSendResult,
    MarketTrendImmediateSendResult,
    NotificationPolicyCreate,
    NotificationPolicyEvaluationResult,
    NotificationPolicyRead,
    PriceChangeEventRead,
    PriceGroupCreate,
    PriceGroupRead,
    PriceMarketIndexRead,
    PriceMonitorRunResult,
    PriceSnapshotRead,
    PriceTrendEventRead,
)
from app.services.price_monitor import (
    build_market_index_for_group,
    capture_price_snapshot,
    create_notification_policy,
    create_price_group,
    create_monitored_source,
    evaluate_price_trend_notification_policies,
    get_price_group,
    get_monitored_source,
    list_market_digest_batches,
    list_market_indexes,
    list_monitored_sources,
    list_notification_policies,
    list_price_change_events,
    list_price_groups,
    list_price_snapshots,
    list_price_trend_events,
    run_due_price_monitor_checks,
    run_market_digest_batch,
    send_queued_market_trend_digest,
    send_ready_market_trend_alerts,
    update_monitored_source,
)
from app.services.runtime_settings import effective_settings

router = APIRouter(prefix="/api/price-monitor", tags=["price-monitor"])


@router.post("/groups", response_model=PriceGroupRead, status_code=status.HTTP_201_CREATED)
def create_price_group_endpoint(payload: PriceGroupCreate, db: Session = Depends(get_db)):
    return create_price_group(db, payload)


@router.get("/groups", response_model=list[PriceGroupRead])
def list_price_groups_endpoint(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return list_price_groups(db, limit=limit, offset=offset)


@router.post("/groups/{group_id}/market-indexes", response_model=PriceMarketIndexRead)
def build_market_index_endpoint(group_id: str, db: Session = Depends(get_db)):
    group = get_price_group(db, group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return build_market_index_for_group(db, group)


@router.get("/groups/{group_id}/market-indexes", response_model=list[PriceMarketIndexRead])
def list_market_indexes_endpoint(
    group_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    if get_price_group(db, group_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return list_market_indexes(db, group_id=group_id, limit=limit, offset=offset)


@router.post("/sources", response_model=MonitoredSourceRead, status_code=status.HTTP_201_CREATED)
def create_monitored_source_endpoint(
    payload: MonitoredSourceCreate,
    db: Session = Depends(get_db),
):
    return create_monitored_source(db, payload)


@router.get("/sources", response_model=list[MonitoredSourceRead])
def list_monitored_sources_endpoint(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    product_id: str | None = None,
    db: Session = Depends(get_db),
):
    return list_monitored_sources(db, limit=limit, offset=offset, product_id=product_id)


@router.get("/sources/{source_id}", response_model=MonitoredSourceRead)
def get_monitored_source_endpoint(source_id: str, db: Session = Depends(get_db)):
    source = get_monitored_source(db, source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return source


@router.patch("/sources/{source_id}", response_model=MonitoredSourceRead)
def update_monitored_source_endpoint(
    source_id: str,
    payload: MonitoredSourceUpdate,
    db: Session = Depends(get_db),
):
    source = get_monitored_source(db, source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return update_monitored_source(db, source, payload)


@router.post("/sources/{source_id}/capture", response_model=PriceSnapshotRead)
def capture_price_snapshot_endpoint(source_id: str, db: Session = Depends(get_db)):
    source = get_monitored_source(db, source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    adapter = build_price_monitor_adapter(effective_settings(db))
    return capture_price_snapshot(db, source, adapter)


@router.get("/sources/{source_id}/snapshots", response_model=list[PriceSnapshotRead])
def list_price_snapshots_endpoint(
    source_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    if get_monitored_source(db, source_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    return list_price_snapshots(db, source_id=source_id, limit=limit, offset=offset)


@router.post("/run-once", response_model=PriceMonitorRunResult)
def run_price_monitor_once_endpoint(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    adapter = build_price_monitor_adapter(effective_settings(db))
    summary = run_due_price_monitor_checks(db, adapter=adapter, limit=limit)
    return PriceMonitorRunResult(
        checked=summary.checked,
        snapshots=summary.snapshots,
        changes=summary.changes,
        errors=summary.errors,
    )


@router.get("/changes", response_model=list[PriceChangeEventRead])
def list_price_changes_endpoint(
    source_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return list_price_change_events(db, source_id=source_id, limit=limit, offset=offset)


@router.get("/trend-events", response_model=list[PriceTrendEventRead])
def list_price_trend_events_endpoint(
    group_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return list_price_trend_events(db, group_id=group_id, limit=limit, offset=offset)


@router.post(
    "/notification-policies",
    response_model=NotificationPolicyRead,
    status_code=status.HTTP_201_CREATED,
)
def create_notification_policy_endpoint(
    payload: NotificationPolicyCreate,
    db: Session = Depends(get_db),
):
    return create_notification_policy(db, payload)


@router.get("/notification-policies", response_model=list[NotificationPolicyRead])
def list_notification_policies_endpoint(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return list_notification_policies(db, limit=limit, offset=offset)


@router.post(
    "/notification-policies/evaluate",
    response_model=NotificationPolicyEvaluationResult,
)
def evaluate_notification_policies_endpoint(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    summary = evaluate_price_trend_notification_policies(db, limit=limit)
    return NotificationPolicyEvaluationResult(
        evaluated=summary.evaluated,
        ready_immediate=summary.ready_immediate,
        queued_digest=summary.queued_digest,
        suppressed=summary.suppressed,
    )


@router.post("/trend-digests/send", response_model=MarketTrendDigestSendResult)
def send_market_trend_digest_endpoint(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    settings = effective_settings(db)
    summary = send_queued_market_trend_digest(
        db,
        adapter=build_notification_adapter(settings),
        console_url=settings.operator_console_url,
        limit=limit,
    )
    return MarketTrendDigestSendResult(events=summary.events, deliveries=summary.deliveries)


@router.post("/trend-digests/run-batch", response_model=MarketDigestBatchRunResult)
def run_market_trend_digest_batch_endpoint(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    settings = effective_settings(db)
    summary = run_market_digest_batch(
        db,
        adapter=build_notification_adapter(settings),
        console_url=settings.operator_console_url,
        limit=limit,
    )
    return MarketDigestBatchRunResult(
        batch_id=summary.batch_id,
        events=summary.events,
        deliveries=summary.deliveries,
        status=summary.status,
    )


@router.get("/trend-digests/batches", response_model=list[MarketDigestBatchRead])
def list_market_trend_digest_batches_endpoint(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return list_market_digest_batches(db, limit=limit, offset=offset)


@router.post("/trend-alerts/send", response_model=MarketTrendImmediateSendResult)
def send_market_trend_immediate_alerts_endpoint(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    settings = effective_settings(db)
    summary = send_ready_market_trend_alerts(
        db,
        adapter=build_notification_adapter(settings),
        console_url=settings.operator_console_url,
        limit=limit,
    )
    return MarketTrendImmediateSendResult(events=summary.events, deliveries=summary.deliveries)
