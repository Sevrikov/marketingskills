---
name: ecommerce-product-normalization
description: Normalize raw product input into structured e-commerce product fields before research, content generation, media generation, or publication.
metadata:
  version: 0.1.0
---

# Ecommerce Product Normalization

Use this skill when a user or integration provides product data that may be incomplete, inconsistent, or unstructured.

## Inputs

- title
- brand
- model
- category
- sku
- gtin
- mpn
- price
- currency
- availability
- source_url
- images
- raw_description

## Workflow

1. Preserve original raw input.
2. Normalize title, brand, model, category and identifiers.
3. Mark missing fields explicitly.
4. Do not invent GTIN, MPN, SKU or exact specs.
5. Create a list of fields that require research.

## Output

Return structured JSON compatible with the `products` table.
