from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MonitoredSourceCreate(BaseModel):
    product_id: str | None = None
    price_group_id: str | None = None
    url: str = Field(min_length=1)
    label: str | None = None
    competitor_name: str | None = None
    market_position: int | None = Field(default=None, ge=1)
    source_priority: int = Field(default=100, ge=1)
    source_type: str = "competitor_product"
    is_active: bool = True
    check_interval_minutes: int = Field(default=1440, ge=5)
    next_check_at: datetime | None = None
    extractor_type: str = "generic_js"
    extractor_script: str | None = None
    expected_currency: str | None = Field(default=None, max_length=8)
    metadata_json: dict[str, Any] | None = None


class MonitoredSourceUpdate(BaseModel):
    product_id: str | None = None
    price_group_id: str | None = None
    url: str | None = Field(default=None, min_length=1)
    label: str | None = None
    competitor_name: str | None = None
    market_position: int | None = Field(default=None, ge=1)
    source_priority: int | None = Field(default=None, ge=1)
    source_type: str | None = None
    is_active: bool | None = None
    check_interval_minutes: int | None = Field(default=None, ge=5)
    next_check_at: datetime | None = None
    extractor_type: str | None = None
    extractor_script: str | None = None
    expected_currency: str | None = Field(default=None, max_length=8)
    metadata_json: dict[str, Any] | None = None


class MonitoredSourceRead(BaseModel):
    id: str
    product_id: str | None
    price_group_id: str | None
    url: str
    label: str | None
    competitor_name: str | None
    market_position: int | None
    source_priority: int
    source_type: str
    is_active: bool
    check_interval_minutes: int
    next_check_at: datetime | None
    last_checked_at: datetime | None
    extractor_type: str
    extractor_script: str
    expected_currency: str | None
    last_price: Decimal | None
    last_currency: str | None
    last_availability: str | None
    last_status: str | None
    last_error: str | None
    metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PriceSnapshotRead(BaseModel):
    id: str
    monitored_source_id: str
    status: str
    price: Decimal | None
    currency: str | None
    availability: str | None
    title: str | None
    sku: str | None
    confidence: Decimal | None
    extractor_type: str
    raw_json: dict[str, Any] | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PriceChangeEventRead(BaseModel):
    id: str
    monitored_source_id: str
    price_snapshot_id: str | None
    event_type: str
    old_price: Decimal | None
    new_price: Decimal | None
    old_currency: str | None
    new_currency: str | None
    old_availability: str | None
    new_availability: str | None
    status: str
    metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PriceMonitorRunResult(BaseModel):
    checked: int
    snapshots: int
    changes: int
    errors: int


class PriceGroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: str | None = None
    brand: str | None = None
    keywords: str | None = None
    top_position_limit: int = Field(default=10, ge=1)
    min_sources_for_signal: int = Field(default=3, ge=1)
    metadata_json: dict[str, Any] | None = None


class PriceGroupRead(PriceGroupCreate):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PriceMarketIndexRead(BaseModel):
    id: str
    price_group_id: str
    window: str
    source_count: int
    in_stock_count: int
    min_price: Decimal | None
    max_price: Decimal | None
    avg_price: Decimal | None
    median_price: Decimal | None
    top_sources_avg_price: Decimal | None
    availability_rate: Decimal | None
    metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PriceTrendEventRead(BaseModel):
    id: str
    price_group_id: str
    market_index_id: str | None
    event_type: str
    severity: str
    affected_sources_count: int
    percent_change: Decimal | None
    summary: str
    notify_status: str
    metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationPolicyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    event_scope: str = "price_trend"
    channel: str = "viber"
    delivery_mode: str = Field(default="digest", pattern="^(immediate|digest|stored_only)$")
    min_severity: str = Field(default="high", pattern="^(low|medium|high|critical)$")
    min_affected_sources: int = Field(default=3, ge=1)
    min_percent_change: Decimal = Field(default=Decimal("10.0"), ge=0)
    quiet_hours_start: str | None = Field(default=None, max_length=5)
    quiet_hours_end: str | None = Field(default=None, max_length=5)
    status: str = Field(default="active", pattern="^(active|paused)$")
    metadata_json: dict[str, Any] | None = None


class NotificationPolicyRead(NotificationPolicyCreate):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationPolicyEvaluationResult(BaseModel):
    evaluated: int
    ready_immediate: int
    queued_digest: int
    suppressed: int


class MarketTrendDigestSendResult(BaseModel):
    events: int
    deliveries: int


class MarketTrendImmediateSendResult(BaseModel):
    events: int
    deliveries: int


class MarketDigestBatchRead(BaseModel):
    id: str
    status: str
    event_ids: list[str]
    event_count: int
    title: str
    summary: str
    delivery_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MarketDigestBatchRunResult(BaseModel):
    batch_id: str | None
    events: int
    deliveries: int
    status: str
