# Functional Inventory & Mock Test Plan

## Цель

Зафиксировать полный перечень функций продукта и тестовый режим, в котором все внешние API заменены mock-адаптерами. Этот режим должен регулярно прогоняться до тех пор, пока основные функции не работают стабильно.

## Главные функции продукта

### 1. Product Core

- создать товар;
- получить товар;
- обновить товар;
- хранить бренд, модель, категорию, SKU/GTIN/MPN, цену, валюту, наличие, исходное описание.

Mock status: полностью локально, внешние API не нужны.

### 2. Prompt & Skill Registry

- загрузить seed prompts;
- синхронизировать локальные `.agents/skills`;
- получить список skills;
- получить active prompt по ключу;
- использовать skills как контекст для генерации.

Mock status: полностью локально.

### 3. Customer Pain Research

- исследовать боль покупателя;
- сформировать `pain_profile`;
- связать боль с proof map;
- передать pain angle в описание, статью, инфографику, видео и Viber.

Current status: архитектура, skill, seed prompt, research query integration.

Next backend step: `pain_profiles` table/API.

### 4. Content Task Pipeline

- создать задачу;
- перевести в очередь;
- выполнить research;
- сгенерировать initial draft;
- выполнить critic;
- выполнить rewrite;
- перевести в `waiting_approval`;
- показать drafts, research, events.

Mock replacements:

- LLM -> `MockLLMAdapter`;
- Research -> `MockResearchAdapter`;
- Source corpus -> `MockSourceProvider`.

### 5. Approval

- отправить задачу на approval;
- mock notification;
- approve;
- request rewrite;
- Viber webhook command simulation.

Mock replacements:

- Viber -> `MockNotificationAdapter`.

### 6. Product Content Profiles

- сгенерировать структурную карточку товара;
- обновить поля;
- approve profile;
- встроить approved product card в CMS payload.

Mock status: полностью локально.

### 7. Publish Package

- экспортировать approved content;
- собрать markdown;
- собрать structured package JSON;
- сохранить workflow lineage.

Mock status: полностью локально.

### 8. CMS Preview & Publish Safety Gate

- подготовить CMS payload;
- показать dry-run preview;
- заблокировать real publish по умолчанию;
- требовать точную confirmation phrase;
- publish только через safety gate.

Mock replacements:

- CMS -> `MockCMSAdapter`.

### 9. Media Briefs

- собрать long video brief;
- собрать vertical short brief;
- собрать Veo prompt pack;
- добавить pain profile section;
- запретить real video generation по умолчанию.

Mock replacements:

- Video provider -> no-op / prompt pack only.

### 10. Content Opportunities

- найти темы статей по товару;
- найти темы по группе цен;
- найти темы по бренду/категории;
- создать content task из opportunity.

Mock replacements:

- Source provider -> `MockSourceProvider`;
- Research -> `MockResearchAdapter`.

### 11. Price Monitoring

- создать группу цен;
- создать monitored source;
- снять price snapshot;
- зафиксировать price change;
- построить market index;
- выявить массовое повышение/снижение;
- хранить trend events.

Mock replacements:

- Price extraction -> `MockPriceMonitorAdapter`.

### 12. Market Notifications

- создать notification policy;
- оценить trend events;
- queued digest;
- immediate alert;
- отправить digest batch;
- отметить events как отправленные.

Mock replacements:

- Notifications -> `MockNotificationAdapter`.

### 13. Scheduler

- список jobs;
- создать/обновить job;
- run-now;
- run-due;
- история runs.

Mock status: выполняет локальные jobs без внешних API.

### 14. Static Infographics

- customer pain research;
- infographic data pack;
- design brief;
- browser design prompt;
- QA prompt.

Current status: архитектура/skill.

Next backend step: `infographic_projects`, `infographic_data_packs`.

### 15. Video Infographics

- video data summary;
- hooks;
- script brief;
- storyboard JSON;
- Veo/Seedance provider prompt packs;
- assembly plan;
- video QA.

Current status: архитектура/skill.

Next backend step: `video_infographic_projects`, `video_infographic_storyboards`.

## Mock mode configuration

```text
LLM_PROVIDER=mock
RESEARCH_PROVIDER=mock
SOURCE_PROVIDER=mock
NOTIFICATION_PROVIDER=mock
CMS_PROVIDER=mock
PRICE_MONITOR_PROVIDER=mock
ENABLE_REAL_PUBLISHING=false
ENABLE_REAL_VIDEO_GENERATION=false
ENABLE_GOOGLE_SMOKE_TESTS=false
```

## Stability Gates

Перед любым реальным API-тестом должны проходить:

1. `ruff check`;
2. backend tests;
3. broad mock functional smoke;
4. frontend syntax check;
5. secret scan.

Команда:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test-local-mock-suite.ps1
```

## Что покрывает broad mock smoke

Тест `backend/tests/test_mock_functional_smoke.py` проходит один полный happy path:

- health;
- prompts;
- skills;
- product create;
- product content profile generate/approve;
- content opportunities;
- task creation from opportunity;
- worker draft pipeline;
- drafts/research;
- mock approval notification;
- approval;
- publish package;
- CMS preview;
- real publish blocked by default;
- media brief with pain profile;
- price group;
- market indexes;
- trend detection;
- notification policy;
- digest batch;
- scheduler jobs and run-due.

## Что пока не покрывается broad smoke

- реальные Gemini/Tavily/Viber/CMS/Veo вызовы;
- browser Playwright price extraction;
- будущие pain profile API;
- будущие infographic API;
- будущие video infographic API;
- визуальные проверки frontend через браузер.

Эти пункты добавляются в smoke после реализации соответствующих backend/API модулей.

## Secondary realistic scenarios

Кроме broad mock smoke нужны реалистичные сценарии на конкретных товарах. Они не должны каждый раз ходить во внешний магазин: страница может быть недоступна, измениться или заблокировать запрос. Поэтому данные страницы фиксируются как fixture, а pipeline гоняется локально в mock mode.

### ALTEK ALT-63 portable solar panel

Source URL:

```text
https://elektronom.com.ua/ua/p1859660505-portativnaya-solnechnaya-batareya.html
```

Зафиксированные данные:

- title: `Портативна сонячна батарея 63W чорний`;
- brand: `ALTEK`;
- model/mpn: `ALT-63`;
- price: `4200.00 UAH`;
- category: `Мобільні сонячні зарядки`;
- source product id: `PROM-1859660505`;
- key specs: 63W, MPPT controller, USB 5V/2.4A, USB-C 5V/3A, DC 19V/3A;
- dimensions: 865x700x5 mm unfolded, 290x175x65 mm folded;
- weight: 1.65 kg;
- pain angle: autonomous charging for travel, field conditions and weak-grid scenarios;
- safety notes: direct sunlight required, do not leave under rain, do not charge lithium batteries from clamps.

Команда:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test-realistic-product-card.ps1
```

Покрытие:

- product create from realistic fixture;
- product content profile generate/approve;
- product-card task;
- mock research with customer-pain query;
- initial/critic/final drafts;
- approval;
- publish package;
- CMS preview with approved product card JSON;
- media brief with disabled real video generation.

### Elektronom mobile solar chargers category

Source URL:

```text
https://elektronom.com.ua/ua/g117987855-mobilnye-solnechnye-zaryadki
```

Зафиксированные карточки из JSON-LD категории:

- ALTEK ALT-28 khaki, 28W, `2200.00 UAH`;
- ALF-70W flexible solar module, 70W, `2600.00 UAH`;
- ALTEK ALT-28 black, 28W, `2100.00 UAH`;
- Kraft TPB-SLP5F, 7.5W, `970.00 UAH`;
- ALTEK ALT-14, 14W, `1200.00 UAH`;
- ALTEK ALT-36, 36W, `3600.00 UAH`;
- Kraft KFP-100SP, 100W, `4950.00 UAH`;
- ALTEK ALT-63 black, 63W, `4200.00 UAH`.

Команда:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test-realistic-solar-category.ps1
```

Покрытие:

- создание нескольких товаров из одной категории;
- генерация product content profiles для каждого товара;
- построение price group;
- создание monitored sources;
- расчет market index по группе;
- проверка min/max/avg/median/top average;
- discovery article opportunities по группе.

### Solar category article flow

Команда:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\test-realistic-solar-article.ps1
```

Покрытие:

- создание группы товаров из captured category fixtures;
- расчет market index как контекст статьи;
- discovery content opportunities по группе;
- создание SEO article task из opportunity;
- mock deep research с customer-pain query;
- initial/critic/final drafts;
- approval;
- publish package;
- CMS Article preview;
- media brief для статьи без real video generation.

## Режим стабильности

До подключения новых внешних ключей действуем так:

1. Любая новая функция сначала получает mock adapter или no-op safety mode.
2. Добавляется unit/API test.
3. Добавляется или расширяется broad mock smoke.
4. Проходит `test-local-mock-suite.ps1`.
5. Только после этого включается реальный provider за отдельным флагом.

## Критерий "основные функции работают стабильно"

Минимальный критерий для текущей стадии:

- `test-local-mock-suite.ps1` проходит 5 раз подряд без изменений кода;
- локальный UI может создать task, показать drafts/research/events и approval actions;
- market tab показывает groups/trends/digests;
- media brief создается без real video;
- publication preview создается без real publish;
- secret scan clean.
