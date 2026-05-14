# Обзор аналогов и архитектурные выводы

## 1. Цель анализа

Перед началом реализации нужно изучить аналоги, чтобы не повторить типовые ошибки:

- сделать слишком общий AI-конструктор вместо доменного продукта;
- потерять состояние long-running задач;
- не заложить human approval;
- смешать prompts, skills и бизнес-логику;
- не учитывать стоимость Deep Research и Veo;
- начать с видео до того, как готовы task engine, storage и approval;
- не иметь наблюдаемости и версионирования prompts.

Цель этого документа: зафиксировать, какие решения берем из аналогов, какие не берем, и какие архитектурные решения принять перед кодом.

## 2. Итоговый вывод

Лучший путь: **не копировать один готовый продукт**, а собрать свою архитектуру из проверенных паттернов.

Рекомендуемая позиция:

- ядро продукта делаем свое: FastAPI, PostgreSQL, task engine, adapters, agents, skills registry;
- Google-first стек оставляем главным: Deep Research, Gemini, Veo, Search Console, GA4, Merchant Center;
- из аналогов берем архитектурные паттерны;
- Dify/n8n используем как референсы UX и workflow, но не как основу продукта;
- LangGraph/Temporal используем как ориентир для durable execution;
- Langfuse используем как референс или будущую интеграцию для tracing/prompt/evals;
- Remotion рассматриваем как инструмент программной сборки видео поверх Veo-клипов;
- Agent Skills spec используем как формат для локальных skills.

## 3. Матрица аналогов

| Аналог | Категория | Что полезно | Что не подходит |
|-------|-----------|-------------|-----------------|
| Google Deep Research | research core | автономное исследование, планирование, отчеты с источниками, визуализации | preview-ограничения, нельзя использовать как обычный JSON generator |
| Gemini API Webhooks | event-driven | подписанные webhooks, at-least-once delivery, асинхронные batch/long jobs | нужна идемпотентность и обработка дублей |
| Veo 3.1 / Veo 3 | video generation | 9:16, 16:9, native audio, reference images, long-running operations | длинные ролики нужно собирать из сцен |
| Dify | LLM app platform | visual workflow, RAG, model providers, tools, Prompt IDE, LLMOps | слишком общий конструктор, доменный e-commerce слой все равно писать отдельно |
| n8n | workflow automation | webhooks, approvals, HITL tool review, 400+ integrations | no-code слой может усложнить кастомную Google-first платформу |
| LangGraph | stateful agents | durable execution, human-in-the-loop, checkpoints, resumable agents | добавит сложность, если подключить слишком рано |
| Temporal | durable workflows | надежные workflows, retries, timers, activities, recovery | тяжелее для MVP, нужен позже при масштабе |
| CrewAI | multi-agent framework | роли агентов, tasks, flows, crews, быстрый прототип агентной логики | автономные agents могут быть менее предсказуемы, чем наш explicit pipeline |
| Langfuse | LLMOps | tracing, prompt management, evals, datasets, cost/latency | можно подключить позже, сначала хватит своей таблицы логов |
| LlamaIndex | RAG/document framework | document ingestion, indexing, query over private data | Google File Search Store может закрыть часть задач в Google-first MVP |
| Haystack | production RAG/pipelines | явные RAG pipelines, routing, memory, deployable components | может быть избыточен рядом с Deep Research + File Search |
| Remotion | programmatic video | React video templates, captions, server-side rendering, data-driven video | лицензирование и Node stack; для MVP можно начать с ffmpeg |
| Agent Skills spec | skills format | `SKILL.md`, YAML frontmatter, scripts/references/assets, progressive disclosure | нужно адаптировать под нашу БД и agent bindings |
| marketingskills | marketing skills library | ai-seo, schema, programmatic-seo, copywriting, video, image | SaaS/marketing общий набор, нужны ecommerce custom skills |
| Microsoft Agent Framework A2A | enterprise agent interoperability | Agent Cards, discovery, HTTP agent communication, long-running tasks, streaming, cross-framework agents | избыточно для MVP, требует security/governance слоя |

## 4. Что берем из каждого аналога

### 4.1. Google Deep Research

Берем как центральный research engine.

Паттерны:

- research task запускается отдельно от writing task;
- Deep Research не пишет финальный контент напрямую;
- Deep Research создает report с источниками;
- Formatter Agent нормализует report в JSON;
- для сложных задач включается collaborative planning;
- дорогие исследования требуют approval плана;
- результат сохраняется в `research_reports`.

Архитектурное правило:

```text
Deep Research -> Research Report -> Formatter Agent -> Content/Strategy Agents
```

Не делать:

- не использовать Deep Research для простого rewrite;
- не ожидать от него строгий JSON как от обычной модели;
- не запускать Max без budget guard.

Источник: https://ai.google.dev/gemini-api/docs/deep-research

### 4.2. Gemini API Webhooks

Берем как паттерн событийной обработки.

Паттерны:

- webhook endpoint отвечает быстро;
- payload сохраняется в `webhook_events`;
- обработка идет через queue;
- `webhook-id` используется для deduplication;
- delivery считается at-least-once;
- каждый webhook связывается с `content_task` или `media_asset`;
- нельзя считать webhook уникальным событием без проверки idempotency.

Архитектурное правило:

```text
Webhook -> Verify -> Store -> Deduplicate -> Queue -> Continue Pipeline
```

Источник: https://ai.google.dev/gemini-api/docs/webhooks

### 4.3. Veo 3.1 / Veo 3

Берем как основной video generation engine.

Паттерны:

- каждый Veo-запрос создает short clip;
- длинное видео собирается из сцен;
- хранить `operation.name`;
- polling выполнять в worker;
- скачивать видео сразу после готовности;
- использовать `9:16` для shorts;
- использовать `16:9` для YouTube;
- использовать reference images для товаров;
- использовать first/last frame для контроля сцены.

Архитектурное правило:

```text
Marketing Brief -> Script -> Storyboard -> Scene Prompts -> Veo Clips -> ffmpeg/Remotion Assembly
```

Не делать:

- не запускать Veo без утвержденного video brief;
- не генерировать товарное видео как "реальное", если оно не основано на реальных фото/видео;
- не держать HTTP-запрос открытым до завершения operation.

Источник: https://ai.google.dev/gemini-api/docs/video

### 4.4. Dify

Берем как UX и LLMOps-референс.

Полезные идеи:

- visual workflow canvas;
- Prompt IDE;
- RAG pipeline;
- model providers abstraction;
- agent tools;
- observability;
- backend API для workflow.

Что переносим в наш продукт:

- workflow/status view для task;
- prompt registry;
- model adapter abstraction;
- logs per run;
- RAG/file ingestion later.

Почему не берем Dify как ядро:

- наш продукт не общий LLM app builder;
- нужна жесткая доменная модель: products, specs, competitors, publications, media assets;
- нужна глубокая интеграция Google Deep Research/Veo/Merchant Center;
- проще сделать узкий product pipeline, чем кастомизировать общий конструктор.

Источник: https://github.com/langgenius/dify

### 4.5. n8n

Берем HITL и webhook patterns.

Полезные идеи:

- approval перед рискованным tool call;
- разные approval channels: Telegram, email, chat;
- workflow pause/wait;
- webhook trigger;
- separate test/prod webhook URLs;
- reviewer видит tool name и parameters.

Что переносим:

- approval не только финального текста, но и tool actions;
- approve/deny/request changes;
- risky actions list;
- отдельная таблица approval requests;
- tool call preview перед публикацией, рассылкой, изменением цены, запуском Veo.

Риск:

- если подключить n8n как runtime, бизнес-логика расползется по no-code workflows;
- для MVP лучше реализовать approval внутри backend.

Источники:

- https://docs.n8n.io/advanced-ai/human-in-the-loop-tools/
- https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/

### 4.6. LangGraph

Берем durable execution principles.

Полезные идеи:

- checkpoint между шагами;
- resumable workflow;
- human-in-the-loop interrupt;
- long-running stateful agents;
- side effects должны быть wrapped as tasks;
- deterministic replay.

Что переносим:

- state machine;
- task events;
- idempotent steps;
- resume from last successful step;
- запрет повторного выполнения side effects без проверки.

Решение:

- MVP: своя простая state machine в PostgreSQL;
- позже: рассмотреть LangGraph или Temporal, если pipeline станет сложным.

Источник: https://github.com/langchain-ai/langgraph

### 4.7. Temporal

Берем как эталон надежности workflows.

Полезные идеи:

- workflows могут ждать дни/недели;
- activities имеют retries/timeouts;
- workflow state восстанавливается после сбоев;
- бизнес-логика пишется кодом, а не только конфигом.

Что переносим:

- каждый external API call как activity;
- timeout/retry policy;
- long waits не держат процесс;
- cron/scheduled workflows;
- recovery после падения worker.

Решение:

- MVP без Temporal;
- добавить ADR после первых стабильных pipelines;
- если появятся десятки long-running процессов с approval, Veo и CMS side effects, Temporal станет сильным кандидатом.

Источник: https://temporal.io/

### 4.8. CrewAI

Берем agent role/task vocabulary.

Полезные идеи:

- agents.yaml/tasks.yaml как читаемая конфигурация;
- разделение Crews и Flows;
- Flows для precise control;
- Crews для автономной исследовательской/аналитической работы;
- expected output для каждой task.

Что переносим:

- agent definitions в YAML/DB;
- task expected output;
- роли и цели агентов;
- agent + skill binding.

Риск:

- слишком автономные agents могут делать непредсказуемые шаги;
- для коммерческой публикации лучше explicit pipeline.

Решение:

- не делать CrewAI core dependency на MVP;
- использовать его как reference для agent/task config;
- возможно использовать для isolated research experiments.

Источник: https://github.com/crewAIInc/crewAI

### 4.9. Langfuse

Берем LLMOps-паттерн.

Полезные идеи:

- trace каждого LLM call;
- prompt management;
- prompt versioning;
- evals;
- datasets;
- cost/latency monitoring;
- playground для итераций.

Что переносим в MVP:

- таблица `llm_calls`;
- prompt version на каждом task;
- cost estimate;
- latency;
- input/output hash;
- quality score.

Решение:

- MVP: простая собственная observability в БД;
- Phase 2: подключить Langfuse self-hosted или cloud для трассировки и evals.

Источник: https://github.com/langfuse/langfuse

### 4.10. LlamaIndex и Haystack

Берем как reference для RAG и document pipelines.

Полезные идеи:

- document loaders;
- parsing PDF/CSV/manuals;
- structured extraction;
- retrieval pipelines;
- vendor-agnostic RAG;
- components with explicit routing.

Решение:

- MVP Google-first: File Search Store + PostgreSQL;
- если File Search Store не закрывает приватные документы, добавить LlamaIndex или Haystack;
- не подключать оба сразу.

Источники:

- https://github.com/run-llama/llama_index
- https://github.com/deepset-ai/haystack

### 4.11. Remotion

Берем как кандидат для video assembly layer.

Полезные идеи:

- видео как код;
- React components для intro/outro/lower thirds;
- data-driven rendering;
- captions;
- scalable server-side rendering;
- reusable templates.

Где применить:

- branded intro/outro;
- титры и lower thirds;
- шаблонные shorts;
- графики и сравнения в видео;
- автоматическая обложка.

Решение:

- MVP media: ffmpeg;
- Phase 2 video: оценить Remotion для шаблонов и динамических overlays;
- проверить лицензию перед коммерческим использованием.

Источник: https://github.com/remotion-dev/remotion

### 4.12. Agent Skills spec и marketingskills

Берем как формат skills.

Полезные идеи:

- skill как папка;
- обязательный `SKILL.md`;
- YAML frontmatter;
- `scripts/`;
- `references/`;
- `assets/`;
- progressive disclosure;
- validation.

Что переносим:

- `.agents/skills/{skill}/SKILL.md`;
- индекс skills в БД;
- agent_skill_bindings;
- skill lifecycle;
- related skills;
- quality gates.

Решение:

- использовать Agent Skills spec как формат файлов;
- использовать `Sevrikov/marketingskills` как внешнюю библиотеку;
- создать ecommerce-specific skills поверх нее.

Источники:

- https://agentskills.io/specification
- https://github.com/Sevrikov/marketingskills

### 4.13. Microsoft Agent Framework A2A

Берем как enterprise-ориентир для agent interoperability.

Что такое A2A:

- открытый Agent-to-Agent протокол для связи агентов через HTTP;
- agents могут находить друг друга через Agent Cards;
- agent card описывает имя, версию, endpoint, capabilities;
- поддерживаются разные protocol bindings, включая HTTP+JSON и JSON-RPC;
- поддерживаются streaming responses через Server-Sent Events;
- поддерживаются long-running tasks через continuation token;
- Microsoft Agent Framework может оборачивать A2A endpoint как стандартный `AIAgent`;
- A2A полезен, когда агенты живут в разных сервисах, командах, организациях, языках или фреймворках.

Почему это enterprise-уровень:

- дает стандартизированное общение между удаленными агентами;
- позволяет подключать внешних специализированных агентов без доступа к их коду;
- подходит для service boundaries и organizational boundaries;
- поддерживает discovery через `.well-known/agent-card.json` или enterprise registry;
- заставляет думать о versioning, auth, retries, timeouts, ownership и governance.

Что переносим в нашу архитектуру:

- добавить понятие `Agent Card` для каждого публичного/внутреннего агента;
- заложить возможность future endpoint `/a2a/{agent_name}`;
- описывать capabilities агентов явно;
- хранить agent version и ownership;
- отделять локальные agents-as-tools от remote agents-over-A2A;
- для external/partner agents использовать только через allowlist и approval.

Что не делаем в MVP:

- не реализуем полноценный A2A protocol;
- не выносим всех агентов в отдельные микросервисы;
- не подключаем неизвестные remote agents динамически;
- не даем external agents доступ к CMS, ценам, клиентским данным и публикации без отдельного security layer.

Рекомендуемый путь:

```text
MVP: local agents + skills registry
Phase 2: internal Agent Cards
Phase 3: A2A-compatible endpoints for selected agents
Enterprise: A2A registry + auth + policy engine + audit
```

Источники:

- https://learn.microsoft.com/en-us/agent-framework/journey/agent-to-agent
- https://learn.microsoft.com/en-us/agent-framework/agents/providers/agent-to-agent
- https://learn.microsoft.com/en-us/agent-framework/integrations/a2a

## 5. Архитектурные ошибки, которых избегаем

### Ошибка 1. Делать общий AI-конструктор

Плохой путь:

```text
Сделаем свой Dify/n8n для всего.
```

Правильный путь:

```text
Делаем доменный продукт для e-commerce content/research/media.
```

### Ошибка 2. Пускать AI напрямую в CMS

Плохой путь:

```text
AI сгенерировал -> сразу опубликовал.
```

Правильный путь:

```text
AI сгенерировал -> quality gates -> approval -> publish.
```

### Ошибка 3. Не хранить промежуточные результаты

Плохой путь:

```text
Один script запустился, упал, все потеряно.
```

Правильный путь:

```text
Каждый step сохраняет state, output, cost, errors.
```

### Ошибка 4. Смешивать prompts и код

Плохой путь:

```text
Prompts зашиты в Python functions.
```

Правильный путь:

```text
Prompt registry + skill registry + versioning.
```

### Ошибка 5. Начинать с Veo

Плохой путь:

```text
Сначала делаем видео, потом разберемся с системой.
```

Правильный путь:

```text
Сначала approval/storage/task engine, потом Veo.
```

### Ошибка 6. Игнорировать at-least-once webhooks

Плохой путь:

```text
Webhook пришел один раз и точно уникальный.
```

Правильный путь:

```text
Webhook может повториться. Нужны webhook_id, dedupe, idempotency.
```

### Ошибка 7. Считать Deep Research обычной LLM

Плохой путь:

```text
Попросим Deep Research вернуть строгий финальный JSON и сразу публикуем.
```

Правильный путь:

```text
Deep Research создает report. Formatter Agent нормализует. Validator проверяет.
```

### Ошибка 8. Подключать A2A без governance

Плохой путь:

```text
Любой remote agent может подключиться и выполнять действия.
```

Правильный путь:

```text
A2A только через registry, auth, allowlist, scoped permissions, audit и approval для risky actions.
```

## 6. Рекомендуемые ADR-решения

### ADR-001. Core architecture

Решение:

Делаем собственный backend и task engine, а не строим продукт поверх Dify/n8n.

Причина:

Нужна доменная модель e-commerce, Google-first интеграции и медиа pipeline.

### ADR-002. Workflow engine

Решение:

MVP: PostgreSQL state machine + Redis worker.

Phase 2: рассмотреть Temporal или LangGraph для durable workflows.

Причина:

Слишком раннее внедрение Temporal/LangGraph замедлит MVP, но их паттерны нужны в модели.

### ADR-003. Human approval

Решение:

Approval является обязательным для risky actions:

- публикация;
- изменение цены;
- email-рассылка;
- запуск дорогого Veo;
- публикация видео;
- массовое обновление карточек.

### ADR-004. Prompt/Skill management

Решение:

Prompts и skills не зашиваются в код.

Используем:

- `prompt_templates`;
- `skill_registry`;
- `.agents/skills`;
- `agent_skill_bindings`.

### ADR-005. Observability

Решение:

MVP: собственные таблицы logs/llm_calls/cost_events.

Phase 2: подключить Langfuse.

### ADR-006. Video stack

Решение:

MVP: video brief + storyboard без обязательной генерации.

Phase 2:

- Veo для клипов;
- ffmpeg для сборки;
- Remotion рассмотреть для branded templates, captions, overlays.

### ADR-007. RAG

Решение:

MVP: Google File Search Store или PostgreSQL storage.

Phase 2: LlamaIndex/Haystack только если появится реальная потребность в сложном приватном RAG.

### ADR-008. A2A enterprise interoperability

Решение:

MVP не реализует полноценный A2A protocol, но архитектура должна быть A2A-ready.

Что заложить сразу:

- `agents` или `agent_registry` table;
- agent name/version/owner/capabilities;
- public/private flag;
- allowed tools;
- risky action policy;
- audit log;
- возможность позже сгенерировать Agent Card.

Когда внедрять A2A:

- когда появятся отдельные сервисные агенты;
- когда нужно подключать внешние agents;
- когда разные команды будут владеть разными agents;
- когда потребуется enterprise marketplace/catalog агентов.

Причина:

A2A дает интероперабельность, но приносит сетевые сбои, latency, auth, versioning, ownership и security risks. Для MVP это overhead, для enterprise-фазы — правильная цель.

## 7. Что добавить в текущий план работ

Добавить перед Sprint 0:

### Sprint -1. Architecture Validation

Длительность: 1-2 дня.

Задачи:

- зафиксировать ADR-001 ... ADR-007;
- выбрать Redis worker: RQ или Celery;
- выбрать первую CMS или publish package fallback;
- определить, используем ли Langfuse сразу или позже;
- определить формат skill folders;
- определить minimum Google API credentials;
- проверить доступность Deep Research и Veo в аккаунте/регионе;
- определить лимиты бюджета.

Выход:

- разработка начинается без архитектурных развилок.

## 8. Практический итог

Наша архитектура после анализа аналогов остается правильной, но нужно усилить 5 вещей:

1. **Сделать state machine и idempotency первыми.**
2. **Сделать skills registry не позже prompt registry.**
3. **Ввести approval на tool calls, не только на финальный текст.**
4. **Сразу логировать cost/latency/model/prompt version.**
5. **Veo запускать только после video brief approval и готового media storage.**
6. **A2A заложить как future enterprise boundary, но не внедрять в MVP runtime.**

Если эти правила соблюсти, мы не повторим основные ошибки AI workflow продуктов: хаотичные prompts, потеря состояния, дорогие бесконтрольные вызовы, публикация без проверки и невозможность понять, почему агент сделал именно так.

## 9. Источники

- Google Gemini Deep Research Agent: https://ai.google.dev/gemini-api/docs/deep-research
- Google Gemini API Webhooks: https://ai.google.dev/gemini-api/docs/webhooks
- Google Veo video generation: https://ai.google.dev/gemini-api/docs/video
- Dify: https://github.com/langgenius/dify
- n8n Human-in-the-loop tools: https://docs.n8n.io/advanced-ai/human-in-the-loop-tools/
- n8n Webhook node: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/
- LangGraph: https://github.com/langchain-ai/langgraph
- LangGraph durable execution: https://docs.langchain.com/oss/python/langgraph/durable-execution
- Temporal: https://temporal.io/
- CrewAI: https://github.com/crewAIInc/crewAI
- Langfuse: https://github.com/langfuse/langfuse
- LlamaIndex: https://github.com/run-llama/llama_index
- Haystack: https://github.com/deepset-ai/haystack
- Remotion: https://github.com/remotion-dev/remotion
- Agent Skills specification: https://agentskills.io/specification
- Marketing skills fork: https://github.com/Sevrikov/marketingskills
- Microsoft Agent Framework A2A journey: https://learn.microsoft.com/en-us/agent-framework/journey/agent-to-agent
- Microsoft A2A Agent provider: https://learn.microsoft.com/en-us/agent-framework/agents/providers/agent-to-agent
- Microsoft A2A integration: https://learn.microsoft.com/en-us/agent-framework/integrations/a2a
