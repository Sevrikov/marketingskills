# Infographic Intelligence & Design Pipeline

## Цель

Построить отдельный контур для аналитических инфографик по товарам, группам товаров, брендам и рыночным трендам. Инфографика должна быть не просто красивой картинкой, а проверяемым визуальным аналитическим продуктом:

- собрать факты, цены, характеристики, позиции товара и конкурентов;
- нормализовать данные в структурированный `data pack`;
- синтезировать выводы для покупателя, маркетолога и контент-менеджера;
- подготовить дизайн-бриф и промпты для браузерного дизайн-инструмента;
- проверить источники, читаемость, корректность диаграмм и отсутствие выдуманных claims;
- экспортировать готовые ассеты для карточек товаров, статей, соцсетей, CMS и Viber-дайджестов.

## Место в продукте

Инфографический контур дополняет уже существующие модули:

- `product_content_profiles` - структурированная карточка товара;
- `price_groups`, `price_market_indexes`, `price_trend_events` - биржевой мониторинг цен по группам;
- `content_opportunities` - темы статей и исследовательские возможности;
- `content_research_reports` и source corpus - исследовательская база;
- `media_briefs` - видео и Veo-ready брифы;
- publish package / CMS dry-run - безопасная упаковка в публикацию.

Рекомендуемое название нового backlog-элемента: `P0-039: infographic intelligence and design prompt library`.

## Типы инфографик

### 1. Product Position Infographic

Показывает место конкретного товара в группе:

- цена товара против min / avg / median / max по группе;
- позиция в ценовом коридоре;
- сильные и слабые стороны относительно конкурентов;
- основные характеристики;
- кому подходит;
- когда лучше выбрать альтернативу;
- источники и дата среза.

### 2. Competitor Comparison Infographic

Сравнивает 3-7 товаров:

- цена;
- ключевые характеристики;
- гарантия / комплектация / наличие;
- пользовательские критерии выбора;
- итоговая оценка по сценариям;
- примечания по спорным или неполным данным.

### 3. Market Trend Infographic

Показывает движение рынка:

- массовое повышение или снижение цен;
- группы товаров с самым сильным движением;
- топ-позиции, где изменение значимо;
- распределение конкурентов по ценовым сегментам;
- сигнал для закупки, переоценки или промо.

### 4. Buyer Guide Infographic

Объясняет выбор категории:

- какие характеристики действительно важны;
- типовые ошибки выбора;
- диапазоны цен;
- сценарии использования;
- decision matrix для разных покупателей.

### 5. Article / AEO Infographic

Поддерживает статью:

- тезисные блоки;
- сравнительные таблицы;
- диаграммы;
- мини-глоссарий;
- FAQ-выжимка;
- источники для доверия и answer-engine цитируемости.

## Архитектурный пайплайн

```text
Scope
-> Source Collection
-> Gemini Deep Research / Tavily / Known URL Browser Scrape
-> Structured Data Pack
-> Analyst Synthesis
-> Infographic Strategy
-> Design Brief
-> Design Prompt Library
-> Browser Design Operator
-> Asset QA
-> Human Approval
-> CMS / Product Card / Social / Viber Export
```

## Роли агентов

### Data Collector Agent

Собирает данные по scope: товар, группа, бренд, конкуренты, URL, известные источники, свежие цены и характеристики.

Выход:

- список источников;
- raw snippets / extracted text;
- дата среза;
- предупреждения по недоступным страницам.

### Deep Research Agent

Использует Gemini grounded research для более глубокого анализа:

- что важно в категории;
- какие критерии сравнения реально влияют на выбор;
- какие бренды и модели часто сравнивают;
- какие claims безопасно использовать;
- какие данные требуют ручной проверки.

Выход:

- исследовательский отчет;
- факты с источниками;
- гипотезы отдельно от фактов;
- список недостающих данных.

### Data Normalizer Agent

Превращает исследование в строгий JSON:

- товары;
- конкуренты;
- характеристики;
- цены;
- рыночные позиции;
- источники;
- confidence;
- missing fields.

Главное правило: если число, характеристика или claim не подтверждены, поле помечается как `unknown`, `needs_review` или `hypothesis`, а не выдумывается.

### Market Analyst Agent

Считает:

- ценовой индекс товара;
- позицию в группе;
- отклонение от медианы;
- сигнальность изменения;
- сильные / слабые стороны;
- buyer-fit scores.

### Infographic Strategist

Выбирает тип инфографики и композицию:

- какой главный тезис;
- какие блоки нужны;
- какие данные визуализировать графиком;
- где нужна таблица;
- какие callouts вынести;
- какие источники показать сносками.

### Visual Data Designer

Готовит дизайн-бриф:

- формат;
- сетка;
- визуальная иерархия;
- палитра;
- графики;
- таблицы;
- бейджи;
- сноски;
- экспортные размеры.

### Browser Design Operator

Работает через браузерный дизайн-инструмент, например Claude design / Claude Artifacts-подобный интерфейс, HTML/CSS/SVG редактор или другой визуальный агент.

Система не должна считать такой инструмент жесткой зависимостью. Это внешний дизайн-слой, куда оператор или утвержденная браузерная автоматизация передает только подготовленный дизайн-бриф и sanitized data pack.

### QA & Citation Validator

Проверяет:

- каждое число имеет источник;
- диаграммы используют правильные единицы;
- дата среза видна;
- сноски соответствуют утверждениям;
- labels не накладываются;
- изображение читаемо в нужных размерах;
- нет выдуманных сравнений;
- спорные claims помечены как оценки или гипотезы.

## Предлагаемые сущности БД

### `infographic_projects`

- `id`
- `scope_type`: `product`, `price_group`, `brand`, `trend_event`, `content_opportunity`, `custom`
- `scope_id`
- `title`
- `infographic_type`
- `status`: `draft`, `collecting`, `data_ready`, `brief_ready`, `design_prompt_ready`, `design_ready`, `qa_failed`, `qa_passed`, `approved`, `exported`
- `created_by`
- `created_at`
- `updated_at`

### `infographic_data_packs`

- `id`
- `project_id`
- `data_pack_json`
- `source_count`
- `missing_fields_json`
- `confidence_score`
- `created_at`

### `infographic_design_briefs`

- `id`
- `project_id`
- `brief_markdown`
- `brief_json`
- `prompt_pack_json`
- `created_at`

### `infographic_assets`

- `id`
- `project_id`
- `asset_type`: `html`, `svg`, `png`, `webp`, `pdf`, `cms_block`, `social_crop`
- `storage_uri`
- `source_asset_text`
- `width`
- `height`
- `qa_status`
- `created_at`

### `infographic_reviews`

- `id`
- `project_id`
- `review_type`: `data`, `design`, `legal`, `marketing`, `final`
- `status`
- `notes`
- `created_at`

## API MVP

```text
POST /api/infographics/projects
GET  /api/infographics/projects
GET  /api/infographics/projects/{project_id}

POST /api/infographics/projects/{project_id}/collect-data
POST /api/infographics/projects/{project_id}/generate-data-pack
POST /api/infographics/projects/{project_id}/generate-brief
POST /api/infographics/projects/{project_id}/prepare-design-prompts

POST /api/infographics/projects/{project_id}/assets
POST /api/infographics/projects/{project_id}/qa
POST /api/infographics/projects/{project_id}/approve
POST /api/infographics/projects/{project_id}/export-package
```

## Формат `infographic_data_pack`

```json
{
  "schema_version": "1.0",
  "scope": {
    "type": "product",
    "id": "product-id",
    "title": "Product / group / brand name",
    "market": "Ukraine ecommerce",
    "snapshot_date": "2026-05-08"
  },
  "main_subject": {
    "name": "Product name",
    "brand": "Brand",
    "price": {
      "value": 0,
      "currency": "UAH",
      "source_id": "s1",
      "captured_at": "2026-05-08T00:00:00+03:00"
    },
    "specs": [
      {
        "name": "Spec name",
        "value": "Spec value",
        "source_id": "s2",
        "confidence": "high"
      }
    ]
  },
  "market_position": {
    "group_name": "Category",
    "price_min": 0,
    "price_median": 0,
    "price_avg": 0,
    "price_max": 0,
    "position_label": "mid-market",
    "relative_to_median_pct": 0,
    "rank_estimate": null,
    "notes": []
  },
  "competitors": [
    {
      "name": "Competitor product",
      "brand": "Brand",
      "price": 0,
      "currency": "UAH",
      "key_specs": {},
      "advantages": [],
      "tradeoffs": [],
      "source_ids": []
    }
  ],
  "buyer_scores": [
    {
      "scenario": "Best for budget buyers",
      "score": 0,
      "max_score": 10,
      "rationale": "Short cited rationale",
      "source_ids": []
    }
  ],
  "visualization_candidates": [
    {
      "type": "bar_chart",
      "title": "Price vs market median",
      "data_refs": ["market_position"],
      "unit": "UAH"
    }
  ],
  "claims": [
    {
      "claim": "Claim text",
      "claim_type": "fact",
      "source_ids": ["s1"],
      "confidence": "high"
    }
  ],
  "sources": [
    {
      "id": "s1",
      "title": "Source title",
      "url": "https://example.com",
      "publisher": "Publisher",
      "captured_at": "2026-05-08T00:00:00+03:00"
    }
  ],
  "missing_or_risky_data": [
    {
      "field": "warranty",
      "reason": "No reliable source found",
      "action": "manual_review"
    }
  ]
}
```

## Библиотека инфографических промптов

Промпты должны быть маленькими и проверяемыми. Нельзя делать один огромный промпт “собери данные и нарисуй красиво”, потому что так теряется контроль над источниками.

### Prompt 1: Scope Builder

Назначение: определить границы инфографики.

```text
Ты продуктовый аналитик ecommerce. Сформируй scope для инфографики.

Вход:
- объект: {product_or_group_or_brand}
- цель: {goal}
- аудитория: {audience}
- канал: {channel}
- доступные внутренние данные: {internal_data_summary}

Верни JSON:
{
  "scope_type": "product|price_group|brand|trend_event|content_opportunity|custom",
  "primary_question": "...",
  "infographic_type": "product_position|competitor_comparison|market_trend|buyer_guide|article_aeo",
  "required_data": [],
  "competitor_selection_rules": [],
  "visual_outputs": [],
  "risk_notes": []
}

Не придумывай факты. Если данных мало, укажи, какие поля нужно собрать.
```

### Prompt 2: Gemini Deep Research Brief

Назначение: получить исследовательскую базу для категории, товара или бренда.

```text
Ты исследователь рынка для ecommerce. Проведи grounded research по теме:
{scope_title}

Цель исследования:
{primary_question}

Нужно собрать:
1. ключевые критерии выбора в категории;
2. основные конкурирующие товары или бренды;
3. важные характеристики для сравнения;
4. типовые ценовые сегменты;
5. проверяемые факты для инфографики;
6. спорные утверждения, которые нельзя использовать без ручной проверки.

Требования:
- каждый факт сопровождай источником;
- отделяй факт от гипотезы;
- не выдумывай цены, характеристики, рейтинги и проценты;
- отмечай дату актуальности;
- если источник не дает точного значения, напиши "не подтверждено".

Верни:
- краткое резюме;
- таблицу фактов;
- список источников;
- список недостающих данных;
- рекомендации, какие блоки стоит визуализировать.
```

### Prompt 3: Source Corpus Extractor

Назначение: извлечь данные из уже собранных URL, сниппетов, браузерных скрапов или Tavily.

```text
Ты парсер источников для аналитической инфографики.

Входной корпус:
{source_corpus}

Извлеки только подтвержденные данные:
- цены;
- характеристики;
- наличие;
- гарантия;
- комплектация;
- преимущества;
- ограничения;
- сравнения;
- даты публикации или захвата.

Верни JSON:
{
  "facts": [
    {
      "subject": "...",
      "field": "...",
      "value": "...",
      "unit": null,
      "source_id": "...",
      "confidence": "high|medium|low",
      "notes": ""
    }
  ],
  "missing_fields": [],
  "conflicts": [],
  "source_quality_notes": []
}

Запрещено: объединять разные источники в одно значение без пометки, делать выводы без источника.
```

### Prompt 4: Data Pack Normalizer

Назначение: привести данные к строгой схеме `infographic_data_pack`.

```text
Ты нормализатор данных. Преобразуй исследовательский отчет и извлеченные факты в infographic_data_pack JSON.

Вход:
- scope: {scope_json}
- research_report: {research_report}
- extracted_facts: {facts_json}
- internal_product_data: {product_json}
- market_price_data: {market_json}

Правила:
- используй только подтвержденные данные;
- каждое число должно иметь source_id или ссылку на внутренний расчет;
- если значения конфликтуют, не выбирай победителя без правила, а добавь запись в missing_or_risky_data;
- отделяй claims типа "fact", "calculation", "hypothesis", "marketing_interpretation";
- не добавляй неподтвержденные рейтинги.

Верни только валидный JSON по схеме infographic_data_pack.
```

### Prompt 5: Market Analyst

Назначение: превратить data pack в аналитические выводы.

```text
Ты market analyst для ecommerce. На основе infographic_data_pack подготовь выводы для инфографики.

Посчитай и объясни:
- позицию товара в группе;
- отличие от медианы цены;
- ценовой сегмент;
- 3-5 преимуществ;
- 3-5 tradeoffs;
- кому товар подходит;
- когда выбрать конкурента;
- какие данные лучше показать графиком;
- какие данные лучше показать таблицей;
- какие claims требуют сносок.

Формат ответа:
{
  "headline_insight": "...",
  "supporting_insights": [],
  "recommended_visual_blocks": [],
  "chart_specs": [],
  "table_specs": [],
  "footnote_requirements": [],
  "do_not_claim": []
}

Не делай рекламных утверждений сильнее, чем позволяют данные.
```

### Prompt 6: Infographic Creative Strategy

Назначение: определить композицию и смысловой сценарий.

```text
Ты арт-директор и информационный дизайнер. На основе data pack и market analysis создай стратегию инфографики.

Вход:
- infographic_type: {type}
- channel: {cms_article|product_card|instagram|viber|youtube_community|pdf}
- dimensions: {width}x{height}
- data_pack: {data_pack}
- analyst_output: {analyst_output}

Сформируй:
- главный визуальный тезис;
- порядок блоков сверху вниз;
- какие блоки должны быть диаграммами;
- какие блоки должны быть таблицами;
- какие callouts нужны;
- какие сноски показать;
- какие элементы нельзя перегружать;
- рекомендации по цветовой логике.

Верни JSON и короткий Markdown-бриф.
```

### Prompt 7: Browser Design Agent Prompt

Назначение: передать внешнему браузерному дизайн-инструменту точное задание.

```text
Ты senior visual designer и frontend-oriented infographic designer.

Создай редактируемую инфографику на основе строго заданных данных. Не добавляй новые факты, числа, бренды, цены, проценты или источники.

Формат:
- итог: {html_css_svg_or_design_artifact}
- размер: {dimensions}
- канал: {channel}
- язык: {language}

Данные:
{infographic_data_pack}

Дизайн-бриф:
{design_brief}

Обязательные элементы:
- заголовок с главным выводом;
- визуальный блок позиции товара на рынке;
- сравнительная таблица или диаграмма конкурентов;
- 2-4 callout-блока;
- сноски с source ids;
- дата среза;
- блок "данные требуют проверки", если такие поля есть.

Стиль:
- современный ecommerce / consumer electronics;
- высокая читаемость;
- аккуратные таблицы и полосы сравнения;
- без декоративной перегрузки;
- не использовать фальшивые логотипы;
- не скрывать источники мелким нечитаемым текстом.

Технические требования:
- если это HTML/CSS, все стили в одном файле;
- если это SVG, текст должен быть редактируемым;
- все диаграммы должны иметь подписи, единицы и шкалу;
- никакие подписи не должны накладываться друг на друга;
- сноски должны совпадать с source ids из data pack.
```

### Prompt 8: Design QA

Назначение: проверить результат дизайна.

```text
Ты QA-редактор аналитической инфографики.

Проверь дизайн-результат:
{design_artifact}

Сравни с data pack:
{infographic_data_pack}

Проверь:
1. нет ли чисел или claims, которых нет в data pack;
2. у всех чисел есть источник, единица и дата среза;
3. диаграммы не искажают пропорции;
4. подписи читаемы;
5. сноски совпадают с source ids;
6. отсутствуют неподтвержденные логотипы, рейтинги и награды;
7. есть пометки для неполных данных;
8. дизайн подходит под канал и размер.

Верни:
{
  "qa_status": "pass|fail",
  "blocking_issues": [],
  "non_blocking_issues": [],
  "fix_prompt": "..."
}
```

### Prompt 9: Revision Prompt

Назначение: безопасно исправить дизайн после QA.

```text
Исправь инфографику только по списку QA issues.

QA issues:
{qa_issues}

Исходный дизайн:
{design_artifact}

Data pack:
{infographic_data_pack}

Правила:
- не меняй подтвержденные данные;
- не добавляй новые факты;
- исправь только указанные проблемы;
- сохрани source ids и дату среза;
- верни полный обновленный артефакт.
```

### Prompt 10: CMS / Social Export Prompt

Назначение: подготовить ассеты и подписи для публикации.

```text
Ты content operations editor. Подготовь экспорт инфографики для публикации.

Вход:
- approved design artifact: {asset}
- data pack: {infographic_data_pack}
- target channel: {channel}

Верни:
{
  "cms_title": "...",
  "cms_caption": "...",
  "alt_text": "...",
  "source_note": "...",
  "social_caption_variants": [],
  "viber_digest_text": "...",
  "schema_org_image_metadata": {},
  "publication_warnings": []
}

Не обещай больше, чем подтверждает инфографика.
```

## Browser design integration

Интеграция с Claude design / браузерным дизайн-инструментом должна быть сделана через безопасный адаптер:

1. Backend готовит `prompt_pack_json`.
2. Operator console показывает data pack и prompt для копирования.
3. На MVP оператор вручную вставляет prompt во внешний дизайн-инструмент.
4. В следующей фазе браузерная автоматизация может открыть утвержденную страницу, вставить prompt и получить артефакт.
5. Любой результат возвращается в систему как `infographic_asset` и проходит QA.

Ограничения:

- не отправлять API keys, внутренние токены, себестоимость, приватные поставщицкие условия;
- не отправлять персональные данные клиентов;
- не отправлять закрытые коммерческие расчеты, если инфографика предназначена для публичной публикации;
- не считать внешний дизайн-инструмент источником фактов;
- не публиковать результат без QA и approval.

## Правила качества данных

- Числа без источника не попадают в публичную инфографику.
- Цены всегда имеют валюту, дату среза и источник.
- Сравнения должны указывать критерий сравнения.
- Рейтинги и оценки должны иметь прозрачную формулу.
- Если формула экспертная, она помечается как internal scoring.
- Графики должны показывать шкалу и единицы.
- Сноски не должны быть декоративными: source id обязан вести к реальному источнику.
- Если данные неполные, это лучше показать честно, чем скрыть.

## Visual QA checklist

- Текст читается на мобильном размере.
- Таблица не превращается в мелкую сетку.
- Цвета не кодируют данные неоднозначно.
- Красный / зеленый используются только там, где смысл очевиден.
- Полосы сравнения имеют одинаковую шкалу.
- Лейблы не накладываются.
- Нет декоративных элементов, похожих на реальные данные.
- Источники и дата среза видны.
- У изображения есть alt text.

## MVP-этапы

### P0-039: Architecture and Prompt Library

- этот документ;
- skill `ecommerce-infographic-brief`;
- prompt library;
- data pack schema;
- API план.

### P0-040: Data Pack Backend

- модели `infographic_projects`, `infographic_data_packs`;
- API создания проекта;
- генерация mock data pack;
- связь с product / price group / content opportunity.

### P0-041: Design Brief Backend

- сервис генерации design brief;
- prompt pack JSON;
- хранение версий брифа;
- QA-заготовка.

### P0-042: Operator Console Tab

- вкладка `Infographics`;
- создание проекта;
- просмотр data pack;
- кнопка `Prepare design prompt`;
- ручной upload / paste результата дизайна.

### P0-043: Browser Design Adapter

- opt-in браузерный workflow;
- manual confirmation перед отправкой;
- сохранение HTML/SVG результата;
- QA.

### P0-044: Publishing Integration

- экспорт в publish package;
- CMS image block;
- social crops;
- Viber digest summary.

## Следующий практический шаг

Начать с `P0-040`: сделать backend-модели и API для `infographic_projects` и `infographic_data_packs`, чтобы мы могли создавать инфографический проект из товара, группы цен или темы статьи и получать первый mock/structured data pack без внешних API.
