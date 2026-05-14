---
name: ecommerce-article-production-brief
description: Create ecommerce article production briefs, article data packs, SEO/AEO article specifications, image briefs, infographic slots, asset insertion plans, and QA prompts for product, category, brand, price group, or content opportunity articles. Use when Codex needs to plan article writing, data collection, picture requirements, generated image prompts, article assembly, or CMS-ready article assets.
---

# Ecommerce Article Production Brief

## Workflow

1. Start from product, group, brand, topic, or content opportunity.
2. Build or request `pain_profile` and `article_data_pack`.
3. Create article brief before drafting.
4. Draft article with explicit asset slots.
5. Create image brief and infographic brief from the same facts.
6. Keep generated images separate from factual overlays.
7. Insert only approved assets into article/package/CMS payload.
8. QA text, facts, pain claims, images, alt text, captions, and source notes.

## Required Outputs

- `article_data_pack`;
- article ТЗ / `article_brief`;
- article draft requirements;
- `image_brief_json`;
- infographic requirements;
- asset slot map;
- QA checklist;
- forbidden claims.

## Rules

- Do not generate article copy before data pack and brief are clear.
- Do not let image generation invent facts, logos, ratings, prices, tables, or source notes.
- Use asset slots such as `{{image:hero}}` and `{{infographic:power_vs_use_case}}`.
- Exact prices, charts, labels and tables should be rendered as controlled overlays or HTML/SVG, not trusted to a bitmap model.
- Every image needs purpose, dimensions, alt text, caption and approval status.

The canonical spec lives in `docs/ARTICLE_PRODUCTION_PIPELINE.md`.
