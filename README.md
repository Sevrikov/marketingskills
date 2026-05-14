# AI Marketing Content Factory

Google-first AI content and research factory for an electronics e-commerce store.

The product goal is to turn a product or topic into a controlled pipeline:

```text
Product / Topic -> Task -> Deep Research -> Gemini Content -> Critic/Rewriter
-> Schema -> Approval -> Publish Package -> GSC/Sitemap task
```

## Current Phase

Sprint 0 / P0 foundation.

Implemented in this scaffold:

- monorepo structure;
- FastAPI backend placeholder;
- worker placeholder;
- Docker Compose for backend, worker, PostgreSQL, Redis, MinIO;
- `.agents` structure for product context and local skills;
- project documentation from planning phase.

## Repository Layout

```text
backend/       FastAPI API, domain services, adapters, workers
frontend/      Future React UI
workers/       Future standalone worker helpers
.agents/       Product marketing context and agent skills
docs/          Product, architecture and planning documents
```

The planning documents currently live in the repository root and can later be moved into `docs/` when the codebase stabilizes.

## Local Start

Create local env:

```powershell
Copy-Item .env.example .env
```

Run services:

```powershell
docker compose up --build
```

Healthcheck:

```text
GET http://localhost:8000/health
```

## Local Start Without Docker

For the current Windows workspace, a local Python runtime can live in `.tools/`
and the virtual environment in `.venv/`.

Run backend tests:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test-backend.ps1
```

Run the full local mock stability suite:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test-local-mock-suite.ps1
```

Run the realistic product-card smoke for a captured Elektronom/ALTEK product fixture:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test-realistic-product-card.ps1
```

Run the realistic solar-category smoke for captured Elektronom category fixtures:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test-realistic-solar-category.ps1
```

Run the realistic solar-category article smoke:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test-realistic-solar-article.ps1
```

Run the local backend on SQLite with synchronous worker execution:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-backend-local.ps1
```

Then open:

```text
frontend/index.html
```

## Safety Defaults

Real publishing, video generation and image generation are disabled by default:

```text
ENABLE_REAL_PUBLISHING=false
ENABLE_REAL_VIDEO_GENERATION=false
ENABLE_REAL_IMAGE_GENERATION=false
```

This keeps early development in mock/publish-package mode until approval, storage and quality gates are ready.

## Secrets

Never commit API keys.

For local Gemini tests, put a key only in `.env`:

```text
GOOGLE_API_KEY=your_rotated_test_key_here
```

If a key was pasted into chat, logs, GitHub, or any shared document, rotate it in Google AI Studio / Google Cloud before continued use.

Recommended restrictions:

- restrict the key to Gemini / Generative Language APIs needed for testing;
- use a separate test project;
- set budget alerts;
- rotate keys after experiments;
- never put keys in `.env.example`, README, commits, screenshots, or prompts.

## Temporary Debug Endpoints

During local MVP development:

```text
GET  /debug/llm-provider
GET  /debug/research-provider
GET  /debug/source-provider
GET  /debug/price-monitor-provider
GET  /debug/cms-provider
GET  /debug/notification-provider
GET  /debug/image-generation-provider
POST /debug/llm-echo?prompt=hello
```

These endpoints are for local testing only and must be removed or protected before deployment.

## API Settings Manager

The operator console includes an `API settings` tab backed by:

```text
GET /api/runtime-settings
PUT /api/runtime-settings
```

It manages local runtime overrides for:

- Google, Tavily and Viber credentials;
- provider choices for content, research, source collection, notifications and image generation;
- Gemini models for content, critic/rewrite, deep research and image generation;
- Viber reviewer ids, sender name and webhook settings;
- safety flags such as real image generation and Google smoke tests.

Secrets are write-only in the UI. The backend returns only `configured` and a masked value.
Empty secret fields do not clear existing secrets.

## Gemini Grounded Research

The default research provider is mock mode:

```text
LLM_PROVIDER=mock
RESEARCH_PROVIDER=mock
```

To test grounded Gemini research locally, set these only in `.env`:

```text
RESEARCH_PROVIDER=gemini
GOOGLE_API_KEY=your_local_test_key
GEMINI_RESEARCH_MODEL=gemini-2.5-flash-lite
```

Then run the local backend and enqueue a task. Real API usage happens only when
`RESEARCH_PROVIDER=gemini` and a local key is configured.

For content generation, real Gemini is also opt-in:

```text
LLM_PROVIDER=gemini
GEMINI_CONTENT_MODEL=gemini-2.5-flash-lite
GEMINI_CRITIC_MODEL=gemini-2.5-flash-lite
```

Keep `LLM_PROVIDER=mock` for routine local operator testing.

For article image generation, mock mode is the default:

```text
IMAGE_GENERATION_PROVIDER=mock
```

To test Gemini image generation locally, use only `.env` and enable all three fields:

```text
IMAGE_GENERATION_PROVIDER=gemini
ENABLE_REAL_IMAGE_GENERATION=true
GOOGLE_API_KEY=your_local_test_key
GEMINI_IMAGE_MODEL=gemini-3.1-flash-image-preview
```

Real image calls are made only through the Article Studio asset action
`Generate mock image` / `generate-image` endpoint after the backend has been restarted
with those settings.

Current model choices are based on the AI Studio rate-limit snapshot and real low-cost
API probes from 2026-05-07:

- `gemini-2.5-flash-lite`: preferred content/critic/research model; real text and grounded calls succeeded.
- `gemini-3-flash-preview`: available through `models.list`; real text call returned HTTP 200 but empty text in one probe, so keep as fallback only.
- `gemini-3.1-flash-lite-preview`: available through `models.list`, but real call returned temporary `503 UNAVAILABLE`.
- `gemini-2.5-flash`: avoided for now because the snapshot showed 21 / 20 RPD used.
- `gemini-2.5-pro`, `gemini-3.1-pro`, Veo and image models showed 0 / 0 limits in this project.
- `gemini-embedding-001` and `gemini-embedding-2`: real embedding calls succeeded with 3072 dimensions.

The Gemini Developer API documentation points users to AI Studio for active project
rate limits. For online operation we therefore keep a local limit snapshot, enforce
conservative model selection, and treat 429/503 responses as signals to fallback or
pause work.

The local Gemini quota governor is enabled by default for real Gemini calls:

```text
ENABLE_GEMINI_QUOTA_GOVERNOR=true
GEMINI_QUOTA_LEDGER_PATH=.tmp/gemini_quota_ledger.json
GEMINI_DAILY_MODEL_LIMITS=gemini-2.5-flash-lite=20,gemini-3-flash-preview=20,gemini-3.1-flash-lite-preview=500,gemini-embedding-001=1000,gemini-embedding-2=1000
GEMINI_UNAVAILABLE_COOLDOWN_SECONDS=600
```

It records local daily successes and failures, blocks a model for the current day
after `429 RESOURCE_EXHAUSTED`, and cools it down after `503 UNAVAILABLE`. To inspect
today's local ledger:

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.cli gemini-quota-status
```

## Source Collection

The research pipeline has a separate source collection layer before final synthesis.
Local development uses deterministic mock documents:

```text
SOURCE_PROVIDER=mock
SOURCE_COLLECTION_ENABLED=true
```

For Tavily MVP tests, configure only local `.env` values:

```text
SOURCE_PROVIDER=tavily
TAVILY_API_KEY=
SOURCE_COLLECTION_MAX_RESULTS=5
TAVILY_SEARCH_DEPTH=basic
TAVILY_INCLUDE_RAW_CONTENT=markdown
```

Collected source documents are formatted into a source corpus and passed into the
research adapter. If `SOURCE_COLLECTION_REQUIRED=false`, provider failures are recorded
without breaking the whole draft pipeline.

See `docs/SOURCE_PROVIDER_STRATEGY.md`.

## Price Monitoring

Known competitor or supplier URLs can be checked through the price monitor API:

```text
POST /api/price-monitor/sources
POST /api/price-monitor/sources/{source_id}/capture
GET  /api/price-monitor/sources/{source_id}/snapshots
POST /api/price-monitor/run-once
GET  /api/price-monitor/changes
POST /api/price-monitor/groups
POST /api/price-monitor/groups/{group_id}/market-indexes
GET  /api/price-monitor/trend-events
POST /api/price-monitor/notification-policies
POST /api/price-monitor/notification-policies/evaluate
POST /api/price-monitor/trend-digests/send
POST /api/price-monitor/trend-alerts/send
POST /api/price-monitor/trend-digests/run-batch
GET  /api/price-monitor/trend-digests/batches
```

The default provider is deterministic and does not open a browser:

```text
PRICE_MONITOR_PROVIDER=mock
```

The future browser mode is isolated behind:

```text
PRICE_MONITOR_PROVIDER=playwright
```

See `docs/PRICE_MONITORING.md`.

## Scheduler

Recurring operations use a shared scheduler registry:

```text
POST /api/scheduler/jobs
GET  /api/scheduler/jobs
PATCH /api/scheduler/jobs/{job_key}
POST /api/scheduler/jobs/{job_key}/run-now
POST /api/scheduler/run-due
GET  /api/scheduler/runs
```

Default jobs cover due price checks, trend policy evaluation, immediate trend alerts
and market digest batches. The same engine is intended for future stock sync, supplier
price sync and product-card refresh recommendations.

CLI:

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.cli run-scheduler-once --limit 20
```

See `docs/SCHEDULER.md`.

The static operator console now includes `Market` and `Scheduler` tabs for these APIs:

- market groups, monitored sources, trend events, policies and digest batches;
- scheduler jobs, run-now actions, run-due action and run history.

## Content Opportunities

Article topic discovery can turn a product, price group, brand, category or custom query
into prioritized SEO/AEO article ideas:

```text
POST /api/content-opportunities/discover
GET  /api/content-opportunities
POST /api/content-opportunities/{opportunity_id}/create-task
```

The operator console includes an `Opportunities` tab for discovery and one-click
creation of `seo_article` tasks.

See `docs/CONTENT_OPPORTUNITIES.md`.

## Infographic Intelligence

Analytical infographics are planned as a separate data-to-design pipeline for products,
product groups, brands, market trends and article assets. The architecture separates:

- Gemini/Tavily/browser source collection;
- strict cited `infographic_data_pack` generation;
- market analysis and buyer-fit scoring;
- design brief and browser design-agent prompts;
- QA against sources before CMS, social or Viber export.

The first implementation target is backend support for infographic projects and data packs.

See `docs/INFOGRAPHIC_INTELLIGENCE_DESIGN_PIPELINE.md`.

## Customer Pain Research

All product-facing materials should start from a researched buyer problem when one can
be verified. The planned `pain_profile` layer identifies:

- the primary pain or buying problem;
- buyer words, use contexts and trigger events;
- alternatives and objections;
- a proof map from pain to product feature, source or calculation;
- channel-specific guidance for descriptions, articles, infographics, video, Shorts and Viber.

If the pain is not confirmed, the system must mark it as a hypothesis instead of turning
it into a headline claim.

See `docs/CUSTOMER_PAIN_RESEARCH_LAYER.md`.

## Article Production

SEO/AEO articles are planned as a full production pipeline, not only text generation:

- article data pack;
- article brief / ТЗ;
- draft generation;
- image brief / ТЗ на картинки;
- infographic slots;
- asset QA;
- article assembly with approved images;
- CMS-ready package.

See `docs/ARTICLE_PRODUCTION_PIPELINE.md`.

## Video Infographics

Video infographics extend the same cited data-pack approach into Shorts, explainers,
market-pulse videos and competitor-comparison videos. The planned pipeline generates:

- video-ready research summaries;
- hooks and script briefs;
- storyboard JSON;
- Veo / Seedance / manual-editor prompt packs;
- assembly notes for overlays, subtitles, exact prices and source notes;
- QA prompts before approval and export.

Real video generation remains disabled until provider limits, asset policy and approval
gates are ready.

See `docs/VIDEO_INFOGRAPHIC_STORYBOARD_PIPELINE.md`.

## Product Content Profiles

Raw product rows can now be converted into structured ecommerce cards:

```text
GET   /api/products/{product_id}/content-profile
POST  /api/products/{product_id}/content-profile/generate
PATCH /api/products/{product_id}/content-profile
POST  /api/products/{product_id}/content-profile/approve
```

The profile contains generated title, short and long descriptions, SEO metadata,
specifications JSON, FAQ JSON, schema.org `Product` JSON and alt text suggestions.
Generation follows the local ecommerce skills and marks missing fields instead of
inventing identifiers, exact specs or commercial terms.

See `docs/PRODUCT_CONTENT_PROFILES.md`.

## Viber-First Approval Notifications

Approval notifications use a neutral notification adapter, with Viber as the first real
messenger target. Local development stays in mock mode:

```text
NOTIFICATION_PROVIDER=mock
```

To send approval requests through Viber, configure only local `.env` values:

```text
NOTIFICATION_PROVIDER=viber
VIBER_AUTH_TOKEN=
VIBER_REVIEWER_IDS=viber_user_id_1,viber_user_id_2
VIBER_SENDER_NAME=AI Content Factory
VIBER_WEBHOOK_PUBLIC_URL=https://your-public-domain.example/api/webhooks/viber
VIBER_WEBHOOK_EVENT_TYPES=message,conversation_started,subscribed,unsubscribed,failed
VIBER_WEBHOOK_SECRET_REQUIRED=true
OPERATOR_CONSOLE_URL=https://your-console.example
```

The approval endpoint sends a short Viber message with reply actions:

```text
POST /api/tasks/{task_id}/notify-approval
```

Viber callbacks are received here:

```text
POST /api/webhooks/viber
```

Supported reply commands are `approve:{task_id}` and `rewrite:{task_id}`. Viber can
message only users who have subscribed to or messaged the bot first, so reviewer IDs
must be collected during bot onboarding.

See the full setup checklist in `docs/VIBER_BOT_RUNBOOK.md`.

## Publication Dry Run

Publishing is split into a safe preview step and an explicit publish safety gate. The
current implementation prepares destination-specific CMS payloads without sending anything
to an external CMS:

```text
POST /api/tasks/packages/{package_id}/publication-preview
GET  /api/tasks/packages/{package_id}/publication-previews
POST /api/tasks/publication-previews/{preview_id}/publish
```

The preview payload includes draft title, HTML body, original markdown, SEO metadata,
schema.org JSON and a safety marker showing that it is a dry run. If an approved product
content profile exists for the task product, the payload also includes `product_card_json`
and schema.org `Product`.

Real publish remains blocked unless all safety checks pass:

```text
ENABLE_REAL_PUBLISHING=true
confirmation_phrase=publish:{preview_id}
```

See `docs/CMS_PUBLISHING_SAFETY.md`.

## Media Brief Export

Approved publish packages can also be converted into a safe media brief pack before any
video generation:

```text
POST /api/tasks/packages/{package_id}/media-brief
GET  /api/tasks/packages/{package_id}/media-briefs
```

The generated `video_brief_pack` includes:

- long YouTube video brief;
- Shorts/Reels/TikTok vertical brief;
- Google Veo prompt pack with scene prompts and negative prompts.

Real video generation remains blocked. The brief carries:

```text
real_video_generation_enabled=false
ENABLE_REAL_VIDEO_GENERATION=true
```

For a one-off smoke test without changing `.env`, use:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke-gemini-research.ps1
```

The script enables `RESEARCH_PROVIDER=gemini` and
`ENABLE_GOOGLE_SMOKE_TESTS=true` only for that process.

You can override the model for the smoke process:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke-gemini-research.ps1 -Model gemini-2.0-flash
```

Common external smoke outcomes:

- `503 UNAVAILABLE`: Google accepted the request, but the model is temporarily overloaded.
- `429 RESOURCE_EXHAUSTED`: the API key/project reached quota or has no free-tier quota for that model.

## Planning Docs

- `docs/PROGRAM_MAP_AND_API_KEYS.md`
- `docs/FUNCTIONAL_INVENTORY_AND_MOCK_TEST_PLAN.md`
- `docs/ARTICLE_PRODUCTION_PIPELINE.md`
- `TZ_AI_content_agent.md`
- `TECH_TZ_PRODUCT_ARCHITECTURE.md`
- `WORK_PLAN_ARCHITECTURE_TASK_QUEUE.md`
- `ANALOGS_AND_ARCHITECTURE_REVIEW.md`
