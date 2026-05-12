---
tags:
  - project/loyality
  - backend
  - order
  - oms
  - benchmarks
  - research
type: research
date: 2026-04-29
aliases: [OMS Platforms, Distributed Order Management, OMS vs ERP vs WMS]
cssclasses: [research]
status: active
parent: "[[Research - Order Architecture]]"
project: "[[Loyality Project]]"
component: backend
---

# Research — Order (4) OMS Platforms

> Индустриальные стандарты OMS-фич и разделение ответственности OMS / ERP / WMS. Платформы: IBM Sterling, Manhattan Active Omni, Oracle Retail OMS, NetSuite, Salesforce OMS, fabric OMS. DOM, ATP/ATS/ATC, sourcing rules, BOPIS, ship-from-store, RMA.

## TL;DR — ключевые выводы

1. **OMS — это single source of truth** для заказа и для inventory availability. ERP — для финансов, WMS — для физического склада, OMS — для customer-facing order lifecycle и orchestration.
2. **DOM (Distributed Order Management)** — стандарт de-facto. Gartner определяет три обязательные фичи: order orchestration, enterprise inventory visibility, order fulfillment optimization. Без них это не enterprise OMS.
3. **Архитектурный консенсус 2024–2026:** микросервисы, API-first, cloud-native, headless (MACH). IBM Sterling, Manhattan Active, Salesforce OMS, fabric OMS — все построены на этих принципах. Только NetSuite остаётся монолитной частью ERP.
4. **Разница между вендорами — не в фичах, а в композиции.** Базовый набор (DOM + ATP + sourcing rules + BOPIS + ship-from-store + RMA + returns) есть у всех. Разница: deployment model (cloud-native vs hybrid), pricing, расширяемость, deep retail-vertical features (size/curve allocation, store ops UI).
5. **Available-to-Promise (ATP)** — отдельный first-class engine, не SQL-запрос к stock. Реальный ATP учитывает on-hand, in-transit, on-order, safety stock, channel allocation, fulfillment lead times, sourcing rules, и возвращает promise date.
6. **OMS поглощает фичи WMS и ERP** постепенно (store inventory, simple billing/finance), но настоящие enterprises всё равно держат три системы — OMS как orchestration layer.

---

## 1. Что такое OMS — современное определение

### 1.1 Определение Gartner

Gartner определяет Distributed Order Management (DOM) как software that orchestrates and optimizes the order fulfillment process. Три обязательные капабилити:

1. **Order Orchestration** — конфигурируемые business rules в иерархии (по каналам, гео, сегментам клиентов).
2. **Enterprise Inventory Management** — видимость inventory на уровне всей сети (DC, stores, in-transit, on-order, supplier-owned).
3. **Order Fulfillment Optimization** — выбор оптимального источника отгрузки по cost / SLA / margin.

### 1.2 Современный OMS = order hub

OMS в 2025–2026 позиционируется как order hub / single source of truth:

- Real-time inventory truth (не batch-sync из ERP/WMS/POS).
- AI-powered routing с учётом proximity, delivery windows, fulfillment costs, warehouse congestion.
- Configurable routing rules без внешней разработки.
- Real-time revisions параметров маршрутизации.

Глобальный рынок omnichannel OMS оценивается в ~$3.64 млрд и растёт двузначно — драйверы: real-time expectations, fragmented tech stacks, AI.

---

## 2. Индустриальный стандарт фич OMS (must-have в 2026)

Эталонный feature checklist, который встречается у всех изученных вендоров:

### 2.1 Order capture & aggregation

- Multi-channel ingestion (web, mobile, marketplace, POS, contact center, EDI, social commerce).
- Unified order representation независимо от канала.
- Single customer view across orders.
- Idempotent order create API.

### 2.2 Inventory & promising

- **Enterprise inventory visibility** — DC + stores + in-transit + on-order + supplier inventory.
- **Available-to-Promise (ATP)** rules engine (отдельно от sourcing).
- **Available-to-Sell (ATS)** projection (per channel, с allocation/safety stock policies).
- **Available-to-Commerce (ATC)** — Manhattan-style: что выставлено в каналы.
- Real-time stock updates с conflict resolution.

### 2.3 Order orchestration / DOM

- Configurable sourcing rules в иерархии (channel → region → product category → SKU).
- Weighted brokering — выбор location по margin / labor cost / proximity.
- Order splitting — split order across nodes (line-level и quantity-level).
- Fulfillment zones — гео-ограничения на источники.
- Backorder / preorder / dropship flows.
- Re-route при exceptions (нехватка stock, отказ store).

### 2.4 Fulfillment options

- Ship-from-DC, ship-from-store.
- BOPIS (Buy Online, Pickup In-Store).
- BOPAC / curbside pickup.
- Ship-to-store (для последующего pickup или replenishment).
- Endless aisle (виртуальная полка).
- Locker pickup, third-party PUDO.

### 2.5 Customer service / agent UI

- Order modification post-capture (адрес, способ доставки, items).
- Manual exception handling.
- Refund / partial refund / store credit / exchange.
- Appeasements (compensations) и flexible discounting.
- Cross-order customer history.

### 2.6 Returns & RMA

- Automated RMA generation с правилами авторизации.
- Customer self-service return portal.
- Carrier label generation (multi-carrier).
- Disposition routing: restock / refurbish / recycle / liquidate / donate.
- Fraud detection (return-pattern analytics).
- Reverse logistics network optimization.

### 2.7 Payments

- Multi-PSP integration (Stripe, Adyen, регионально-специфичные).
- Authorize / capture split (capture после ship).
- Partial captures, partial refunds.
- 3DS, SCA support.
- Multiple tender split (gift card + card + loyalty points).

### 2.8 Analytics & reporting

- Operational dashboards (fill rate, on-time %, split rate, cancel rate, NPS).
- Business KPI (AOV, conversion, refund rate, return rate by SKU).
- Cohort и retention analytics.
- Cause analysis (cancel reasons taxonomy).

### 2.9 Platform / extensibility

- API-first (REST / GraphQL).
- Webhooks / event streaming.
- Drag-and-drop workflow builder (low-code).
- Plug-in / extension framework.
- Multi-tenant SaaS deployment.

---

## 3. IBM Sterling Order Management

### 3.1 Позиционирование

Один из старейших enterprise-OMS, де-факто reference-implementation для крупного retail/B2B. Используется крупнейшими ритейлерами; в Black Friday 2024 платформа обработала 20+ миллиардов API calls и inventory actions.

### 3.2 Архитектура

- Перешёл от monolithic Java-стека к composable, microservice-based, API-first архитектуре.
- 400+ настраиваемых environments.
- Multi-tenant микросервисы со scale horizontal/vertical.
- Гибридные deployments (on-prem + cloud).

### 3.3 Модули

| Модуль | Назначение |
|---|---|
| Distributed Order Management (DOM) | Aggregation orders, sourcing engine, lifecycle management |
| Sterling Intelligent Promising | AI-driven ATP / promise date / cost-margin optimization |
| Sterling Store Engagement | Store associate UI, ship-from-store, BOPIS |
| Sterling Store Inventory Management (SIM) | Store-level stock, cycle counts, replenishment |
| Sterling Fulfillment Optimizer | Cost-optimal sourcing с margin awareness |
| Sterling Inventory Visibility | Enterprise-wide inventory aggregation |
| Sterling Call Center | Agent UI |
| Sterling Configure-Price-Quote | B2B configuration |

### 3.4 Ключевые фичи

- Single order repository для modify / cancel / track / monitor в real-time.
- Intelligent sourcing engine для extended enterprise (включая partners, suppliers).
- AI-based fulfillment optimization — assess product margins, shipping speeds, fulfillment costs against inventory data across DCs and stores.
- B2B advanced capabilities preview — большой фокус на B2B order types (contracts, scheduled orders, blanket POs).
- Modernization journey — IBM публикует 3-stage roadmap для миграции legacy → composable.

### 3.5 Где применяется

Tier-1 retail (Macy's, Best Buy, Office Depot — публичные case studies), telco, large B2B distributors. Сложен в имплементации, но extremely расширяем.

---

## 4. Manhattan Active Omni

### 4.1 Позиционирование

Cloud-native OMS, объединённый с POS, customer engagement, store inventory & fulfillment в единое приложение Active Omni. Главный конкурент IBM Sterling в enterprise сегменте.

### 4.2 Архитектура

- API-first, all-microservices платформа.
- Cloud-native, auto-scaling.
- Never needs upgrading — continuous delivery, версии не публикуются как у legacy software.
- Developer-friendly, resilient.

### 4.3 Состав Active Omni

| Компонент | Назначение |
|---|---|
| Active Order Management | Order orchestration, lifecycle |
| Available to Commerce | Channel-aware inventory exposure |
| Fulfillment Optimization | Best source/route selection |
| Active Store Inventory & Fulfillment | Store ops, ship-from-store, BOPIS |
| Active Point of Sale | Modern POS интегрированный с OMS |
| Active Customer Engagement & Service | Agent UI |
| Omnichannel Allocation | Cross-channel inventory allocation |

### 4.4 Ключевые фичи

- **Available to Commerce (ATC)** — отдельный концепт: что доступно для конкретного канала, с настройкой safety stock и promotion holdouts.
- **Real-time, dynamic inventory visibility** через все DCs и stores (case Duluth Trading: 4 DCs + 65 stores + digital).
- **Order splitting & consolidation** — обе операции first-class.
- **AI/ML driven order routing** с оптимизацией conversion + fulfillment cost одновременно.
- **In-store fulfillment workflows** — picklist generation, packing UI, shipping label.
- **Endless aisle** — продажа в магазине того, чего нет в магазине.

### 4.5 Где применяется

Apparel & footwear (Adidas, Crate & Barrel), specialty retail. Сильнее IBM Sterling в native cloud experience, слабее — в B2B.

---

## 5. Oracle Retail Order Management Suite (OROMS)

### 5.1 Позиционирование

Renamed: ранее Order Management System Cloud Service, теперь Retail Order Administration Cloud Service в составе Retail Order Management Suite Cloud Service. Direct-to-consumer фокус (web, contact center, retail stores).

### 5.2 Состав suite

| Компонент | Назначение |
|---|---|
| Order Administration | Lifecycle: capture → fulfillment, exceptions |
| Retail Order Broker | Routing engine, sourcing |
| Customer Engagement | CSR tools |
| Order Reporting & Analytics | KPIs, dashboards |

### 5.3 Routing Engine — Oracle Retail Order Broker

Отдельно стоит выделить — это reference-implementation routing engine:

- **Weighted brokering:** предпочтение locations по lower labor cost, in-store margin (selling price - cost) ниже online margin.
- **Allow Split Order preference + Allow Split Line** — quantity одной линии может быть split across locations.
- **Fulfillment zones** — гео-ограничения на eligible locations.
- **Exclude Locations with Zero Availability** — pre-filter до probability rules.
- **Probability rules** — моделирование вероятности выполнения location'ом.

### 5.4 Ключевые фичи

- Online + batch payment authorization.
- Promotion management (effectiveness tracking).
- Returns and exchanges, returns-in-store.
- Real-time inventory visibility через rules-based brokering engine.
- Multi-channel order fulfillment.

### 5.5 Где применяется

Mid-market retail с Oracle stack (Retail Merchandising, Retail Stores, Retail Insights). Не лучший выбор для greenfield modern stack.

---

## 6. NetSuite (Order Management внутри ERP)

### 6.1 Позиционирование

NetSuite не является pure-play OMS — это ERP с встроенным order management. Главное преимущество: отсутствие интеграционной поверхности между OMS и ERP. SuiteCommerce — встроенная e-commerce платформа.

### 6.2 Особенность

> "Your online store runs on the same database as your ERP — inventory, pricing, customer records, and order data are all native, with no middleware, no sync jobs, and no integration to maintain."

Это и плюс, и минус:

- ✅ Нет sync issues между OMS и ERP.
- ✅ Финансы (revenue recognition, COGS) автоматически в один такт с order events.
- ❌ Не предлагает best-of-breed OMS-функционала enterprise-уровня.
- ❌ Frontend SuiteCommerce — слабая часть стека.

### 6.3 Order management фичи

- End-to-end order lifecycle от cart до fulfillment.
- Multi-channel order consolidation (web, marketplace, phone, EDI).
- Drop ship & special orders — auto-generated POs к vendors с customer shipping address.
- Backorder handling — orders не stuck в pending, есть exception flows.
- Inventory commitment per order line.
- Dropship purchase orders — sales order Mark Shipped → PO → Pending Billing flow.

### 6.4 Где применяется

SMB / mid-market multi-channel ритейл. Часто используется как ERP под Shopify или другим headless front-end (Shopify+NetSuite — типичная комбинация).

---

## 7. Salesforce Order Management

### 7.1 Позиционирование

Часть Salesforce Commerce Cloud, native интеграция с B2C Commerce, B2B Commerce, Service Cloud. Позиционируется как "OMS, который знает customer" — leveraging Salesforce CDP/Service.

### 7.2 Архитектура & data model

Salesforce Order Management имеет один из самых больших data model среди продуктов Salesforce. Ключевые objects:

| Object | Назначение |
|---|---|
| Order | Original captured order (immutable snapshot) |
| OrderSummary | Mutable view — current state с changes/refunds/cancellations |
| FulfillmentOrder | Триггерит downstream fulfillment process |
| FulfillmentOrderLineItem | Items в FulfillmentOrder |
| OrderItemSummary | Текущее состояние line item |
| OrderDeliveryGroup | Группировка items по shipping method |
| OrderPaymentSummary | Платёжный agg по order |
| Returns / Refunds / Adjustments | Financial events |

### 7.3 Ключевая идея: Order vs OrderSummary

- **Order** = "что покупатель отправил" — immutable snapshot.
- **OrderSummary** = "что есть сейчас" — учитывает cancellations, modifications, returns.

Это elegant решение проблемы immutability vs mutability в OMS.

### 7.4 Process automation

- Create Fulfillment Order Flow — генерирует FulfillmentOrder из Order, push в WMS.
- WMS возвращает status updates через webhooks/API.
- Drag-and-drop workflow builder на основе Salesforce Flow.
- Pre-built supply chain workflows.
- Service Cloud integration для return/exchange.

### 7.5 DOM-функциональность

- Sourcing/routing rules (proximity, cost, SLA).
- Order splitting.
- Inventory updates через native интеграцию или ERP.
- Re-routing logic (если reservation cancelled).

### 7.6 Где применяется

Brands в Salesforce ecosystem (Commerce Cloud customers). Хорош там, где customer 360 уже на Salesforce. Слабее в pure-retail-ops (in-store ops UI скромный).

---

## 8. fabric OMS

### 8.1 Позиционирование

Cloud-native, AI-powered DOM от MACH-натурального вендора (модульный composable commerce). Целевая аудитория — mid-market и upper-mid enterprises, которым нужен OMS без heavy lift IBM/Manhattan implementation.

### 8.2 Архитектура

- Multi-tenant cloud architecture on AWS.
- Modular & scalable — можно купить отдельные модули.
- Configurable без кодинга — "modify order fulfillment logic without the need for coding".

### 8.3 Ключевые фичи

- Distributed Order Management (DOM).
- Advanced order routing.
- Network aggregation (DCs + stores + 3PLs + suppliers в единый view).
- Preorder / backorder inventory management — first-class.
- BOPIS, ship-to-store, store-as-mini-DC.
- 360-degree inventory view — on-shelf, in-transit, on-order across nodes.
- Order aggregation — single source of truth across channels.

### 8.4 Где применяется

Direct-to-consumer brands, mid-market multi-store retailers. Конкурирует с Kibo, Deck Commerce, OneStock, Hardis в этом сегменте.

---

## 9. Сводная сравнительная таблица

| Аспект | IBM Sterling | Manhattan Active Omni | Oracle OROMS | NetSuite | Salesforce OMS | fabric OMS |
|---|---|---|---|---|---|---|
| Тип | Composable enterprise OMS | Cloud-native unified commerce | Retail-vertical OMS | ERP-integrated OM | CRM-integrated OMS | MACH-native OMS |
| Архитектура | Microservices, hybrid cloud | Microservices, cloud-native, no-upgrade | Cloud service | Monolithic SaaS ERP | Multi-tenant SaaS, Force.com | Multi-tenant AWS-native |
| Деплоймент | On-prem + cloud + hybrid | Pure cloud | Pure cloud | Pure cloud | Pure cloud | Pure cloud |
| DOM (Gartner-grade) | ✔ | ✔ | ✔ | Limited | ✔ | ✔ |
| ATP engine | Sterling Intelligent Promising | Available-to-Commerce | Order Broker rules | Native ATP | Native + integrations | Built-in |
| In-store ops | Strong (SIM, Store Engagement) | Strong (Active Store) | Moderate | Limited | Moderate | Moderate |
| B2B support | Strong | Moderate | Weak | Strong (ERP) | Moderate | Weak |
| Returns / RMA | ✔ Full | ✔ Full | ✔ Full | ✔ Basic | ✔ via Service Orders | ✔ |
| Workflow customization | Configuration + custom code | Config-heavy | Config | SuiteScript | Salesforce Flow / Apex | No-code config |
| Целевой сегмент | Tier-1 enterprise | Tier-1 enterprise | Mid-tier retail | SMB/mid-market | SF ecosystem | Mid-market / DTC |

---

## 10. OMS vs ERP vs WMS — разделение ответственности

### 10.1 Эссенциальное правило (mental model)

| Система | Главный вопрос | Источник истины для |
|---|---|---|
| OMS | "Где взять и как доставить эти items этому customer?" | Customer-facing order state, inventory availability across nodes, sourcing decisions |
| ERP | "Сколько денег / стоимости в книгах на каждом этапе?" | Financial state (AR, AP, GL, COGS, revenue), cross-functional master data, procurement |
| WMS | "Как товар физически переместить в этом конкретном здании?" | Physical inventory by bin/zone, picking paths, putaway, labour |

### 10.2 Зоны ответственности — детальная разбивка

#### 10.2.1 OMS owns

- Order capture, validation, idempotency.
- Order lifecycle FSM (created → paid → fulfilled → shipped → delivered → returned).
- Multi-channel order aggregation.
- Sourcing/routing decisions (which node fulfills what).
- ATP/ATS calculation поверх aggregated inventory.
- Customer-facing tracking & notifications.
- Returns initiation, RMA generation.
- Cross-channel inventory visibility (read-only aggregation поверх WMS feeds).
- Order modification (cancel / edit / re-route).
- Customer 360 view (orders, returns, support history).

#### 10.2.2 WMS owns

- Bin-level inventory accuracy внутри warehouse.
- Wave / batch / zone picking strategies.
- Putaway / receiving / cycle counts.
- Labour management, productivity tracking.
- Equipment integration (conveyor, sorters, robots).
- Pack station logic, carton optimization.
- Shipping execution (label print, manifest).
- Cross-docking workflows.
- Returns physical receiving + grading.

#### 10.2.3 ERP owns

- General Ledger, financial close.
- AR/AP, invoicing, collections.
- Procurement (PO management for inbound).
- Master data: items, vendors, customers (financial side).
- Tax engine integration / tax filing.
- Manufacturing planning (MRP).
- Cost accounting, COGS, margin reporting.
- HR / payroll (для классических ERP).
- Demand planning, forecasting.

### 10.3 Серые зоны — где дублирование возможно

| Capability | OMS | ERP | WMS | Кто должен владеть? |
|---|---|---|---|---|
| Inventory availability | ✔ aggregated | ✔ accounting view | ✔ physical | OMS для customer view, WMS для физической accuracy, ERP — financial reconciliation |
| Order state tracking | ✔ customer-facing FSM | ✔ financial | – | OMS для customer; ERP отражает financial events |
| Returns processing | ✔ initiation/RMA | ✔ refund accounting | ✔ physical receive | OMS orchestrates, WMS выполняет, ERP finalizes finance |
| Order capture | ✔ | Sometimes | – | OMS (всегда в modern stack) |
| Pricing | – | ✔ list price | – | ERP (или dedicated pricing service в composable stack) |

### 10.4 Mental model в одной фразе

> Если главная боль — **warehouse speed and accuracy** → нужен WMS.
>
> Если главная боль — **order volume and multichannel selling** → нужен OMS.
>
> Если главная боль — **cross-department alignment** (finance, production, purchasing) → нужен ERP.

В большинстве enterprise-стеков нужны все три и они интегрируются.

### 10.5 Современный тренд: OMS поглощает соседние домены

- OMS забирает у ERP: customer-facing order state, simple invoicing, partial inventory accounting.
- OMS забирает у WMS: store inventory management (через мобильные store ops apps).
- ERP сохраняет: financial close, GL, tax, deep procurement, HR.
- WMS сохраняет: warehouse-internal physical execution.

Tier-1 OMS (IBM Sterling, Manhattan) уже включают полноценный store inventory management module. Это не значит, что они заменяют WMS на 200K-SKU DC — но для store-as-DC (200–10K SKUs) — заменяют.

---

## 11. Архитектурные паттерны OMS — best practices

### 11.1 MACH (Microservices, API-first, Cloud-native, Headless)

Стандарт для современных OMS:

- **Microservices:** order capture, sourcing, ATP, fulfillment, returns, payments — каждое отдельным сервисом.
- **API-first:** всё доступно через REST/GraphQL до того как появился UI.
- **Cloud-native:** контейнеризация, auto-scaling, multi-region.
- **Headless:** UI отделён от бизнес-логики; OMS UI ≠ единственный консьюмер OMS API.

Все из изученных вендоров (кроме NetSuite) объявляют MACH-compliance в той или иной степени.

### 11.2 Composable commerce

OMS — один из компонентов decomposed commerce stack: search / checkout / PIM / OMS / pricing / loyalty — separate API-connected services.

> Every composable architecture is headless; not every headless implementation is composable.

OMS становится central orchestrator: ловит events от storefront, payment, inventory, и оркестрирует fulfillment.

### 11.3 Event-driven backbone

Современные OMS строятся на event streaming (Kafka, Kinesis):

- `OrderCreated` → запускает sourcing.
- `OrderSourced` → запускает payment capture.
- `PaymentCaptured` → запускает fulfillment release.
- `Shipped` → запускает customer notification + ERP financial event.
- `Delivered` → запускает loyalty / NPS.
- `ReturnRequested` → запускает RMA workflow.

Это естественно совпадает с FSM из Темы 1 и Saga pattern (Тема 5).

### 11.4 Configuration-over-code

Все enterprise OMS позиционируют no-code/low-code rule editing:

- IBM Sterling: configurable order pipelines.
- Manhattan: configurable orchestration rules.
- fabric: AI-powered no-code workflows.
- Salesforce: Salesforce Flow.
- Oracle Order Broker: weighted brokering settings.

Цель: бизнес-аналитики могут менять sourcing logic без deployment. Это критично для seasonality (peak), promo events, store closures.

---

## 12. Available-to-Promise (ATP) — глубокий разбор

ATP — отдельная критичная подсистема, заслуживающая внимания.

### 12.1 Что такое ATP

ATP rules engine отвечает на вопрос: "Можем ли мы пообещать customer'у этот item в этот срок к этому адресу — и если да, то откуда?"

Ответ — не yes/no, а: yes/no + promise date + source location + cost.

### 12.2 Что входит в supply pool

ATP не равен on-hand inventory. Включает:

- **On-hand** (физически на складе, не reserved).
- **In-transit** (между warehouses).
- **On-order** (PO размещён, ETA известна).
- **Available from supplier** (vendor-stocked, dropship eligible).
- **Allocated future** (planned receipt).

Минус allocations: safety stock, channel reservations, promo holdouts.

### 12.3 Что входит в правила

- **Sourcing rules** — какие nodes могут fulfilment'ить какие order types.
- **Assignment sets** — связка sourcing rules с territories/products.
- **ATP rules** — как именно считать availability (which buckets to consider, lead times).
- **Allocation rules** — как resolve conflicts (multiple orders на одну единицу).

### 12.4 Reference implementations

- **Oracle Fusion Global Order Promising (GOP)** — самая формализованная модель: sourcing rules + assignment sets + ATP rules + allocation rules.
- **IBM Sterling Intelligent Promising** — AI-driven, оптимизирует cost + margin + speed одновременно.
- **Manhattan Available to Commerce** — channel-aware: одну и ту же on-hand можно разделить между digital и retail.
- **fabric OMS** — built-in promise engine с network aggregation.

### 12.5 Важно: ATP ≠ ATS ≠ ATC

| Термин | Семантика |
|---|---|
| ATP (Available-to-Promise) | Что мы обещаем доставить, с promise date |
| ATS (Available-to-Sell) | Что виртуально доступно для покупки в каком-либо канале |
| ATC (Available-to-Commerce) | Что реально выставлено в конкретный канал (Manhattan-specific) |

ATS ≥ ATC всегда (ATC = ATS minus channel allocations).

---

## 13. Где какой OMS выбрать — decision matrix

### 13.1 Сценарии и рекомендации

| Сценарий | Рекомендация |
|---|---|
| Tier-1 retail (1000+ stores, 10M+ orders/year), сложный B2B+B2C | IBM Sterling или Manhattan Active Omni |
| Tier-1 retail с фокусом на cloud-native, no upgrades | Manhattan Active Omni |
| Уже инвестировали в Salesforce ecosystem | Salesforce OMS |
| SMB/mid-market, нужна tight integration с финансами | NetSuite |
| Mid-market DTC, MACH stack, скорость time-to-market | fabric OMS |
| Уже на Oracle Retail stack | Oracle OROMS |
| Greenfield, сложная network, in-house engineering | Композиция: fabric/commercetools + Stripe + Algolia + WMS |

### 13.2 Anti-patterns

- ❌ Покупка Tier-1 OMS под SMB load (стоимость владения, time-to-value).
- ❌ Использование NetSuite как enterprise OMS на 100M+ orders/year — она не для этого.
- ❌ Build своего OMS с нуля без понимания ATP/sourcing complexity — это 3+ years of engineering.
- ❌ Multi-OMS topology (OMS-A для одного канала, OMS-B для другого) — теряется единая customer view.

---

## 14. Тренды 2025–2026

1. **AI / ML повсеместно:** order routing, demand forecasting, fraud detection, return optimization, NPS prediction.
2. **Real-time inventory** становится нормой (vs batch sync). Без этого modern customer expectations не выполнить.
3. **Store-as-DC / micro-fulfillment** — stores играют роль mini-DCs, OMS должен это поддерживать как first-class node type.
4. **Sustainability scoring** в sourcing rules — выбор location с минимальным CO2.
5. **Composable commerce** вытесняет monolithic suites в greenfield projects.
6. **Convergence OMS + POS** (Manhattan Active Omni — самый яркий пример).
7. **Embedded customer service** — OMS включает agent UI как неотъемлемую часть.

---

## 15. Чек-лист "что должен включать enterprise OMS в 2026"

- [ ] Multi-channel order capture (web, mobile, marketplace, POS, EDI, contact center)
- [ ] Idempotent order creation API
- [ ] Order lifecycle FSM с явным separation финансового и fulfillment state
- [ ] Enterprise inventory aggregation (DC + store + in-transit + on-order + supplier)
- [ ] ATP rules engine (separate от sourcing engine)
- [ ] Configurable sourcing rules (no-code)
- [ ] Weighted brokering (cost/margin-aware)
- [ ] Order splitting (line + quantity level)
- [ ] BOPIS / curbside / ship-to-store / endless aisle
- [ ] Ship-from-store с store-side workflow UI
- [ ] Real-time inventory updates (event-driven)
- [ ] RMA generation, return labels, disposition routing
- [ ] Multi-PSP payment integration с partial capture / partial refund
- [ ] Multi-tender split (gift card + card + loyalty)
- [ ] Saga-based orchestration с compensating actions
- [ ] Webhooks / event streaming для downstream integrations
- [ ] ERP-grade financial event reconciliation
- [ ] WMS integration (bidirectional, real-time)
- [ ] CSR / agent UI
- [ ] Operational dashboards (fill rate, on-time, split rate, cancel rate)
- [ ] Business KPI dashboards (AOV, conversion, return rate)
- [ ] Multi-region / multi-currency / multi-locale
- [ ] Tax engine integration
- [ ] Fraud scoring integration
- [ ] Audit trail и event sourcing для compliance

---

## 16. Источники

### Industry & Gartner

- Gartner — Distributed Order Management Systems Market
- Gartner Market Guide for DOM Systems
- Gartner Market Guide 2025 for DOM — Kbrw
- Gartner 2025 DOM — Hardis
- Gartner Report — fabric
- Omnichannel Order Management 2025 Guide — Coderapper

### IBM Sterling

- IBM Sterling Order Management — IBM
- IBM Sterling Distributed Order Management overview
- Sterling Distributed Order Management features
- IBM Sterling Order and Fulfillment Suite
- Map your journey to IBM Sterling Order Management modernization
- Sterling Store Inventory Management

### Manhattan Active Omni

- Manhattan OMS solutions
- What is an OMS? — Manhattan
- Manhattan Active OMS Review — The Retail Exec
- Omnichannel Allocation — Manhattan
- Store Inventory and Fulfillment — Manhattan
- Duluth Trading + Manhattan Active Omni case study

### Oracle Retail OMS

- Oracle Retail Order Management Suite Cloud Service docs
- Oracle Retail OMS Cloud Service press release
- Order Broker Routing Engine Overview
- Oracle Order Broker Whitepaper — Quickborn
- Set Up Promising Rules and Sourcing Rules for Order Management — Oracle

### NetSuite

- NetSuite Order Management — Oracle docs
- SuiteCommerce — Oracle NetSuite for Ecommerce
- NetSuite Drop Shipment and Special Order Purchases
- NetSuite Setting Up Drop Shipping
- NetSuite Ecommerce Guide — BrokenRubik

### Salesforce OMS

- Salesforce Order Management — Salesforce
- Salesforce OMS Order Management Standard Objects
- Salesforce Order Management Data Model — Firat Esmer
- Salesforce Order Lifecycle Management — Trailhead
- Implement Distributed Order Management — Trailhead
- Objects Used by Order Management — Salesforce Help

### fabric OMS

- Order Management System — fabric OMS
- Distributed Order Management System features — fabric
- fabric OMS Developer Overview
- Next-Gen Fulfillment Orchestration — fabric blog
- What is Order Management — fabric

### OMS vs ERP vs WMS

- WMS vs OMS — TechTarget
- ERP vs OMS vs WMS — The Web Addicts
- OMS and WMS Better Together — Deposco
- ERP vs WMS Key Differences — Hardis Supply Chain
- What is ERP, PIM, WMS, OMS — Folio3
- Complete Guide to WMS, OMS, IMS, ERP — Skulabs

### MACH / Composable

- Composable Commerce vs Headless — Elogic
- Headless vs Composable vs MACH — Alokai
- The Differences Between Composable, Headless and MACH — commercetools
- MACH Architecture & NetSuite — BrokenRubik

### BOPIS / Store Fulfillment

- BOPIS Guide — fabric
- How an OMS Automates BOPIS and Curbside Pickup — Deck Commerce
- What is BOPIS — IBM Think
- BOPIS — Kibo Documentation

### ATP / Promising

- Set up ATP — Microsoft Learn
- Oracle Fusion Global Order Promising
- How Order Promising Rules Work Together — Oracle
- Available-to-Promise — Interlake Mecalux

### Returns / RMA

- What is RMA — Loop Returns
- Returns Management System — ReverseLogix
- What is a Return Management System — Claimlane

---

## Related

- [[Research - Order Architecture]] — индекс серии Order
- [[Research - Order (3) E-commerce Giants]] — B2C-сторона (Amazon/Shopify)
- [[Research - Order (1) Domain-Driven Design]] — теория BC и context map (OMS как orchestration BC)
- [[Research - Order (6) Logistics Integration]] — sourcing rules, ship-from-store, BOPIS
- [[Research - Order (8) Analytics and Operations]] — admin UX в OMS
- [[Backend]] — backend dashboard
- [[Loyality Project]]
