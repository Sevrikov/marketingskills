# Article Production Pipeline

## Цель

Сделать производство статьи отдельным управляемым процессом, а не просто "сгенерировать текст". Для ecommerce статья должна проходить через:

1. сбор данных;
2. customer pain research;
3. article data pack;
4. ТЗ/бриф статьи;
5. draft generation;
6. fact/pain/SEO/AEO QA;
7. ТЗ на изображения и инфографику;
8. генерацию или подбор изображений;
9. вставку ассетов в статью;
10. publish package;
11. CMS preview / approval / publish gate.

## Текущий статус

Реализовано:

- `content_opportunities` по товару/группе/бренду;
- `seo_article` task;
- mock research;
- draft -> critic -> rewrite;
- approval;
- publish package;
- CMS Article preview;
- media brief после publish package;
- realistic smoke для статьи по группе солнечных зарядок.

Не реализовано как отдельный модуль:

- строгий `article_data_pack`;
- отдельное ТЗ статьи;
- отдельное ТЗ на картинки;
- image generation adapter;
- image approval;
- вставка image/infographic assets в article body/CMS payload;
- visual QA.

## Главный пайплайн

```text
Product / Group / Brand / Topic
-> Content Opportunity
-> Customer Pain Research
-> Source Collection / Deep Research
-> Article Data Pack
-> Article Brief / ТЗ
-> Draft Generation
-> Critic / Rewrite
-> Image Brief / ТЗ на картинки
-> Image / Infographic Asset Generation
-> Asset QA
-> Article Assembly
-> Human Approval
-> Publish Package
-> CMS Preview
```

## Article Data Pack

`article_data_pack` должен быть входом для статьи, инфографики и изображений.

```json
{
  "schema_version": "1.0",
  "scope": {
    "type": "price_group",
    "title": "Мобільні сонячні зарядки",
    "language": "uk",
    "market": "UA",
    "snapshot_date": "2026-05-08"
  },
  "pain_profile_ref": null,
  "main_question": "Як вибрати портативну сонячну батарею для телефона, ноутбука або походу?",
  "search_intents": ["commercial", "comparison", "problem", "faq"],
  "confirmed_facts": [],
  "market_context": {
    "min_price": "970.00",
    "median_price": "2400.00",
    "max_price": "4950.00",
    "currency": "UAH",
    "source": "internal_market_index"
  },
  "recommended_products": [],
  "sections": [],
  "faq_questions": [],
  "image_requirements": [],
  "infographic_requirements": [],
  "sources": [],
  "missing_or_risky_data": []
}
```

## ТЗ статьи

Article brief должен отвечать на вопросы:

- кто читатель;
- какую боль закрываем;
- какой главный поисковый intent;
- какой H1;
- какие H2/H3;
- какие товары упоминаем;
- какие таблицы нужны;
- какие изображения нужны;
- какие claims запрещены;
- какие источники обязательны;
- какой CTA.

### Prompt: Article Brief

```text
Ты ecommerce content strategist. Создай ТЗ статьи на основе article_data_pack.

Вход:
- article_data_pack: {article_data_pack}
- pain_profile: {pain_profile}
- market_index: {market_index}
- content_opportunity: {content_opportunity}

Верни:
{
  "title": "...",
  "h1": "...",
  "intent": "...",
  "audience": "...",
  "main_pain_angle": "...",
  "outline": [],
  "required_facts": [],
  "comparison_tables": [],
  "product_blocks": [],
  "faq": [],
  "image_brief_needed": true,
  "infographic_brief_needed": true,
  "forbidden_claims": [],
  "cta": "..."
}

Не добавляй факты, которых нет в data pack.
```

## Написание статьи

Статья должна:

- начинаться с боли или покупательского вопроса;
- давать быстрый ответ в первых 1-2 абзацах;
- объяснять критерии выбора;
- показывать ограничения;
- связывать товары с задачами;
- включать FAQ;
- содержать внутренние ссылки/товарные блоки;
- иметь source notes, если использовались внешние данные.

### Prompt: Article Draft

```text
Ты пишешь ecommerce SEO/AEO статью.

Вход:
- article_brief: {article_brief}
- article_data_pack: {article_data_pack}
- pain_profile: {pain_profile}

Требования:
- пиши на языке {language};
- начинай с прямого ответа;
- боль покупателя должна быть видна, если она подтверждена;
- каждый важный claim должен опираться на data pack;
- не выдумывай цены, характеристики, гарантию, отзывы или результаты;
- добавь места для изображений как asset slots:
  {{image:hero}}
  {{image:comparison_table}}
  {{image:how_to_choose}}
  {{infographic:power_vs_use_case}}

Верни Markdown.
```

## ТЗ на картинки

Для статьи нужны не просто "красивые картинки", а ассеты с задачей.

Типы:

- `hero_image` - первый экран статьи;
- `product_context_image` - товар в сценарии использования;
- `comparison_table_image` - визуальная таблица;
- `infographic` - диаграмма/таблица/шкала;
- `safety_note_image` - ограничения и предупреждения;
- `social_preview` - превью для соцсетей/Viber.

### Image Brief JSON

```json
{
  "schema_version": "1.0",
  "article_id": "article-task-id",
  "assets": [
    {
      "slot": "hero",
      "asset_type": "hero_image",
      "purpose": "Show mobile solar charging use case",
      "prompt": "...",
      "negative_prompt": "...",
      "dimensions": "1200x675",
      "must_include": [],
      "must_not_include": ["fake logos", "unsupported text claims"],
      "source_refs": []
    }
  ]
}
```

### Prompt: Image Brief

```text
Ты visual editor для ecommerce статьи. Создай ТЗ на изображения.

Вход:
- article_brief: {article_brief}
- article_draft: {article_draft}
- article_data_pack: {article_data_pack}
- brand/product constraints: {constraints}

Верни image_brief_json:
- hero;
- 1-2 context images;
- comparison or infographic asset;
- social preview;
- alt text для каждого asset;
- forbidden visual claims.

Правила:
- не рисовать фальшивые логотипы;
- не писать мелкий текст внутри AI-image, если его лучше наложить версткой;
- точные цифры, цены и таблицы лучше делать как overlay/HTML/SVG;
- каждое изображение должно иметь purpose.
```

## Генерация картинок

Реальная генерация должна быть отдельным opt-in шагом.

Безопасный MVP:

```text
Article Draft
-> Image Brief
-> Human Review
-> Generate Image / Upload Manual Asset
-> Asset QA
-> Insert Asset Slots
```

Генератор изображений не должен быть источником фактов. Он создает визуал, а числа, таблицы, цены, source ids и подписи накладываются отдельным controlled layer.

## Добавление картинок в статью

Статья должна хранить asset slots:

```markdown
{{image:hero}}
{{image:product_context_1}}
{{infographic:power_vs_use_case}}
{{image:safety_notes}}
```

После approval ассеты подставляются в publish package:

```json
{
  "assets": [
    {
      "slot": "hero",
      "asset_id": "asset-id",
      "url": "storage://...",
      "alt_text": "...",
      "caption": "...",
      "status": "approved"
    }
  ]
}
```

CMS payload должен получать:

- HTML body with image placements;
- image metadata;
- alt text;
- captions;
- source/copyright notes;
- OpenGraph image if approved.

## API план

```text
POST /api/article-production/{task_id}/data-pack
POST /api/article-production/{task_id}/brief
POST /api/article-production/{task_id}/image-brief
POST /api/article-production/{task_id}/assets
POST /api/article-production/{task_id}/assemble
POST /api/article-production/{task_id}/qa
POST /api/article-production/{task_id}/approve-assets
```

## DB план

### `article_data_packs`

- `id`
- `task_id`
- `scope_type`
- `scope_id`
- `data_pack_json`
- `status`
- `created_at`

### `article_briefs`

- `id`
- `task_id`
- `brief_json`
- `brief_markdown`
- `status`
- `created_at`

### `article_assets`

- `id`
- `task_id`
- `slot`
- `asset_type`
- `brief_json`
- `storage_uri`
- `alt_text`
- `caption`
- `status`
- `qa_json`
- `created_at`

## Следующий практический шаг

Сделать `P0-051`: Article production backend MVP:

- mock `article_data_pack`;
- mock `article_brief`;
- mock `image_brief`;
- asset slots в publish package;
- realistic smoke: solar category article -> article brief -> image brief -> package with asset slots.

## Operator Article Studio MVP

Implemented in `frontend/` as `P0-052`:

- selected `seo_article` task gets an Article Studio tab;
- the tab combines research report, article brief, draft preview, editor checkpoint, image/infographic brief and publication handoff;
- editable checkpoints are stored in browser `localStorage` by task id;
- no real external API calls are made by the preview;
- backend persistence is still planned.

Implemented backend persistence in `P0-053`:

- `GET /api/tasks/{task_id}/article-checkpoints`;
- `PUT /api/tasks/{task_id}/article-checkpoints/{checkpoint_type}`;
- `DELETE /api/tasks/{task_id}/article-checkpoints/{checkpoint_type}`;
- supported checkpoint types: `article_brief`, `editor_notes`, `image_brief`, `qa`;
- frontend still keeps a local fallback copy in browser storage when backend save fails.

Durable review checkpoint records:

```text
article_review_checkpoints
- id
- task_id
- checkpoint_type: article_brief | editor_notes | image_brief | qa
- body_markdown
- status: draft | reviewed | approved
- reviewer
- created_at
- updated_at
```

`P0-054` connects persisted checkpoints to production flow:

- generation prompt context can include saved Article Studio checkpoints;
- rewrite prompt context can include saved `editor_notes`, `article_brief`, `image_brief` and `qa`;
- publish package JSON includes `article_studio.checkpoints`;
- publish package Markdown includes an `Article Studio Checkpoints` section;
- publish package JSON includes extracted article asset slots such as `{{image:hero}}`.

`P0-055` adds a fast human-in-the-loop rewrite path:

- `POST /api/tasks/{task_id}/rewrite-from-checkpoints`;
- task must be `waiting_approval`;
- backend saves/uses the latest Article Studio checkpoints;
- backend rewrites from the latest final draft without rerunning research;
- the rewritten draft is stored as a new `final` draft;
- task returns to `waiting_approval` with step `article_studio_rewrite_ready`;
- frontend exposes this as `Rewrite from notes` in Article Studio.

`P0-056` adds operator rewrite diff:

- compares the previous `final` draft with the latest `final` draft;
- added lines use a translucent green background;
- removed lines use a translucent red background;
- unchanged lines remain neutral;
- diff is rendered directly in Article Studio after rewrite.

`P0-057` adds rewrite version decisions:

- latest rewrite can be accepted or rejected from Article Studio;
- decision is stored in draft `metadata_json.version_decision`;
- accepted/rejected state is shown in the rewrite diff badge;
- publish package export prefers the latest accepted `final` draft;
- rejected `final` drafts are skipped during export.

`P0-058` adds the first image asset loop:

- article assets are generated from final-draft slots such as `{{image:hero}}` and `{{infographic:comparison}}`;
- generated records live in `article_assets`;
- each asset stores slot, type, mock storage URI, brief JSON, alt text, caption, QA JSON and review status;
- Article Studio exposes `Prepare image assets`, `Approve asset` and `Reject asset`;
- publish package JSON includes `article_studio.assets` and `article_studio.approved_assets`;
- publish package Markdown includes an `Article Assets` section;
- real image generation remains out of the MVP path until a provider is explicitly enabled.

`P0-059` adds CMS preview placement:

- CMS preview replaces article asset tokens with `<figure>` blocks;
- approved assets with `mock://` storage render as upload/generator placeholders;
- assets without approval remain visible as editorial placeholders, not final images;
- CMS payload includes `media_assets_json` with slot, type, status, URI, alt text, caption and `cms_insertion`;
- Article Studio shows a visual empty asset block with loading/review state before real image generation is connected.

`P0-060` adds the image upload/generator contract:

- `ImageGenerationAdapter` is the provider boundary for generated article visuals;
- the default `MockImageGenerationAdapter` returns a safe SVG data URI, so the UI can exercise a real image preview without paid calls;
- `POST /api/tasks/{task_id}/article-assets/{asset_id}/generate-image` generates/updates one asset;
- `POST /api/tasks/{task_id}/article-assets/{asset_id}/upload` attaches a manual URL, storage URI or data URI;
- upload/generation resets the asset to `generated`, because the visual needs review again before publishing;
- Article Studio exposes `Generate mock image` and `Attach URL` controls per asset;
- CMS preview renders approved non-mock URLs/data URIs as `<img>` and keeps unresolved assets as placeholders.

`P0-061` adds Gemini image provider wiring:

- `GeminiImageGenerationAdapter` implements the same `ImageGenerationAdapter` interface;
- provider is selected with `IMAGE_GENERATION_PROVIDER=gemini`;
- real calls require `ENABLE_REAL_IMAGE_GENERATION=true` and `GOOGLE_API_KEY`;
- default model is `gemini-3.1-flash-image-preview`, with configurable fallback list in `GEMINI_IMAGE_MODELS`;
- Gemini inline image parts are converted to browser-previewable `data:<mime>;base64,...` URIs;
- the same Article Studio `generate-image` endpoint is used for mock and Gemini providers.
