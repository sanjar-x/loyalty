---
tags:
  - project/loyality
  - backend
  - logistics
  - dobropost
  - moc
type: moc
date: 2026-04-30
aliases: [DobroPost Shipment API, ДоброПост MoC]
status: active
project: "[[Loyality Project]]"
component: backend
---

# DobroPost Shipment API — MoC

> Документация интеграции ДоброПост в Loyality cross-border-dropship flow. Папка разделена на 4 markdown'а + 1 машиночитаемый `openapi.json`. Каждый файл имеет одну, четко очерченную ответственность — это позволяет обновлять контракт ДоброПост (`reference.md` / `openapi.json`) **без затрагивания** Loyality-specific решений (`integration.md` / `webhooks.md` / `status-codes.md`).

## Контекст

ДоброПост — российский партнёр для **cross-border сегмента** (Китай → таможня → склад в РФ). В Loyality он покрывает **первый из двух обязательных Shipment'ов** на Order: cross-border (DobroPost) + last-mile (CDEK / Yandex Delivery). Last-mile shipment создаётся автоматически на webhook'е `status_id ∈ {648, 649}`, не на checkout'е.

Customer на странице tracking'а видит **3 трек-номера**: китайский (`incomingDeclaration`), ДоброПост (`dptrackNumber`), последняя миля.

```text
Order ─┬─ Shipment #1 (provider=dobropost)  — Китай → склад ДоброПост в РФ
       └─ Shipment #2 (provider=cdek|yandex) — склад ДоброПост → ПВЗ → customer
                       создаётся на webhook'е 648/649, не на checkout'е
```

## Структура папки

| Файл                                | Тип       | Что внутри                                                                            | Когда читать                                |
| ----------------------------------- | --------- | ------------------------------------------------------------------------------------- | ------------------------------------------- |
| [`reference.md`](./reference.md)    | reference | Дословный перевод PDF ДоброПост в Markdown. Endpoints, поля, payload'ы, http-codes.   | Нужен ответ «что отдаёт ДоброПост» — first stop. |
| [`openapi.json`](./openapi.json)    | reference | OpenAPI 3.0-spec для генерации клиентов (Swagger Editor, Stoplight, Postman).         | Нужен codegen, импорт в API-клиент.         |
| [`status-codes.md`](./status-codes.md) | reference | 40 status_id ДоброПост + маппинг на `TrackingStatus` Loyality + поведение FSM.        | Парсите webhook / фильтруете `?statusId=`.  |
| [`webhooks.md`](./webhooks.md)      | spec      | Loyality-side контракт: signature, idempotency, два формата payload, retry, outbox.   | Реализуете `DobroPostWebhookAdapter`.       |
| [`integration.md`](./integration.md) | spec     | Loyality cross-border flow: FSM Order, 1:2 ratio, manager actions, edge-cases, sequence. | Дизайните Order module, manager UX, RMA.    |

## Reading order

**Если вы новенький** в проекте и хотите понять интеграцию:

1. [`integration.md`](./integration.md) — TL;DR + sequence diagram, чтобы увидеть big picture.
2. [`reference.md`](./reference.md) — какой контракт у ДоброПост.
3. [`status-codes.md`](./status-codes.md) — что значат коды статусов.
4. [`webhooks.md`](./webhooks.md) — как Loyality обрабатывает входящие webhook'и.

**Если вы реализуете адаптер** (provider factory + clients):

1. [`reference.md`](./reference.md) §1–5 — endpoints для booking + tracking poll.
2. [`webhooks.md`](./webhooks.md) — для `IWebhookAdapter`.
3. [`status-codes.md`](./status-codes.md) — для маппинга в `TrackingStatus`.
4. [`integration.md` §DI registration](./integration.md#di-registration-tbd) — как вписать в `_FACTORY_MAP`.
5. Образец — `src/modules/logistics/infrastructure/providers/cdek/` (полная реализация).

**Если вы дизайните Order module** (Q3 2026):

1. [`integration.md` §FSM Order](./integration.md#fsm-order-cross-border--dropship) — 7 статусов + переходы.
2. [`integration.md` §Manager actions](./integration.md#manager-actions--admin-панель) — admin endpoints + side effects.
3. [`integration.md` §Edge cases](./integration.md#edge-cases) — 7 сценариев.
4. [[Research - Order (2) State Machine FSM]] §15 — детальный FSM в vault.

## Архитектурные инварианты (фиксируем здесь, не дублируем в других файлах)

1. **`Order : Shipment = 1 : 2` минимум, всегда.** ДоброПост — никогда не единственный shipment.
2. **Shipment #2 создаётся на event'е `CrossBorderArrived`** (status_id 648/649), не на checkout'е.
3. **ДоброПост не участвует в customer-facing rate calc / pickup-point fan-out.** Только admin-managed booking + tracking ingest.
4. **Webhook идемпотентен на трёх уровнях**: DB unique constraint → domain `TrackingAppendOutcome` → router swallow всех ошибок (см. [`webhooks.md` §Идемпотентность](./webhooks.md#идемпотентность-критично)).
5. **Customer видит 3 трек-номера** в email/UI: `incomingDeclaration`, `dptrackNumber`, last-mile `tracking_number`.
6. **`PUT /api/shipment` нужен только** для исправления паспортных данных при `passportValidationStatus=false` — не для других мутаций.
7. **`DELETE /api/shipment/{id}` НЕ используется** в production flow; cancellation идёт через локальный Order `CANCELLED + REFUND`.

## Текущий статус реализации

Provider-стек ДоброПост — **реализован** (2026-04-30):

- ✅ `Shipment` aggregate + factory `create_admin_managed` (`domain/entities.py`).
- ✅ `Shipment.cross_border_arrived_at` (миграция `30_0150_32_a27095efe3bc`).
- ✅ `CrossBorderArrivedEvent` + `ShipmentPassportValidationFailedEvent`.
- ✅ `DobroPostProviderFactory` + `DobroPostBookingProvider` + `DobroPostTrackingPollProvider` + `DobroPostWebhookAdapter`.
- ✅ Зарегистрирован в `_FACTORY_MAP` (`infrastructure/bootstrap.py`).
- ✅ Admin command `CreateCrossBorderShipmentHandler` (procurement flow).
- ✅ `HandleDobroPostPassportValidationHandler` для passport-validation failure path.
- ✅ Provider-input validator (`provider_validators.py`) — отвергает создание DobroPost-аккаунта без webhook auth.
- ✅ Partial index `ix_shipments_stuck_cross_border` для nightly job.
- ⏳ Order-side consumer для `CrossBorderArrivedEvent` (создание Shipment #2) — Order module Q3 2026.
- ⏳ Order-side consumer для `ShipmentPassportValidationFailedEvent` (CS escalation) — Order module Q3 2026.
- ⏳ E2E-тесты на webhook idempotency.

Полный roadmap — в [`webhooks.md` §Roadmap](./webhooks.md#roadmap).

## Источник и обновление

- **Source PDF:** «API Шипменты 16.04.2025.pdf» (внутренняя документация ДоброПост).
- **API version:** 2025-04-16.
- **Когда ДоброПост обновит контракт:** заменяется только `reference.md` + `openapi.json`. `integration.md` / `webhooks.md` / `status-codes.md` — стабильны (Loyality-side решения), правятся точечно.

## Связанное

- [[Research - Order (6) Logistics Integration]] — общая архитектура Shipping BC.
- [[Research - Order (2) State Machine FSM]] §15 — FSM Order cross-border + dropship.
- [[Research - Order (1) Domain-Driven Design]] — будущий Order aggregate.
- [[Loyality FRD]] — функциональные требования.
- `src/modules/logistics/` — текущий код (CDEK + Yandex полностью реализованы; DobroPost — точка расширения).
