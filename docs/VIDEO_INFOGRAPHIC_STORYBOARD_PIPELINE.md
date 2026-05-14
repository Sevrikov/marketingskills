# Video Infographic & Shorts Storyboard Pipeline

## Цель

Развить статическую инфографику в видеоформат: короткие вертикальные ролики, длинные объясняющие видео, карточки для соцсетей, видео-вставки в статьи и Viber-ready дайджесты. Основа остается прежней: сначала факты, источники и structured data pack, потом сценарий, раскадровка, motion-дизайн и только затем передача в Veo / Seedance / другой video generation provider.

Главная идея: video infographic не должна быть "просто красивым AI-видео". Это доказательная визуальная история о товаре, группе товаров, бренде или ценовом тренде.

## Связь с текущей архитектурой

Видео-инфографический контур использует:

- `infographic_data_pack` из `docs/INFOGRAPHIC_INTELLIGENCE_DESIGN_PIPELINE.md`;
- `product_content_profiles` для точных карточек товаров;
- `price_market_indexes` и `price_trend_events` для рыночных движений;
- `content_opportunities` для тем статей и роликов;
- `media_briefs` как существующий слой video-ready брифов;
- Gemini Deep Research / Tavily / browser scrape как источники данных;
- human approval перед реальной генерацией видео.

Рекомендуемый backlog-элемент: `P0-041: video infographic storyboard and prompt library`.

## Форматы видео-инфографики

### 1. Product Shorts Infographic

Вертикальный короткий ролик по одному товару.

Сюжет:

- hook: главный покупательский вопрос;
- позиция товара в группе;
- 2-3 сильных аргумента;
- 1 честное ограничение;
- короткий CTA.

Подходит для:

- Shorts / Reels / TikTok;
- Viber-тизера;
- карточки товара;
- быстрых промо.

### 2. Product Group Market Pulse

Видео о движении цен в группе товаров.

Сюжет:

- что изменилось на рынке;
- массовое повышение / снижение;
- какие сегменты двигаются сильнее;
- какие товары стали интереснее;
- рекомендация: наблюдать, закупать, переоценить, запустить промо.

### 3. Competitor Battle

Видео-сравнение нескольких товаров.

Сюжет:

- проблема выбора;
- таблица/полосы сравнения;
- сценарии покупателя;
- победители по сценариям, а не абсолютный "лучший";
- сноски по источникам.

### 4. Buyer Guide Explainer

Объясняющее видео по категории.

Сюжет:

- какие характеристики важны;
- что является маркетинговым шумом;
- как читать характеристики;
- как выбрать под бюджет;
- связка с товарами магазина.

### 5. Article Companion Video

Видео-вставка для SEO/AEO статьи.

Сюжет:

- кратко визуализирует центральный тезис статьи;
- дает таблицу/диаграмму;
- ведет к полной статье или карточке товара;
- содержит source note и дату среза.

## Архитектурный пайплайн

```text
Scope
-> Deep Research / Source Collection
-> Infographic Data Pack
-> Video Angle Selection
-> Script Brief
-> Storyboard JSON
-> Shot Prompt Pack
-> Provider Adapter: Veo / Seedance / Manual Editor
-> Generated Clips
-> Assembly Notes
-> Video QA
-> Human Approval
-> CMS / Product Card / Social / Viber Export
```

## Ключевые роли агентов

### Video Research Planner

Определяет, какая информация нужна именно для видео:

- какие данные должны быть на экране;
- какие можно проговорить voiceover;
- какие нельзя показывать без источника;
- какие visual metaphors безопасны;
- какие фрагменты лучше делать статичной графикой, а какие motion video.

### Motion Infographic Strategist

Превращает data pack в динамическую структуру:

- hook;
- sequence;
- графики;
- таблицы;
- transitions;
- visual hierarchy;
- rhythm;
- subtitle density.

### Storyboard Agent

Создает покадровую или посценную раскадровку:

- scene id;
- duration target;
- visual description;
- on-screen text;
- voiceover;
- data refs;
- source refs;
- motion notes;
- provider prompt.

### Provider Prompt Adapter

Переводит универсальную сцену в промпт под конкретный генератор:

- `veo_text_to_video`;
- `veo_image_to_video`;
- `seedance_text_to_video`;
- `seedance_image_to_video`;
- `manual_editor`;
- future providers.

Важно: provider adapter не добавляет новые факты. Он только адаптирует стиль, камеру, движение, длительность и ограничения.

### Assembly Agent

Готовит инструкцию для сборки:

- порядок клипов;
- титры;
- субтитры;
- voiceover;
- music bed;
- final CTA;
- safe margins;
- экспортные размеры.

### Video QA Agent

Проверяет:

- нет ли выдуманных цифр;
- source ids совпадают с data pack;
- титры читаются;
- голос не говорит больше, чем подтверждено;
- визуальная метафора не вводит в заблуждение;
- ролик не делает незаконных или медицинских/финансовых claims;
- все цены имеют дату среза.

## Provider constraints

Ограничения генераторов нужно хранить в capability registry и обновлять по факту доступных аккаунту лимитов.

Текущие ориентиры по публичной документации Google:

- Gemini API документация описывает Veo 3.1 как генерацию 8-секундных видео 720p/1080p с нативным аудио, video extension, first/last frame и до трех reference images.
- Vertex AI документация по Veo 3 указывает для `veo-3.0-generate-001` и `veo-3.0-fast-generate-001`: text-to-video, prompt rewriting, sound generation, aspect ratios 16:9 и 9:16, 720/1080, длина 4/6/8 секунд, до 4 видео за запрос.
- Для Seedance / Seedance 2 публичные страницы и посредники часто расходятся между собой, поэтому в проекте нужно не хардкодить claims, а хранить provider profile, подтвержденный реальным тестом конкретного API-доступа.

Источники:

- Google AI Developers, Veo 3.1 in Gemini API: https://ai.google.dev/gemini-api/docs/video
- Google Cloud Vertex AI, Veo overview: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/video/overview
- Google Cloud Vertex AI, Veo 3 model docs: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/veo/3-0-fast-generate-001

## Предлагаемые сущности БД

### `video_infographic_projects`

- `id`
- `source_type`: `product`, `price_group`, `brand`, `trend_event`, `content_opportunity`, `infographic_project`, `custom`
- `source_id`
- `title`
- `format_type`: `shorts`, `explainer`, `market_pulse`, `competitor_battle`, `article_companion`
- `target_channel`
- `status`: `draft`, `data_ready`, `script_ready`, `storyboard_ready`, `prompt_pack_ready`, `clips_ready`, `qa_failed`, `qa_passed`, `approved`, `exported`
- `created_at`
- `updated_at`

### `video_infographic_storyboards`

- `id`
- `project_id`
- `storyboard_json`
- `script_markdown`
- `shot_count`
- `target_duration_seconds`
- `language`
- `created_at`

### `video_infographic_prompt_packs`

- `id`
- `project_id`
- `provider`
- `provider_profile_json`
- `prompt_pack_json`
- `negative_prompt`
- `created_at`

### `video_infographic_assets`

- `id`
- `project_id`
- `asset_type`: `reference_image`, `generated_clip`, `assembled_video`, `subtitle_file`, `voiceover_script`, `cms_embed`
- `storage_uri`
- `provider`
- `generation_job_id`
- `metadata_json`
- `qa_status`
- `created_at`

### `video_infographic_reviews`

- `id`
- `project_id`
- `review_type`: `script`, `storyboard`, `provider_prompt`, `clip`, `final`
- `status`
- `notes`
- `created_at`

## API MVP

```text
POST /api/video-infographics/projects
GET  /api/video-infographics/projects
GET  /api/video-infographics/projects/{project_id}

POST /api/video-infographics/projects/{project_id}/generate-script
POST /api/video-infographics/projects/{project_id}/generate-storyboard
POST /api/video-infographics/projects/{project_id}/prepare-provider-prompts
POST /api/video-infographics/projects/{project_id}/assets
POST /api/video-infographics/projects/{project_id}/qa
POST /api/video-infographics/projects/{project_id}/approve
POST /api/video-infographics/projects/{project_id}/export-package
```

## `video_infographic_storyboard` JSON

```json
{
  "schema_version": "1.0",
  "project": {
    "title": "Video title",
    "format_type": "shorts",
    "target_channel": "youtube_shorts",
    "aspect_ratio": "9:16",
    "target_duration_seconds": 30,
    "language": "uk-UA",
    "snapshot_date": "2026-05-08"
  },
  "source_data_pack_ref": {
    "type": "infographic_data_pack",
    "id": "data-pack-id"
  },
  "creative_angle": {
    "hook": "Main hook",
    "main_insight": "Main cited insight",
    "viewer_takeaway": "What the viewer should understand",
    "cta": "Open product card / read article / check group"
  },
  "style": {
    "visual_style": "clean ecommerce motion infographic",
    "motion_style": "smooth animated charts, quick product cut-ins",
    "color_logic": "neutral product UI with accent colors for price movement",
    "music_mood": "light energetic tech",
    "voiceover_tone": "clear, factual, confident"
  },
  "scenes": [
    {
      "scene_id": "s01",
      "duration_seconds": 5,
      "purpose": "hook",
      "visual": "Product appears beside a moving price band",
      "on_screen_text": "Is this model above or below market median?",
      "voiceover": "Let's compare this model with the current market range.",
      "data_refs": ["market_position.relative_to_median_pct"],
      "source_ids": ["s1"],
      "motion_notes": "Price band animates from min to max, product marker lands on its position",
      "reference_assets": [],
      "provider_prompt_base": "..."
    }
  ],
  "subtitles": {
    "required": true,
    "max_chars_per_line": 34,
    "burned_in": true
  },
  "qa_requirements": [
    "All prices show currency and snapshot date",
    "No unsupported claims",
    "Source ids visible in final frame or caption"
  ]
}
```

## Библиотека промптов для видео-инфографики

### Prompt 1: Video Scope Builder

```text
Ты video strategist для ecommerce. Определи scope видео-инфографики.

Вход:
- объект: {product_or_group_or_brand_or_trend}
- цель: {goal}
- канал: {channel}
- желаемый формат: {shorts|explainer|market_pulse|competitor_battle|article_companion}
- доступные данные: {data_summary}

Верни JSON:
{
  "format_type": "...",
  "primary_question": "...",
  "target_audience": "...",
  "hook_hypotheses": [],
  "required_data": [],
  "recommended_duration_seconds": 30,
  "aspect_ratio": "9:16|16:9|1:1",
  "risk_notes": []
}

Не выдумывай факты и не обещай, что генератор сможет сделать конкретный эффект без provider profile.
```

### Prompt 2: Video Deep Research Brief

```text
Ты researcher для видео-инфографики ecommerce.

Тема:
{scope}

Найди и структурируй информацию, которая может быть показана в видео:
1. ключевой покупательский конфликт;
2. важные характеристики;
3. конкуренты или альтернативы;
4. ценовой контекст;
5. данные, которые можно показать графиком;
6. данные, которые лучше оставить в voiceover;
7. claims, которые нельзя использовать без проверки.

Требования:
- каждый факт с источником;
- числа без источника запрещены;
- цены с валютой и датой;
- отделяй факт, расчет, гипотезу и маркетинговую интерпретацию.

Верни research brief, source table и список missing data.
```

### Prompt 3: Video Data Pack Normalizer

```text
Ты нормализатор данных для video infographic.

Вход:
- infographic_data_pack: {data_pack}
- research_brief: {research}
- internal_product_data: {product_data}
- market_data: {market_data}

Создай video-ready data summary:
{
  "confirmed_facts": [],
  "visualizable_metrics": [],
  "voiceover_only_facts": [],
  "competitor_points": [],
  "trend_points": [],
  "missing_or_risky_data": [],
  "source_map": []
}

Не добавляй новые факты. Сохраняй source ids.
```

### Prompt 4: Hook & Angle Generator

```text
Ты creative strategist. На основе video-ready data summary предложи 5 hooks для короткого видео.

Для каждого hook верни:
- текст hook;
- какой факт поддерживает hook;
- риск преувеличения;
- лучший формат визуализации;
- подходит ли для Shorts;
- подходит ли для длинного explainer.

Запрещено использовать clickbait, который сильнее фактов.
```

### Prompt 5: Script Brief

```text
Ты сценарист аналитической ecommerce видео-инфографики.

Вход:
- выбранный hook: {hook}
- data summary: {video_data_summary}
- канал: {channel}
- длительность: {duration}
- язык: {language}

Создай script brief:
{
  "title": "...",
  "one_sentence_promise": "...",
  "structure": [
    {"part": "hook", "duration": 4, "goal": "..."},
    {"part": "proof", "duration": 12, "goal": "..."},
    {"part": "comparison", "duration": 10, "goal": "..."},
    {"part": "cta", "duration": 4, "goal": "..."}
  ],
  "voiceover_script": "...",
  "on_screen_text_blocks": [],
  "forbidden_claims": [],
  "source_note": "..."
}

Говори кратко. Не перегружай экран текстом.
```

### Prompt 6: Storyboard Generator

```text
Ты storyboard director для motion infographic.

Создай storyboard JSON по схеме video_infographic_storyboard.

Вход:
- script brief: {script_brief}
- video data summary: {video_data_summary}
- target aspect ratio: {aspect_ratio}
- provider profile: {provider_profile}

Для каждой сцены укажи:
- duration_seconds;
- purpose;
- visual;
- on_screen_text;
- voiceover;
- data_refs;
- source_ids;
- motion_notes;
- provider_prompt_base;
- negative_prompt_notes.

Сцена не должна содержать фактов без data_refs/source_ids.
```

### Prompt 7: Reference Frame Brief

```text
Ты visual director. Подготовь brief для reference frames, которые можно передать video generator или дизайнеру.

Вход:
- storyboard scene: {scene}
- product assets: {assets}
- infographic style: {style}

Верни:
- frame purpose;
- layout;
- visual hierarchy;
- product/image placement;
- chart/table placement;
- text safe areas;
- footnote placement;
- image prompt if reference image must be generated.

Не добавляй логотипы конкурентов, если они не предоставлены легально.
```

### Prompt 8: Veo Prompt Adapter

```text
Ты prompt adapter для Veo-class video generation.

Преобразуй storyboard scene в provider prompt.

Вход:
- scene: {scene}
- provider_profile: {provider_profile}
- reference_frame_notes: {reference_frame_notes}

Верни:
{
  "provider": "veo",
  "model_preference": "{model}",
  "prompt": "...",
  "negative_prompt": "...",
  "aspect_ratio": "...",
  "duration_seconds": 8,
  "needs_reference_image": false,
  "onscreen_text_to_add_in_editing": [],
  "post_editing_notes": []
}

Правила:
- prompt на английском, если provider требует или лучше понимает английский;
- факты и текст с цифрами лучше добавлять на этапе монтажа, если модель плохо держит текст;
- не добавляй новые числа, бренды или claims;
- учитывай duration из provider_profile.
```

### Prompt 9: Seedance Prompt Adapter

```text
Ты prompt adapter для Seedance-class video generation.

Преобразуй storyboard scene в provider prompt.

Вход:
- scene: {scene}
- provider_profile: {provider_profile}
- reference_assets: {reference_assets}

Верни:
{
  "provider": "seedance",
  "model_preference": "{model}",
  "prompt": "...",
  "negative_prompt": "...",
  "aspect_ratio": "...",
  "duration_seconds": 10,
  "input_assets": [],
  "post_editing_notes": []
}

Правила:
- не полагайся на неподтвержденные возможности модели;
- если нужны точные таблицы, цифры или мелкий текст, вынеси это в post-editing;
- provider_profile важнее общих слухов о модели.
```

### Prompt 10: Assembly Plan

```text
Ты video editor. Создай план сборки готового ролика из generated clips, графических overlay и subtitles.

Вход:
- storyboard: {storyboard}
- generated clips: {clips}
- voiceover script: {voiceover}
- subtitles: {subtitles}

Верни:
{
  "timeline": [],
  "overlay_text": [],
  "chart_overlays": [],
  "subtitle_plan": [],
  "music_notes": "...",
  "final_frame": "...",
  "export_presets": []
}

Цифры, таблицы и source ids лучше добавлять как overlay после генерации, если provider не гарантирует точный текст.
```

### Prompt 11: Video QA

```text
Ты QA-редактор video infographic.

Проверь:
- storyboard: {storyboard}
- final transcript: {transcript}
- final captions: {captions}
- visual notes or generated clip descriptions: {clip_descriptions}
- data pack: {data_pack}

Верни:
{
  "qa_status": "pass|fail",
  "blocking_issues": [],
  "non_blocking_issues": [],
  "fact_mismatches": [],
  "text_readability_issues": [],
  "source_note_issues": [],
  "fix_prompt": "..."
}

Любая цифра без источника - blocking issue.
```

### Prompt 12: Publication Pack

```text
Ты content operations editor. Подготовь publication pack для видео-инфографики.

Вход:
- approved storyboard: {storyboard}
- approved asset metadata: {assets}
- data pack: {data_pack}
- target channels: {channels}

Верни:
{
  "title_variants": [],
  "description": "...",
  "short_caption": "...",
  "hashtags": [],
  "alt_text": "...",
  "source_note": "...",
  "viber_digest_text": "...",
  "cms_embed_notes": [],
  "product_card_notes": []
}
```

## Практическая стратегия для Veo / Seedance

Для инфографики лучше не заставлять видео-модель рисовать мелкие таблицы и точные цифры внутри кадра. Более надежный production-процесс:

1. Сгенерировать чистый motion background / product motion / abstract market motion.
2. Наложить точные числа, полосы, таблицы, source ids и subtitles в редакторе или HTML/canvas render step.
3. Использовать reference frames для композиции, но не доверять модели точный текст.
4. Делить длинное видео на короткие сцены под ограничения provider.
5. Хранить каждый клип и prompt как воспроизводимый артефакт.

## MVP-этапы

### P0-041: Video Infographic Storyboard Spec

- этот документ;
- обновленный skill `ecommerce-video-brief`;
- prompt library для video infographic;
- provider adapter plan.

### P0-042: Backend Storyboard Models

- `video_infographic_projects`;
- `video_infographic_storyboards`;
- mock storyboard generation;
- связь с `infographic_data_pack` и `media_briefs`.

### P0-043: Prompt Pack Generator

- provider profiles;
- Veo prompt adapter;
- Seedance prompt adapter;
- negative prompt policy;
- no-real-generation safety gate.

### P0-044: Operator Console

- вкладка `Video Infographics`;
- создание проекта;
- просмотр script/storyboard;
- copy prompt для Veo/Seedance;
- upload generated clip metadata.

### P0-045: QA & Export

- video QA endpoint;
- publication pack;
- Viber digest;
- CMS embed;
- product-card video block.

## Следующий практический шаг

После `P0-040` для статического data pack сделать `P0-042`: backend-модели video infographic projects/storyboards и mock storyboards. Тогда мы сможем брать товар или группу товаров, строить data pack, выбирать формат Shorts/Explainer и получать раскадровку с provider-ready prompt pack без реального запуска дорогой генерации.
