# Gemini Rate Limits Snapshot

Snapshot source: `C:\Users\sevri\Downloads\Rate Limit _ Google AI Studio.mhtml`

Snapshot date: 2026-05-07

## Decision

Use these safe defaults for this project after the real API probe:

| Role | Model | Reason |
|---|---|---|
| Content generation | `gemini-2.5-flash-lite` | Real low-cost text call succeeded. |
| Critic / rewrite | `gemini-2.5-flash-lite` | Real low-cost text call succeeded. |
| Grounded research smoke | `gemini-2.5-flash-lite` | Real grounded call succeeded and returned sources. |
| Text fallback | `gemini-3-flash-preview` | API id exists and returned HTTP 200, but one probe returned empty text. |

Avoid for now:

| Model | Reason |
|---|---|
| `gemini-2.5-flash` | Snapshot showed `21 / 20` RPD, already above daily limit. |
| `gemini-2.5-pro` | Snapshot showed `0 / 0` RPM, TPM and RPD. |
| `gemini-3.1-pro` | Snapshot showed `0 / 0` RPM, TPM and RPD. |
| `gemini-3.1-flash-lite` | AI Studio display name is not the executable API id; use `gemini-3.1-flash-lite-preview`, which returned `503` in the real probe. |
| Veo models | Snapshot showed `0 / 0`; keep generation disabled. |
| Image models | Snapshot showed `0 / 0`; keep generation disabled. |

## Real API Probe

Probe date: 2026-05-07

| Pool | Model | Result |
|---|---|---|
| Text | `gemini-3.1-flash-lite` | `404 NOT_FOUND`; not an executable v1beta model id. |
| Text | `gemini-3.1-flash-lite-preview` | `503 UNAVAILABLE`; model exists but was under high demand. |
| Text | `gemini-3-flash` | `404 NOT_FOUND`; not an executable v1beta model id. |
| Text | `gemini-3-flash-preview` | HTTP 200, but returned empty text in one low-cost probe. |
| Text | `gemini-2.5-flash-lite` | Success, returned `OK MODEL`. |
| Text | `gemini-flash-lite-latest` | `503 UNAVAILABLE`; model exists but was under high demand. |
| Text | `gemma-4-26b-a4b-it` | `500 INTERNAL`; not stable enough for current workflow. |
| Embedding | `gemini-embedding-001` | Success, 3072 dimensions. |
| Embedding | `gemini-embedding-2` | Success, 3072 dimensions. |
| Text + Search grounding | `gemini-2.5-flash-lite` | Success, returned answer and 3 grounded chunks. |

## Parsed AI Studio Limits

| Model ID | Name | Category | Status | RPM | TPM | RPD |
|---|---|---|---|---:|---:|---:|
| `gemini-2.5-flash` | Gemini 2.5 Flash | Text-out models | Reached limit | 4 / 5 | 47.11K / 250K | 21 / 20 |
| `gemini-2.5-pro` | Gemini 2.5 Pro | Text-out models | Below limit | 0 / 0 | 0 / 0 | 0 / 0 |
| `gemini-2.0-flash` | Gemini 2 Flash | Text-out models | Below limit | 0 / 0 | 0 / 0 | 0 / 0 |
| `gemini-2.0-flash-lite` | Gemini 2 Flash Lite | Text-out models | Below limit | 0 / 0 | 0 / 0 | 0 / 0 |
| `gemini-3-flash` | Gemini 3 Flash | Text-out models | Below limit | 0 / 5 | 0 / 250K | 0 / 20 |
| `gemini-3.1-flash-lite` | Gemini 3.1 Flash Lite | Text-out models | Below limit | 0 / 15 | 0 / 250K | 0 / 500 |
| `gemini-3.1-pro` | Gemini 3.1 Pro | Text-out models | Below limit | 0 / 0 | 0 / 0 | 0 / 0 |
| `gemini-2.5-flash-lite` | Gemini 2.5 Flash Lite | Text-out models | Below limit | 0 / 10 | 0 / 250K | 0 / 20 |
| `gemini-embedding-1.0` | Gemini Embedding 1 | Other models | Below limit | 0 / 100 | 0 / 30K | 0 / 1K |
| `gemini-embedding-2` | Gemini Embedding 2 | Other models | Below limit | 0 / 100 | 0 / 30K | 0 / 1K |
| `gemini-2.5-flash-tts` | Gemini 2.5 Flash TTS | Multi-modal generative models | Below limit | 0 / 3 | 0 / 10K | 0 / 10 |
| `gemini-3.1-flash-tts` | Gemini 3.1 Flash TTS | Multi-modal generative models | Below limit | 0 / 3 | 0 / 10K | 0 / 10 |
| `veo-3-generate` | Veo 3 Generate | Multi-modal generative models | Below limit | 0 / 0 | 0 / 0 |  |
| `veo-3-fast-generate` | Veo 3 Fast Generate | Multi-modal generative models | Below limit | 0 / 0 | 0 / 0 |  |
| `veo-3-lite-generate` | Veo 3 Lite Generate | Multi-modal generative models | Below limit | 0 / 0 | 0 / 0 |  |
| `deep-research-pro-preview` | Deep Research Pro Preview | Agents | Below limit | 0 / 0 | 0 / 0 | 0 / 0 |
| `gemini-2.5` | Gemini 2.5 | Search grounding | Below limit | 1 / 1.5K |  |  |
| `default` | Default | Search grounding | Below limit | 0 / 1.5K |  |  |

## API Reality

The Gemini Developer API exposes model calls, but the official rate-limit docs direct users
to AI Studio for active project rate limits. It does not document a Gemini Developer API
endpoint for reading the current per-project AI Studio RPM/TPM/RPD table.

For Vertex AI deployments, Google Cloud quotas are available through the Google Cloud quota
system, but that is not the same operational surface as this AI Studio Developer API key.

## Online Strategy

1. Keep real calls opt-in through `LLM_PROVIDER=gemini` or `RESEARCH_PROVIDER=gemini`.
2. Store a manual AI Studio snapshot in docs after each quota change.
3. Enforce local daily request caps through `GeminiQuotaGovernor`.
4. Prefer models with nonzero RPM/TPM/RPD and enough daily headroom.
5. On `429 RESOURCE_EXHAUSTED`, block that model locally for the current UTC day and fallback.
6. On `503 UNAVAILABLE`, cool that model down locally and fallback to the next configured model.
7. Inspect local usage with `python -m app.cli gemini-quota-status` from `backend/`.
8. Keep Veo generation disabled until AI Studio shows nonzero Veo limits and a separate approval gate exists.
