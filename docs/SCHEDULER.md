# Scheduler

The scheduler is the shared engine for recurring operational work. It is not limited to price monitoring; future stock sync, supplier price sync, product-card refreshes and catalog cleanup jobs should use the same registry and run history.

## Concepts

`scheduled_jobs` stores the configured jobs:

- `job_key`: stable human-readable key;
- `job_type`: executor type;
- `interval_minutes`: recurrence interval;
- `next_run_at`: due time;
- `last_run_at`, `last_status`, `last_error`;
- `params_json`: executor parameters, such as `limit`;
- `metadata_json`: optional ownership/context.

`scheduled_job_runs` stores every run:

- job key/type;
- trigger: `schedule` or `manual`;
- status: `running`, `succeeded`, `failed`, `skipped`;
- started/finished timestamps;
- summary JSON or error.

## Default Jobs

The API seeds default jobs when scheduler jobs are listed or due jobs are executed:

| Job key | Job type | Interval |
|---|---:|---:|
| `price-monitor-due-checks` | `price_monitor_due_checks` | 15 min |
| `price-trend-policy-evaluation` | `price_trend_policy_evaluation` | 15 min |
| `market-trend-immediate-alerts` | `market_trend_immediate_alerts` | 10 min |
| `market-digest-batch` | `market_digest_batch` | 720 min |

## API

```text
POST /api/scheduler/jobs
GET  /api/scheduler/jobs
PATCH /api/scheduler/jobs/{job_key}
POST /api/scheduler/jobs/{job_key}/run-now
POST /api/scheduler/run-due
GET  /api/scheduler/runs
```

`run-now` is useful for operator checks. `run-due` executes only active jobs whose `next_run_at` is due.

## CLI

Run once:

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.cli run-scheduler-once --limit 20
```

Run a local loop:

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.cli run-scheduler-loop --sleep-seconds 60
```

For a bounded smoke loop:

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.cli run-scheduler-loop --sleep-seconds 5 --iterations 3
```

## Future Job Types

Recommended next executors:

- `stock_sync`: refresh stock and availability from suppliers or CMS;
- `supplier_price_sync`: update own product prices from supplier feeds;
- `product_card_refresh_recommendations`: create review tasks when market/stock changes justify content updates;
- `cms_product_push`: push approved product content profiles to the selected CMS.

Unknown job types are rejected until an executor is implemented.
