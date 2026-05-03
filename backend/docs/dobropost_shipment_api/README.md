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

## Roadmap

Единый план интеграции ДоброПост (provider-стек + webhook + Order-side). Single source of truth для всех trackable пунктов — другие файлы ссылаются сюда.

| #   | Задача                                                                                  | Статус               |
| --- | --------------------------------------------------------------------------------------- | -------------------- |
| 1   | Добавить `dobropost` в `_FACTORY_MAP` (`infrastructure/bootstrap.py`)                   | ✅ Done              |
| 2   | `DobroPostProviderFactory` + `DobroPostWebhookAdapter`                                  | ✅ Done              |
| 3   | `DobroPostBookingProvider` (`POST /api/shipment`)                                       | ✅ Done              |
| 4   | `DobroPostTrackingPollProvider` (`GET /api/shipment`)                                   | ✅ Done              |
| 5   | `Shipment` factory `create_admin_managed` + поле `cross_border_arrived_at`              | ✅ Done              |
| 6   | `CrossBorderArrivedEvent` + хук в `Shipment.append_tracking_event` (idempotent)         | ✅ Done              |
| 7   | `ShipmentPassportValidationFailedEvent` + `HandleDobroPostPassportValidationHandler`    | ✅ Done              |
| 8   | Admin command `CreateCrossBorderShipmentHandler` (procurement flow)                     | ✅ Done              |
| 9   | Provider-input validator — отвергает DobroPost-аккаунт без webhook auth                 | ✅ Done              |
| 10  | Partial index `ix_shipments_stuck_cross_border` для nightly job                         | ✅ Done              |
| 11  | Не добавлять `dobropost` в `_PROVIDER_COVERAGE` — admin-managed, не участвует в rate fan-out | ✅ Решено (см. §архитектурные инварианты) |
| 12  | Order-side consumer для `CrossBorderArrivedEvent` (создание Shipment #2)                | ⏳ Order module Q3 2026 |
| 13  | Order-side consumer для `ShipmentPassportValidationFailedEvent` (CS escalation)         | ⏳ Order module Q3 2026 |
| 14  | E2E-тесты webhook idempotency (дубликат payload)                                        | ⏳ TODO              |

## Глоссарий

Термины, которые встречаются на каждой странице — определения держим здесь, в других файлах не повторяем.

| Термин                  | Что значит                                                                                                                                |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| **Cross-border**        | Сегмент маршрута Китай → таможня → склад ДоброПост в РФ. Покрывается **Shipment #1** (provider=`dobropost`).                              |
| **Last-mile**           | Сегмент склад ДоброПост → ПВЗ → customer. Покрывается **Shipment #2** (provider=`cdek` / `yandex_delivery`).                              |
| **Shipment #1 / #2**    | Первый/второй shipment одного Order'а. На Order **минимум 2 shipment'а**, всегда. См. инвариант №1.                                         |
| **`incomingDeclaration`** | Китайский трек-номер (поле в `POST /api/shipment`). Customer видит его как «трек по Китаю».                                              |
| **`dptrackNumber`**     | Трек-номер ДоброПост (возвращается в ответе `POST /api/shipment`). Используется как `tracking_number` для Shipment #1.                    |
| **`dpTariffId`**        | ID тарифа доставки ДоброПост (фиксированный по партнёрскому договору; Loyality передаёт hard-coded ID, не выбирает динамически).         |
| **DP Ultra**            | Один из тарифов ДоброПост; единственный, для которого `consigneeBirthDate` обязательное.                                                   |
| **DaData**              | Внешний сервис проверки актуальности паспорта по реестру МВД РФ. Используется ДоброПост перед таможенным оформлением.                       |
| **ПВЗ**                 | Пункт выдачи заказов. Customer выбирает ПВЗ **российского** carrier'а (CDEK / Yandex), не ДоброПост.                                      |
| **Procurement flow**    | Manager-action: выкуп товара в Китае + регистрация в ДоброПост. Реализован в `CreateCrossBorderShipmentHandler`.                          |
| **Admin-managed shipment** | Shipment, создаваемый менеджером (а не customer'ом через checkout). Фабрика `Shipment.create_admin_managed`. Только cross-border сегмент. |
| **Status_id 648 / 649** | Триггеры создания Shipment #2: «подготовлено к last-mile» / «передано на доставку по РФ». Emit'ит `CrossBorderArrivedEvent`.              |

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
