# Content Opportunity Discovery

Content opportunity discovery finds article topics for a selected product, price group, brand, category or custom query.

## Workflow

```text
Product / group / brand / category
-> source collection
-> research synthesis
-> topic opportunities
-> create SEO article task
```

## API

```text
POST /api/content-opportunities/discover
GET  /api/content-opportunities
POST /api/content-opportunities/{opportunity_id}/create-task
```

Discovery payload:

```json
{
  "product_id": "optional-product-id",
  "price_group_id": "optional-group-id",
  "brand": "optional brand",
  "category": "optional category",
  "query": "optional extra query",
  "language": "ru",
  "market": "UA",
  "limit": 8
}
```

Each opportunity stores:

- title and H1;
- intent: commercial, comparison, problem, FAQ, informational or trend;
- priority score;
- reason;
- outline;
- recommended product IDs;
- source snippets;
- research summary;
- optional created `seo_article` task.

## Operator Console

The static console has an `Opportunities` tab:

- choose product, group, brand, category or query;
- click `Discover topics`;
- review scores, intents, sources and reasons;
- create a `seo_article` task from any opportunity.

## Provider Modes

Local development uses mock source/research providers. Real deep research is enabled through the existing source and research adapters:

```text
SOURCE_PROVIDER=tavily
RESEARCH_PROVIDER=gemini
```

Real API usage remains opt-in through local `.env` only.
