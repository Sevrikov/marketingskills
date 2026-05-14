---
name: ecommerce-video-brief
description: Create marketing video briefs, video infographic storyboards, Shorts concepts, scene prompt packs, and Veo/Seedance-ready handoff briefs for ecommerce products, product groups, brands, articles, and market trends. Use before any video generation, especially when Codex must turn structured research or infographic data packs into scripts, storyboards, provider prompts, subtitles, QA, or publication packs.
metadata:
  version: 0.1.0
---

# Ecommerce Video Brief

Use this skill before video generation. Expensive video generation must not start before brief approval.

For video infographics, combine this skill with `ecommerce-customer-pain-research` and `ecommerce-infographic-brief`: pain profile first, data pack second, script/storyboard third, provider prompt fourth.

## Required Fields

- product or category
- goal
- audience
- platform
- format
- key message
- offer
- CTA
- required facts
- forbidden claims
- tone
- duration
- language
- subtitle requirements
- scene list
- source ids and snapshot date for every price, metric, comparison or claim
- approved or draft `pain_profile`
- buyer words and objections if available
- provider target: `veo`, `seedance`, `manual_editor`, or `unknown`
- aspect ratio and safe-area requirements
- voiceover requirements
- generated-text risk policy

## Output

Return a markdown brief and structured JSON for downstream storyboard and scene prompt agents.

For video infographics, return:

- `video_data_summary`;
- `pain_profile` summary and pain-to-proof map;
- `script_brief`;
- `video_infographic_storyboard`;
- `provider_prompt_pack`;
- `assembly_plan`;
- `video_qa_prompt`;
- `publication_pack_prompt`.

## Video Infographic Rules

- Do not ask a video model to generate exact small text, tables, prices or source ids when those can be overlaid later.
- Prefer generated clips for product motion, environment, camera movement, transitions and visual mood.
- Put exact numbers, chart bars, subtitles and source notes in an editing/overlay step.
- Keep every scene tied to `data_refs` and `source_ids`.
- Keep the confirmed buyer pain visible in the hook, first scene, proof scenes, and CTA.
- Do not turn hypothetical pain into fear-based marketing.
- Treat provider claims as capability profiles that must be verified for the current account.
- Keep real generation gated behind human approval and explicit configuration.

The canonical video infographic workflow lives in `docs/VIDEO_INFOGRAPHIC_STORYBOARD_PIPELINE.md`.
