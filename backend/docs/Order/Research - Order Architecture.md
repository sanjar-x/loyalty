---
tags:
  - project/loyality
  - backend
  - order
  - moc
  - research
type: research
date: 2026-04-29
aliases: [Order Architecture, Order Research MOC, Order Index]
cssclasses: [moc, research]
status: active
project: "[[Loyality Project]]"
component: backend
---

# Research — Order Architecture

> Индекс серии deep-research по Order management для Loyality. Серия покрывает теорию (DDD, FSM), индустриальные референсы (e-commerce giants, OMS), интеграционные boundary'и (Payment, Logistics), оркестрацию (Saga) и наблюдаемость (analytics). Используется как фундамент для будущей реализации модуля `order` (целевой milestone Q3 2026).

## Контекст

- **Project:** [[Loyality Project]]
- **Component:** [[Backend]] — модуль `order` (запланирован, не в коде)
- **Trigger:** В Loyality нет собственного склада, заказы идут двумя путями — передача поставщику (локальный/российский) или выкуп на кросс-бордер маркетплейсе (Poizon/Taobao/1688). Прежде чем писать модуль, нужно зафиксировать архитектурную модель Order и его отношения с Cart, Payment, Logistics, Inventory и Marketplace adapters.

**Scope research-серии:**

- Зафиксировать каноничную DDD-модель Order и границы с соседними BC.
- Выбрать каноничный FSM для Order, Payment, Shipment.
- Понять, как делают крупные платформы (B2C + OMS).
- Описать saga-flow checkout'а с компенсациями.
- Спроектировать analytics/admin читающий слой.

**Out of scope:**

- Реализация (код, SQL, FastAPI). Серия — research-only.
- Конкретные SDK PSP / carrier — это идёт в SPEC после серии.

## Research Map

```text
                    ┌──────── (1) DDD ─────────┐
                    │ aggregates / BCs / VOs   │
                    └──────────┬───────────────┘
                               │
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
   ┌─────────────┐    ┌──────────────┐   ┌──────────────┐
   │  (2) FSM    │    │ (3) E-com    │   │ (4) OMS      │
   │ status model│    │  giants      │   │ platforms    │
   └──────┬──────┘    └──────┬───────┘   └──────┬───────┘
          │                  │                  │
          └──────┬───────────┴──────────┬───────┘
                 ▼                      ▼
         ┌──────────────┐       ┌──────────────┐
         │ (5) Payment  │       │ (6) Logistics│
         │ integration  │       │ integration  │
         └──────┬───────┘       └──────┬───────┘
                │                      │
                └──────────┬───────────┘
                           ▼
                  ┌──────────────────┐
                  │  (7) Saga        │
                  │  orchestration   │
                  └─────────┬────────┘
                            ▼
                  ┌──────────────────┐
                  │  (8) Analytics   │
                  │  & operations    │
                  └──────────────────┘
```

## Документы серии

| # | Документ | Тема | Статус |
|---|----------|------|--------|
| 1 | [[Research - Order (1) Domain-Driven Design]] | Aggregates, bounded contexts, value objects, domain events; Evans / Vernon / Fowler | active |
| 2 | [[Research - Order (2) State Machine FSM]] | Канонические статусы Order, FSM-переходы, terminal states, idempotency, замена boolean-flags | active |
| 3 | [[Research - Order (3) E-commerce Giants]] | Amazon SP-API, Shopify GraphQL, Wildberries, Ozon, AliExpress, Lamoda — реальные модели | active |
| 4 | [[Research - Order (4) OMS Platforms]] | IBM Sterling, Manhattan Active, Salesforce OMS, fabric OMS — DOM, ATP, sourcing rules | active |
| 5 | [[Research - Order (5) Payment Integration]] | СБП, ЮKassa, Tinkoff, Stripe Payment Intents, 3DS, idempotency-keys, BNPL, split payments | active |
| 6 | [[Research - Order (6) Logistics Integration]] | Order ↔ Shipment, carrier-agnostic abstraction, СДЭК / Yandex Delivery, tracking, RMA | active |
| 7 | [[Research - Order (7) Saga Pattern]] | Choreography vs Orchestration, Outbox/Inbox, compensating actions, pivot transactions | active |
| 8 | [[Research - Order (8) Analytics and Operations]] | KPI 5 pillars, AOV / GMV / cohort, admin filters, bulk actions, Shopify/Magento UX | active |

## Сквозные принципы (cross-document консенсус)

Эти выводы повторяются в нескольких документах серии и формируют ядро будущей архитектуры модуля `order`:

1. **Order, Payment, Shipment — три разных bounded context.** Связь — по id, не по composition. (см. (1), (5), (6))
2. **FSM, не boolean-flags.** Order имеет одну FSM (lifecycle), Payment и Shipment — собственные, ортогональные. Shopify-style разделение financial/fulfillment FSM. (см. (2), (3), (5), (6))
3. **Idempotency-Key обязателен** на всех мутациях checkout, payment, label generation. UUID v4, TTL 24h+, UNIQUE constraint в БД. (см. (3), (5), (7))
4. **Order : Shipment = 1 : N** — multi-shipment per order стандарт, не исключение. PartiallyShipped — first-class state. (см. (3), (6))
5. **Pending — отдельное preliminary-состояние** до payment authorization, до полной валидации данных. Это инвариантная граница. (см. (2), (3))
6. **Compensation ≠ rollback.** Refund вместо void payment, release вместо restore inventory. Компенсации — forward-going бизнес-операции. (см. (2), (7))
7. **2PC мёртв, Saga — стандарт.** Outbox + Inbox для reliable messaging. Choreography для loose-coupled, Orchestration (Temporal/Camunda) для checkout-critical. (см. (7))
8. **Carrier-agnostic / PSP-agnostic abstraction** через ACL (Anti-Corruption Layer). Adapter pattern для каждого external provider'а. (см. (5), (6))
9. **CQRS-разделение write/read.** Operational dashboards и business KPI dashboards — разные read-models, разные refresh policies. (см. (8))
10. **Cancellation reasons — taxonomized enum.** Не free-text, чтобы потом строить причины-фильтры в analytics. (см. (8))

## Open Questions (для будущего SPEC)

- Marketplace adapter (Poizon / Taobao / 1688) — это часть Order BC, отдельный BC или intermediary в Logistics? (касается (1), (6))
- Saga для Loyality checkout — choreography (RabbitMQ events, который уже есть) или orchestration (новый Temporal/TaskIQ workflow)? (касается (7))
- Inventory reservation в нашей модели — нужен ли вообще, или dropship-модель его вытесняет? (касается (1), (7))
- Loyalty cashback и promo — это part of Order или отдельный BC, событийно связанный? (касается (1), пересечение с будущим модулем `loyalty`)
- Two-step authorize+capture для СБП — поддерживается ли вообще? (касается (5))

## Deliverables после серии

После того как серия будет в `final`, ожидается:

1. **`SPEC - Order Module.md`** — целевой архитектурный документ модуля `order` (структура aggregates, FSM, контракты, schema БД).
2. **`ADR - Order vs Marketplace Adapter Boundary`** — границы responsibility между `order` и кросс-бордер-адаптерами.
3. **`ADR - Saga Orchestration Choice`** — choreography vs orchestration для checkout.
4. **`SPEC - Payment Module.md`** — payment как отдельный модуль backend (PSP adapters, idempotency, 3DS, СБП).
5. Дополнения в `Loyality Project.md` Timeline для модулей `order` / `loyalty`.

## Related

- [[Backend]] — backend dashboard
- [[Loyality Project]] — project dashboard
- [[Loyality TRD]] — technical requirements
- [[ADR-001 Clean Architecture Modular Monolith]]
- [[BRD - Cart Module]] / [[SPEC - Cart Module]] — Cart как upstream от Order
- [[BRD Checkout]] — checkout BRD
- Cart research series: [[Research - Cart Architecture (1) Enterprise Platforms]] · [[Research - Cart Architecture (2) Crossborder Marketplace Patterns]] · [[Research - Cart Architecture (3) DDD Patterns]] · [[Research - Cart Architecture (4) Pricing and Payments]] · [[Research - Cart Architecture (5) State Management and UX]]
- Activity research series: [[Research - Activity Tracking Architecture]]
