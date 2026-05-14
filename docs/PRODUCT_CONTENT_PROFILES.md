# Product Content Profiles

Product content profiles turn a raw product row into a structured ecommerce card that can be reviewed, approved and later pushed to a CMS.

## Current Scope

Implemented:

- one active structured profile per product;
- generated product title;
- short description;
- long AEO-oriented description;
- SEO title and meta description;
- specifications JSON with known facts, missing fields and research-required fields;
- FAQ JSON;
- schema.org `Product` JSON;
- image alt text suggestions;
- manual patch and approval endpoints;
- operator console tab for product-card generation and approval.

The generator is intentionally conservative. It uses product fields, optional task research and optional draft text, but it does not invent GTIN, MPN, SKU, exact specs, price, availability or commercial terms.

## API

```text
GET   /api/products/{product_id}/content-profile
POST  /api/products/{product_id}/content-profile/generate
PATCH /api/products/{product_id}/content-profile
POST  /api/products/{product_id}/content-profile/approve
```

Generation payload:

```json
{
  "language": "ru",
  "source_task_id": "optional-task-id",
  "source_draft_id": "optional-draft-id"
}
```

## Workflow

```text
Product row
-> Product content profile generation
-> Operator review / patch
-> Profile approval
-> Future CMS product-card adapter
```

For mass catalog work, price monitoring and market trend signals should create refresh recommendations first. Only significant changes should move into Viber alerts or human approval queues.

## Next Steps

- Add bulk refresh recommendations by product group.
- Add generated media/image requirements for product galleries.
- Add CMS-specific field mapping after the real destination is selected.
