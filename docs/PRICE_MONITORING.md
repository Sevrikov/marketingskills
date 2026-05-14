# Price Monitoring

Last updated: 2026-05-07

## Goal

Regularly check already-known competitor or supplier URLs without paying for SERP
search every time.

```text
MonitoredSource
-> PriceMonitorAdapter
-> browser or mock page capture
-> JS extractor script
-> PriceSnapshot
-> PriceGroup aggregation
-> PriceMarketIndex
-> PriceTrendEvent
-> notification policy later
```

## Current Implementation

| Component | Status |
|---|---|
| `monitored_sources` model | Implemented |
| `price_snapshots` model | Implemented |
| Generic JS extractor script | Implemented |
| Mock price monitor adapter | Implemented |
| Playwright adapter boundary | Implemented, off by default |
| API create/list/update/capture/snapshots | Implemented |
| Due-source run-once scheduler entrypoint | Implemented |
| Price/availability change events | Implemented |
| Price groups | Implemented |
| Market index aggregation | Implemented |
| Mass trend events | Implemented |
| Notification policies | Implemented |
| Real recurring scheduler | Planned |
| Viber/mock digest delivery | Implemented |
| Viber/mock immediate alerts | Implemented |
| Digest batches | Implemented |
| LLM-generated custom extractors | Planned |

## API

```text
POST /api/price-monitor/sources
GET  /api/price-monitor/sources
GET  /api/price-monitor/sources/{source_id}
PATCH /api/price-monitor/sources/{source_id}
POST /api/price-monitor/sources/{source_id}/capture
GET  /api/price-monitor/sources/{source_id}/snapshots
POST /api/price-monitor/run-once
GET  /api/price-monitor/changes
POST /api/price-monitor/groups
GET  /api/price-monitor/groups
POST /api/price-monitor/groups/{group_id}/market-indexes
GET  /api/price-monitor/groups/{group_id}/market-indexes
GET  /api/price-monitor/trend-events
POST /api/price-monitor/notification-policies
GET  /api/price-monitor/notification-policies
POST /api/price-monitor/notification-policies/evaluate
POST /api/price-monitor/trend-digests/send
POST /api/price-monitor/trend-alerts/send
POST /api/price-monitor/trend-digests/run-batch
GET  /api/price-monitor/trend-digests/batches
```

## Settings

Default local mode is deterministic and does not open a browser:

```text
PRICE_MONITOR_PROVIDER=mock
```

Future real browser mode:

```text
PRICE_MONITOR_PROVIDER=playwright
PRICE_MONITOR_TIMEOUT_SECONDS=20
PRICE_MONITOR_USER_AGENT=AIContentFactoryPriceMonitor/0.1
```

The Playwright adapter evaluates the stored `extractor_script` inside the page and
expects JSON with fields such as:

```json
{
  "title": "Product title",
  "price": "12999.00",
  "currency": "UAH",
  "availability": "in_stock",
  "sku": "ABC-123",
  "confidence": 0.8
}
```

## Operating Rule

Use SERP providers only for discovering new URLs. Use price monitoring for checking
known URLs repeatedly. This keeps costs low and avoids turning Google search pages into
the main monitoring mechanism.

## Manual Scheduled Run

Run all due active sources once:

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.cli run-price-monitor-once --limit 20
```

The service:

1. selects active sources where `next_check_at` is empty or in the past;
2. captures a snapshot;
3. compares price, currency and availability with the previous known values;
4. records `price_changed` and `availability_changed` events;
5. moves `next_check_at` forward by `check_interval_minutes`.

The next production step is to run this command from cron, Windows Task Scheduler, or
an app automation.

## Market Indexes

Price groups turn many URL-level snapshots into a market-level view:

```text
PriceGroup
-> active monitored sources
-> latest source prices
-> min/max/avg/median
-> top position average
-> availability rate
-> trend event when avg price moves significantly
```

Current trend events:

- `mass_price_drop`
- `mass_price_increase`

The first index establishes a baseline. Later indexes compare average price with the
previous index. A change of 5% or more creates a trend event; 10% or more is `high`
severity. Viber should later subscribe only to high-severity trend events or digests,
not every individual price snapshot.

## Notification Policies

Notification policies decide what happens to pending `PriceTrendEvent` records:

```text
PriceTrendEvent pending
-> NotificationPolicy evaluation
-> ready_immediate | queued_digest | stored_only | suppressed
```

Policy thresholds:

- `min_severity`
- `min_affected_sources`
- `min_percent_change`
- `delivery_mode`: `immediate`, `digest`, or `stored_only`

The digest delivery endpoint sends `queued_digest` trend events through the configured
notification adapter. Local development uses `mock-notifications`; real Viber delivery
requires `NOTIFICATION_PROVIDER=viber` and Viber reviewer configuration.

The immediate alert endpoint sends `ready_immediate` trend events one by one and moves
them to `sent_immediate`. Use this only for high-severity policies; normal market
movement should stay in digest mode.

The batch endpoint creates a `market_digest_batches` record, sends one digest message
for the selected `queued_digest` events, stores delivery metadata and links each trend
event back to the batch through `digest_batch_id`.

CLI:

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.cli run-market-digest-once --limit 20
```
