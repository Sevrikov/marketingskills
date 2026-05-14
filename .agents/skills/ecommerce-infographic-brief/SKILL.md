---
name: ecommerce-infographic-brief
description: Create evidence-backed ecommerce infographic data packs, analytical design briefs, browser design-agent prompts, and QA prompts for product, product-group, brand, market-trend, article, CMS, social, or Viber infographics. Use when Codex needs to plan or generate structured infographic prompts, compare products visually, prepare Claude/design-browser prompts, or turn Gemini/Tavily/browser research into cited visual assets.
---

# Ecommerce Infographic Brief

## Workflow

1. Define the infographic scope: product, price group, brand, trend event, content opportunity, or custom market question.
2. Run or request customer pain research when a product/category pain angle matters.
3. Collect or request a source corpus from internal product data, price monitor data, known competitor URLs, Tavily, browser scraping, or Gemini grounded research.
4. Build a strict `infographic_data_pack` before writing any design prompt.
5. Separate facts, calculations, hypotheses, marketing interpretations, and missing data.
6. Create a design brief that names the main insight, pain angle, visual blocks, chart/table specs, source footnotes, dimensions, and target channel.
7. Generate a browser design-agent prompt that forbids new facts and requires editable output.
8. Generate a QA prompt that compares the design artifact back to the data pack and `pain_profile`.

## Required Outputs

For a complete brief, return:

- `infographic_data_pack` JSON or a schema-compatible draft;
- `pain_profile` summary when available;
- `design_brief` Markdown;
- `browser_design_prompt`;
- `qa_prompt`;
- `revision_prompt` when QA issues are known.

## Data Rules

- Never invent prices, specs, market shares, rankings, awards, reviews, or competitor claims.
- Every number needs a source id, internal calculation note, currency/unit, and snapshot date.
- Conflicting values stay visible as conflicts until a rule or human resolves them.
- Use `unknown`, `needs_review`, or `hypothesis` instead of filling gaps.
- Keep public claims weaker than the evidence.
- If a buyer pain is confirmed, show it as a decision problem and map it to proof.
- If a pain is only hypothetical, do not make it the headline.

## Design Rules

- Prefer visual blocks that help decisions: price bands, competitor bars, feature matrices, buyer-fit scorecards, trend strips, callouts, and footnotes.
- Add a pain-to-proof block when `pain_profile` is available.
- Include source footnotes and snapshot date in the design brief.
- Ask browser design tools for editable HTML/CSS/SVG or a structured design artifact.
- Require readable labels, chart units, consistent scales, no overlap, and no decorative fake data.
- Treat Claude/design-browser output as a design surface, not a factual source.

## Prompt Chain

Use this order:

1. Scope Builder
2. Customer Pain Research
3. Gemini Deep Research Brief
4. Source Corpus Extractor
5. Data Pack Normalizer
6. Market Analyst
7. Infographic Creative Strategy
8. Browser Design Agent Prompt
9. Design QA
10. Revision Prompt
11. CMS / Social Export Prompt

The canonical prompt library lives in `docs/INFOGRAPHIC_INTELLIGENCE_DESIGN_PIPELINE.md`.
