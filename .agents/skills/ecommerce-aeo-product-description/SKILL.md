---
name: ecommerce-aeo-product-description
description: Generate product descriptions optimized for e-commerce, SEO, and answer-engine visibility.
metadata:
  version: 0.1.0
---

# Ecommerce AEO Product Description

Use this skill after product normalization, specification extraction and research.
If available, use `ecommerce-customer-pain-research` first and inject the approved `pain_profile`.

## Rules

- Every important paragraph must be a self-contained answer block.
- Start each section with the direct answer.
- Include the product name or category where useful.
- Use numbers, specs, scenarios and comparisons.
- Separate facts from hypotheses.
- Avoid vague advertising language.
- State the confirmed buyer pain early and connect benefits to that pain.
- Do not exaggerate the pain or promise outcomes that are not supported by evidence.
- Use buyer-word FAQ questions when they are present in `pain_profile`.

## Required Sections

- H1
- short answer block
- buyer pain / problem solved
- product overview
- use cases
- benefits
- limitations
- specifications
- comparison notes
- FAQ
- meta title
- meta description
- alt texts
