# Customer Pain Research Layer

## Цель

Добавить обязательный исследовательский слой, который перед любым материалом выясняет, какую реальную боль, задачу или риск закрывает товар. Особенно это важно для топ-товаров: если боль удалось подтвердить, она должна пройти через все материалы:

- описание товара;
- SEO/AEO статью;
- статическую инфографику;
- видео;
- Shorts / Reels / TikTok;
- видео-инфографику;
- Viber-дайджест;
- CMS/publish package.

Главный принцип: мы продаем не набор характеристик, а понятное решение конкретной ситуации покупателя. Характеристики должны быть связаны с болью, сценарием и доказательством.

## Место в пайплайне

```text
Product / Group / Brand / Trend
-> Customer Pain Deep Research
-> pain_profile
-> Product/Market/Infographic Data Pack
-> Content / Article / Infographic / Video / Shorts
-> QA: pain claim vs source evidence
-> Approval
```

`pain_profile` должен появляться до генерации текста, инфографики или видео. Если боль не подтверждена, материалы не должны агрессивно строиться вокруг нее.

## Что исследует модуль

### Buyer pain

Что покупатель пытается решить:

- неудобство;
- потеря времени;
- риск ошибки;
- нехватка качества;
- неуверенность в выборе;
- страх переплатить;
- несовместимость;
- слабая надежность;
- сложность настройки;
- нехватка автономности, скорости, точности или контроля.

### Context of use

Где и когда боль возникает:

- дом;
- офис;
- дорога;
- путешествие;
- ремонт;
- учеба;
- gaming;
- работа с клиентами;
- экстренная ситуация;
- сезонный спрос.

### Trigger event

Что запускает покупку:

- старое устройство сломалось;
- появился новый сценарий;
- цена изменилась;
- конкурентный товар стал дороже;
- нужен подарок;
- бизнесу нужно обновить парк;
- нужно быстро решить проблему.

### Alternatives

С чем покупатель сравнивает:

- дешевый аналог;
- старое устройство;
- другой бренд;
- DIY-решение;
- сервис вместо товара;
- отложить покупку.

### Proof mapping

Какие характеристики реально доказывают, что товар закрывает боль:

- емкость, мощность, скорость, дальность, яркость, автономность;
- комплектация;
- гарантия;
- совместимость;
- наличие;
- цена против группы;
- отзывы или внешние источники, если они доступны и разрешены.

## Схема `pain_profile`

```json
{
  "schema_version": "1.0",
  "scope": {
    "type": "product",
    "id": "product-id",
    "title": "Product title",
    "category": "Category",
    "snapshot_date": "2026-05-08"
  },
  "primary_pain": {
    "summary": "Short confirmed pain statement",
    "buyer_words": ["phrases buyers might use"],
    "severity": "low|medium|high|critical",
    "confidence": "high|medium|low",
    "source_ids": []
  },
  "secondary_pains": [
    {
      "summary": "...",
      "buyer_words": [],
      "confidence": "medium",
      "source_ids": []
    }
  ],
  "use_contexts": [
    {
      "context": "Travel / home / office",
      "pain_expression": "What goes wrong without the product",
      "product_relevance": "How the product helps",
      "source_ids": []
    }
  ],
  "trigger_events": [
    {
      "event": "What starts the purchase",
      "message_angle": "How to address it",
      "source_ids": []
    }
  ],
  "proof_map": [
    {
      "pain": "Pain summary",
      "product_feature": "Confirmed feature/spec",
      "proof_type": "spec|price|comparison|availability|review|expert_source|internal_calculation",
      "evidence": "Short evidence",
      "source_ids": []
    }
  ],
  "objections": [
    {
      "objection": "Why buyer may hesitate",
      "response": "Evidence-backed response",
      "source_ids": []
    }
  ],
  "content_guidance": {
    "description_angle": "How product description should use the pain",
    "article_angle": "How article should frame the problem",
    "infographic_angle": "What to visualize",
    "video_hook": "Best video/Shorts hook",
    "viber_alert_angle": "Short digest angle"
  },
  "do_not_claim": [
    "Unsupported pain or result claims"
  ],
  "sources": [
    {
      "id": "s1",
      "title": "Source title",
      "url": "https://example.com",
      "captured_at": "2026-05-08T00:00:00+03:00"
    }
  ],
  "missing_or_risky_data": [
    {
      "field": "proof for main pain",
      "reason": "No reliable source found",
      "action": "manual_review"
    }
  ]
}
```

## Prompt Library

### Prompt 1: Pain Scope Builder

```text
Ты product marketing researcher. Определи, какую боль может закрывать товар или группа товаров.

Вход:
- product/group/brand: {subject}
- category: {category}
- known specs: {specs}
- known price/market data: {market_data}
- target channel: {channel}

Верни JSON:
{
  "research_question": "...",
  "likely_pains_to_verify": [],
  "buyer_segments": [],
  "use_contexts_to_check": [],
  "competitors_or_alternatives": [],
  "proof_needed": [],
  "risk_notes": []
}

Не утверждай боль как факт. Только сформируй гипотезы для проверки.
```

### Prompt 2: Deep Pain Research

```text
Ты исследователь покупательских проблем для ecommerce.

Тема:
{subject}

Нужно выяснить:
1. какую практическую боль закрывает товар или группа;
2. как покупатели формулируют эту боль своими словами;
3. в каких ситуациях боль возникает;
4. что запускает покупку;
5. с какими альтернативами сравнивают;
6. какие характеристики товара реально доказывают решение;
7. какие claims нельзя делать без дополнительного подтверждения.

Требования:
- каждый подтвержденный факт со ссылкой на источник;
- отделяй факт от гипотезы;
- не выдумывай отзывы, рейтинги, проценты, экономию времени или деньги;
- если боль не подтверждена, так и напиши;
- укажи missing data.

Верни:
- research summary;
- pain table;
- proof map;
- objections;
- content guidance for product description, article, infographic, video, Shorts and Viber.
```

### Prompt 3: Pain Profile Normalizer

```text
Ты нормализатор customer pain research.

Вход:
- deep research report: {research_report}
- product data: {product_data}
- market data: {market_data}
- source corpus: {source_corpus}

Создай strict JSON по схеме pain_profile.

Правила:
- primary_pain только если он подтвержден источниками или надежной внутренней логикой;
- каждая связь "боль -> характеристика -> доказательство" должна иметь source_ids;
- если есть только гипотеза, помести ее в missing_or_risky_data или secondary_pains с confidence=low;
- не добавляй сильные обещания результата.

Верни только валидный JSON.
```

### Prompt 4: Material Injection Planner

```text
Ты контент-стратег. На основе pain_profile определи, как встроить боль во все материалы.

Вход:
- pain_profile: {pain_profile}
- material_type: {product_description|seo_article|infographic|video|shorts|video_infographic|viber_digest|cms_package}
- data_pack: {data_pack}

Верни:
{
  "main_pain_angle": "...",
  "where_to_place": [],
  "phrases_to_use": [],
  "visual_cues": [],
  "proof_points_to_show": [],
  "objections_to_answer": [],
  "do_not_claim": []
}

Правило: pain angle должен быть заметен, но не манипулятивен.
```

### Prompt 5: Pain QA

```text
Ты QA-редактор. Проверь материал против pain_profile.

Материал:
{material}

Pain profile:
{pain_profile}

Проверь:
1. боль упомянута, если она подтверждена;
2. боль не преувеличена;
3. есть связь "боль -> характеристика -> доказательство";
4. нет claims, которые запрещены в do_not_claim;
5. визуалы и заголовки не обещают неподтвержденный результат;
6. objections обработаны честно.

Верни:
{
  "qa_status": "pass|fail",
  "missing_pain_integration": [],
  "overclaims": [],
  "proof_gaps": [],
  "fix_prompt": "..."
}
```

## Как боль должна проявляться в материалах

### Описание товара

- В коротком ответе: какую задачу решает.
- В benefits: не просто преимущества, а "почему это полезно в ситуации X".
- В limitations: честно указать, где товар не закрывает боль.
- В FAQ: вопросы покупателя из `buyer_words`.

### Статья

- Открывать статью проблемой, а не товаром.
- Объяснять контекст боли и ошибки выбора.
- Сравнивать альтернативы.
- Подводить к товару как к одному из решений, а не единственному чуду.

### Инфографика

- Показывать боль как первый или второй блок.
- Визуализировать proof map: pain -> feature -> evidence.
- Добавлять objections/callouts.
- Не превращать боль в эмоциональный scare tactic.

### Видео и Shorts

- Hook строится вокруг покупательского вопроса или боли.
- В первых 3-5 секундах должно быть ясно, почему зрителю это касается.
- Цифры, цены и источники лучше выносить в overlay/subtitles.
- Voiceover должен говорить только подтвержденные pain claims.

### Viber

- Уведомление должно быть коротким:
  - что изменилось;
  - какая боль/сценарий затронут;
  - почему это значимо;
  - что сделать оператору.

## MVP-этапы

### P0-043: Pain Research Architecture

- этот документ;
- skill `ecommerce-customer-pain-research`;
- обновление content/video/infographic skills;
- усиление seed prompts и research query.

### P0-044: Pain Profile Backend

- `pain_profiles` table;
- API генерации профиля по product/group/brand;
- mock profile generation;
- связь с content tasks, infographics and media briefs.

### P0-045: Pain Injection Across Materials

- pain profile injection into draft variables;
- media brief JSON;
- infographic data pack;
- video storyboard;
- QA gates.

## Следующий практический шаг

После текущего архитектурного слоя реализовать backend-модель `pain_profiles` и endpoint:

```text
POST /api/pain-profiles/generate
GET  /api/pain-profiles
GET  /api/pain-profiles/{profile_id}
POST /api/pain-profiles/{profile_id}/approve
```

Затем каждый новый content task, infographic project и video infographic project должен пытаться найти утвержденный `pain_profile` для своего товара, группы или бренда и использовать его как обязательный вход.
