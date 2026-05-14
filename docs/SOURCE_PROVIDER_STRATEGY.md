# Source Provider Strategy

Last updated: 2026-05-07

## Decision

The research pipeline now has a separate `SourceProvider` layer before the final
research synthesizer:

```text
Content Task
-> Query Builder
-> SourceProvider
-> Source Corpus Formatter
-> ResearchAdapter
-> ContentResearchReport
-> Draft Generation
```

This keeps source collection independent from synthesis. Tavily can be used for the
fast MVP path, while Serper, DataForSEO and Brave can be added later without changing
the content pipeline.

## Current Providers

| Provider | Status | Use |
|---|---|---|
| `mock` | Implemented | Default local provider with deterministic documents. |
| `tavily` | Implemented | Real AI-ready web source collection with snippets/raw content. |
| `serper` | Planned | Cheap Google SERP links/snippets; needs page extraction. |
| `dataforseo` | Planned | Cheapest queued volume Google SERP; needs async queue handling and extraction. |
| `brave` | Planned | Independent web index fallback for agentic search. |

## Tavily MVP Config

Use Tavily only in local `.env` or a secret manager:

```text
SOURCE_PROVIDER=tavily
TAVILY_API_KEY=
SOURCE_COLLECTION_ENABLED=true
SOURCE_COLLECTION_REQUIRED=false
SOURCE_COLLECTION_MAX_RESULTS=5
SOURCE_CORPUS_MAX_CHARS=20000
TAVILY_SEARCH_DEPTH=basic
TAVILY_INCLUDE_RAW_CONTENT=markdown
TAVILY_INCLUDE_ANSWER=basic
```

`SOURCE_COLLECTION_REQUIRED=false` means a temporary search-provider failure does not
break the entire content pipeline. Set it to `true` only when source collection is a
hard requirement.

## Cost Guidance

For a 50-query deep research task:

- Tavily is fastest to integrate because it can return AI-ready snippets/raw content.
- Serper and DataForSEO are cheaper for SERP volume, but require a page extraction
  and cleaning stage.
- Brave is valuable as an independent-index fallback.

## Next Work

1. Add query planning so one research task can generate 20-50 targeted source queries.
2. Add corpus dedupe by URL and near-duplicate text.
3. Add `PageExtractor` for Serper/DataForSEO results.
4. Add source cost ledger similar to the Gemini quota ledger.
5. Add Deep Research File Search Store integration after real project limits allow it.
