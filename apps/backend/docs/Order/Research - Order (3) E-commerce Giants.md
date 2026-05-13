---
tags:
  - project/loyality
  - backend
  - order
  - benchmarks
  - research
type: research
date: 2026-04-29
aliases: [Order E-commerce Giants, Amazon Shopify Wildberries Order, Marketplace Order Models]
cssclasses: [research]
status: active
parent: "[[Research - Order Architecture]]"
project: "[[Loyality Project]]"
component: backend
---

# Research — Order (3) E-commerce Giants

> Реальные реализации Order Management у крупных платформ: Amazon (SP-API), Shopify (GraphQL Admin), Wildberries, Ozon, AliExpress, Lamoda. Структура Order, FSM статусов, multi-shipment per order, partial cancellation, идемпотентность checkout.

## TL;DR — ключевые выводы

1. **Order ≠ Shipment.** Все крупные платформы (Amazon, Shopify, Wildberries, Ozon, AliExpress) явно разделяют сущность заказа и сущность посылки/отгрузки. Один Order = N Shipments — это норма, а не исключение.
2. **FSM, а не булевы флаги.** Везде используется явная статусная модель с ограниченным набором переходов. Булевы поля типа `is_paid`, `is_shipped` сохраняются только как denormalized projections поверх FSM.
3. **"Pending" — это вестибюль.** Pending/Created/awaiting_approve/new — отдельное "preliminary" состояние, в котором заказ ещё не считается полноценным (нет всех данных, нет резервов, нет финальной цены). Это ключевая инвариантная граница.
4. **Partial cancellation = item-level операция.** На уровне Order её не делают. Отменяют либо отдельные line items / fulfillment orders / postings (Ozon), либо отдельные сборочные задания (Wildberries).
5. **Идемпотентность checkout — обязательна.** Стандарт: `Idempotency-Key` HTTP-заголовок + UUID v4 + хранение результата (status code + body) на 24+ часа + UNIQUE constraint в БД.
6. **Multi-shipment драйверы:** распределённые склады (multi-node fulfillment), частичная нехватка stock, разные carriers, cross-border vs domestic. Реальный split rate — 10–40% от multi-item orders.

---

## 1. Amazon — каноническая reference-модель

### 1.1 Структура Order (SP-API Orders v0)

Amazon Orders API оперирует двумя уровнями:

- **Order (header)** — `AmazonOrderId`, `PurchaseDate`, `OrderStatus`, `OrderTotal`, `MarketplaceId`, `FulfillmentChannel` (AFN / MFN), `ShipmentServiceLevelCategory`, `IsBusinessOrder`, `IsPrime`, `EarliestShipDate`, `LatestShipDate`.
- **OrderItem (line)** — `ASIN`, `SellerSKU`, `OrderItemId`, `QuantityOrdered`, `QuantityShipped`, `ItemPrice`, `ShippingPrice`, `PromotionDiscount`, `ItemTax`, `IsGift`, `BuyerRequestedCancel`, `BuyerCancelReason`.

Главное архитектурное решение: детальная финансовая разбивка (price/tax/promotion) появляется только после выхода из Pending. В Pending заказ — это "намерение", payment ещё не authorized.

### 1.2 FSM статусов Order

```text
Pending ──► Unshipped ──► PartiallyShipped ──► Shipped ──► (terminal)
   │            │                  │              │
   ├──► Canceled ◄─────────────────┴──────────────┘
   │
   └──► Unfulfillable
```

| Статус | Семантика |
|---|---|
| Pending | Order placed, payment NOT authorized. `getOrderItems` возвращает урезанные данные. |
| Unshipped | Payment authorized, ничего не отгружено. |
| PartiallyShipped | Часть items отгружена. Это отдельный first-class статус, а не флаг. |
| Shipped | Все items отгружены. |
| Canceled | Полная отмена. |
| Unfulfillable | Не может быть выполнен (terminal). |
| InvoiceUnconfirmed | Специфично для отдельных marketplaces. |

Terminal states: `Complete`, `CompletePartialled`, `Canceled`, `Unfulfillable`.

### 1.3 Multi-shipment

Amazon на каждый Order может создавать несколько Shipment сущностей (через FBA/MFN). Каждый shipment имеет собственный tracking, carrier, и отдельный набор OrderItems с `QuantityShipped`. Когда отгружено всё — Order переходит в `Shipped`; когда отгружена часть — `PartiallyShipped`.

В FBA добавляется отдельный объект FulfillmentOrder (MCF — Multi-Channel Fulfillment) со своим жизненным циклом: `Received → Planning → Processing → Shipped`. `cancelFulfillmentOrder` валиден только в `Received/Planning` — после `Processing` отмена уже невозможна.

### 1.4 Partial cancellation

Реализован на уровне OrderItem, не Order:

- **Buyer-initiated:** SP-API проставляет `isBuyerRequestedCancel=true` и `buyerCancelReason` на конкретных items.
- **Seller-initiated:** через Order Cancellation Feeds (XML/Flat-file), не напрямую через REST.
- Если ни один item не может быть выполнен — Order переходит в `Canceled`. Если часть — Order остаётся в `Unshipped/PartiallyShipped` с уменьшенными `QuantityOrdered` на отменённых items.

### 1.5 Идемпотентность

- На стороне buyer-facing checkout идемпотентность реализована через client-side cart token + dedup на сервере; deduplication-window огромный.
- На стороне SP-API писем/feeds идемпотентность достигается через `FeedId` — повторная отправка того же feed возвращает тот же result.

---

## 2. Shopify — самая чистая публичная модель

Shopify — золотой стандарт для изучения структуры Order, потому что вся модель публично документирована в GraphQL Admin API.

### 2.1 Структура

Order — центральная сущность, агрегирующая:

- **LineItem** — `quantity`, `variant`, `price`, `discountAllocations`, `taxLines`, `fulfillableQuantity`, `fulfillmentStatus`.
- **FulfillmentOrder** — "запрос на фулфилмент группы items с одной локации". Один Order может иметь N FulfillmentOrder (по одному на каждую участвующую location). Жизненный цикл: `OPEN → IN_PROGRESS → CLOSED/CANCELLED`.
- **Fulfillment** — фактическая отгрузка (создаётся из FulfillmentOrder). Один FulfillmentOrder → N Fulfillment (если отгружают частями).
- **Transaction** — отдельные платежные движения: authorization, capture, sale, void, refund.
- **Refund** — связан с конкретными RefundLineItem.
- **DraftOrder** — pre-order сущность для админ-флоу.

### 2.2 FSM — два независимых state machine

Shopify явно разделяет financial FSM и fulfillment FSM:

**OrderDisplayFinancialStatus:**

```text
PENDING ──► AUTHORIZED ──► PAID ──► PARTIALLY_REFUNDED ──► REFUNDED
              │             │
              └─► VOIDED    └─► PARTIALLY_PAID
```

| Значение | Семантика |
|---|---|
| PENDING | Provider обрабатывает / manual payment |
| AUTHORIZED | Авторизовано, не списано |
| PARTIALLY_PAID | Capture < total |
| PAID | Полностью оплачено |
| PARTIALLY_REFUNDED | Возврат < total |
| REFUNDED | Полный возврат |
| VOIDED | Authorize отменён без capture |
| EXPIRED | Authorization expired |

**OrderDisplayFulfillmentStatus:**

```text
UNFULFILLED ──► IN_PROGRESS / SCHEDULED / ON_HOLD ──► PARTIALLY_FULFILLED ──► FULFILLED
       │                                                        │
       └──► REQUEST_DECLINED ◄──────────────────────────────────┘
                              + RESTOCKED (post-refund)
```

| Значение | Семантика |
|---|---|
| UNFULFILLED | Ничего не отгружено |
| SCHEDULED | Запланирован на будущую дату |
| ON_HOLD | Заморожен (fraud check, payment hold) |
| IN_PROGRESS | Передан в fulfillment service |
| PENDING_FULFILLMENT | Ждёт ответа fulfillment service |
| PARTIALLY_FULFILLED | Часть items отгружена |
| FULFILLED | Всё отгружено |
| REQUEST_DECLINED | Fulfillment service отказал |

Эти два FSM ортогональны — Order может быть `PAID + UNFULFILLED` или `PENDING + PARTIALLY_FULFILLED` (если разрешена отгрузка до полной оплаты).

### 2.3 Multi-shipment

Shopify реализует multi-shipment через FulfillmentOrder:

- Когда Order содержит items с разных locations (warehouse A + warehouse B), Shopify автоматически создаёт по одному FulfillmentOrder на location.
- Каждый FulfillmentOrder может породить несколько Fulfillment (если warehouse отгружает в две посылки).
- Customer-facing Order имеет агрегированный `displayFulfillmentStatus`, но реальные tracking numbers/carriers — на уровне Fulfillment.

### 2.4 Partial cancellation

- На уровне Order: `cancelOrder` с указанием `staffNote` и `restock` boolean.
- На уровне FulfillmentOrder: `fulfillmentOrderCancel` — отменяет конкретный fulfillment leg.
- На уровне line items: `orderEditBegin → orderEditSetQuantity(0) → orderEditCommit` — Order Editing API позволяет обнулить количество отдельных items с автоматическим refund-расчётом.

### 2.5 Идемпотентность checkout

- Shopify Checkout сохраняет `checkout_token` (UUID), который используется как natural idempotency key — повторный submit с тем же token возвращает существующий Order.
- AbandonedCheckout живёт 3 месяца, после чего автоматически удаляется.
- Конверсия abandoned → DraftOrder требует ручного флоу или сторонних апп — нативной идемпотентной "promote to order" операции нет.
- На уровне Storefront API mutation `checkoutCreate` использует `cartId` для дедупликации.

---

## 3. Wildberries — российская реальность с двумя статусными машинами

### 3.1 Архитектура: двойная FSM

Wildberries — единственная из изученных платформ, где статусная модель явно разделена на две машины прямо в API:

- **wbStatus** — статус, контролируемый WB. Селлер не может его менять, только наблюдает.
- **supplierStatus** — статус, контролируемый селлером. WB не может его менять.

Это редкий явный пример "ownership-aware FSM": каждое поле принадлежит одной стороне, и source of truth по статусу всегда однозначен. В sandbox-окружении WB предоставляет ручную возможность эмулировать `wbStatus` для тестирования.

### 3.2 Модели работы и статусы

**FBS (Fulfillment by Seller) — сборочное задание:**

| supplierStatus | Семантика |
|---|---|
| new | Новое задание от покупателя |
| confirm | Селлер начал сборку |
| complete | Собрано, передано в WB / готово к выдаче |
| cancel | Отменено селлером |

| wbStatus (WB-side) | Семантика |
|---|---|
| waiting | Ожидает выкуп складом |
| sorted | WB-склад отсортировал |
| sold | Выкуплено покупателем |
| canceled | Отменено |
| canceled_by_client | Отменено покупателем |
| declined_by_client | Покупатель отменил в первый час (если ещё не confirm) |
| defect | Брак |
| ready_for_pickup | Готово к выдаче в ПВЗ |

Sequence `new → confirm → complete` — обязательная и линейная. WB-склад принимает только `complete`-задания. Дедлайн: 5 дней (120 часов) или автоматическая отмена.

**DBS (Delivery by Seller) — селлер сам везёт покупателю:**

API содержит специальные методы под FSM-переходы:

- Transfer to Assembly (→ confirm)
- Transfer to Delivery (→ deliver)
- Notify That the Order Has Been Accepted by the Buyer (→ receive)
- Notify That the Buyer Has Declined the Order (→ reject)
- Cancel the Order (→ cancel)

Это пример API, в котором каждая FSM-transition явно выражена отдельным endpoint — отсутствует generic "set status" метод. Это резко уменьшает риск неконсистентных переходов.

### 3.3 Multi-shipment

Реализуется через концепцию **Поставка (Supply)** — контейнер, в который селлер кладёт несколько сборочных заданий (assembly orders). Один пользовательский заказ из нескольких товаров может породить несколько сборочных заданий, причём каждое — потенциально отдельная посылка. С ноября 2025 API оптимизирован — до 100 сборочных заданий можно добавить в Supply одним запросом (batch processing).

### 3.4 Partial cancellation

- На уровне отдельного сборочного задания: `cancel` метод.
- На уровне товара внутри задания: не поддерживается — задание неделимо.
- На уровне покупательской отмены: `declined_by_client` доступен только в первый час и до confirm (важная инвариантная граница: после confirm покупатель уже не может отменить, остаётся только полный возврат после получения).

### 3.5 Идемпотентность

WB API не публикует явный Idempotency-Key-механизм. Дедупликация идёт через `orderId/assemblyOrderId` — повторный POST с тем же ID возвращает existing задание. Для batch-операций используется композитный ключ `(supplyId, orderIds[])`.

---

## 4. Ozon — самая богатая FSM из российских

### 4.1 Структура: Posting (отправление) ≠ Order

Ozon принципиально оперирует Posting, а не Order. Posting = "одна логистическая отправка". Один Order пользователя → N Postings.

```text
Order (логический заказ покупателя)
  └── Posting #1 (товары со склада А)
  └── Posting #2 (товары со склада Б)
  └── Posting #3 (товары FBO)
```

Каждый posting имеет:

- `posting_number` (string, e.g. `"0023-0000-1"`)
- `status`, `substatus`
- `products[]` с `quantity`, `price`, `sku`
- `delivery_method`, `tracking_number`
- `cancel_reason_id`, `cancel_reason_message`

### 4.2 FSM статусов posting

```text
acceptance_in_progress ──► awaiting_approve ──► awaiting_packaging
                                  │                    │
                                  ▼                    ▼
                              cancelled ◄──── awaiting_deliver
                                                        │
                                                        ▼
                                                   delivering
                                                        │
                                                        ├──► delivered
                                                        ├──► not_accepted
                                                        └──► cancelled
```

| Статус | Семантика |
|---|---|
| acceptance_in_progress | Идёт регистрация |
| awaiting_approve | Ждёт подтверждения селлера (FBS) |
| awaiting_packaging | Партнёрский склад начал упаковку |
| awaiting_deliver | Упаковано, ждёт передачи перевозчику |
| arbitration | Спор по доставке |
| client_arbitration | Спор клиента |
| delivering | Перевозчик принял, доставляется |
| driver_pickup | У водителя |
| delivered | Доставлено |
| cancelled | Отменено |
| not_accepted | Не принято в ПВЗ |

Substatus добавляет ортогональную ось: например, `delivering + substatus posting_in_carrier_service` vs `posting_at_pickup_point`.

### 4.3 Multi-shipment

Native multi-shipment — это и есть архитектура Ozon. Один customer-facing Order всегда разбивается на postings; даже если у заказа один товар, это будет один posting.

### 4.4 Partial cancellation

- Granularity = posting (не line item, не whole order).
- Endpoint: `/v3/posting/fbs/cancel` с обязательным `cancel_reason_id` (integer) из справочника `/v2/posting/.../cancel-reason/list`.
- Reason имеет `type_id`: `"buyer"` | `"seller"` — кто инициировал.
- Если `cancel_reason_id == 402` ("Other"), требуется `cancel_reason_message` (строка). В остальных случаях — опционально.
- Отдельный line item внутри posting отменить нельзя — нужно cancel всего posting и пересоздание оставшегося.

### 4.5 Идемпотентность

Ozon API использует `Client-Id` + `Api-Key` headers, идемпотентность операций сборки задаётся через `posting_number` как natural key. Cancel-операция идемпотентна по `posting_number` — повторный cancel вернёт текущий статус без побочных эффектов.

---

## 5. AliExpress — cross-border специфика

### 5.1 Структура

AliExpress Open Platform оперирует Trade Order с line items. Особенность: каждая order содержит cross-border метаданные (страна назначения, customs, logistics service).

API: `aliexpress.trade.redefining.findorderbaseinfo`, `aliexpress.solution.order.info.get`.

### 5.2 FSM (упрощённая)

```text
PLACE_ORDER_SUCCESS ──► IN_CANCEL ──► FINISH (cancelled)
       │
       └──► WAIT_BUYER_ACCEPT_GOODS (transit)
              │
              └──► WAIT_SELLER_SEND_GOODS ──► SELLER_PART_SEND_GOODS ──► WAIT_BUYER_ACCEPT_GOODS
                                                       │                          │
                                                       └──► (continue partial)    └──► FUND_PROCESSING ──► FINISH
```

| Статус | Семантика |
|---|---|
| PLACE_ORDER_SUCCESS | Покупатель оплатил, ждёт обработки |
| WAIT_SELLER_SEND_GOODS | Селлер должен отгрузить (полностью) |
| SELLER_PART_SEND_GOODS | First-class статус для частичной отгрузки |
| WAIT_BUYER_ACCEPT_GOODS | Доставлено, ждёт подтверждения покупателя |
| FUND_PROCESSING | Деньги списываются с escrow на счёт селлера |
| IN_CANCEL | Промежуточный — есть spec по отмене |
| FINISH | Terminal: успех или отмена |
| RISK_CONTROL | Заморожено anti-fraud системой |

Ключевое: `SELLER_PART_SEND_GOODS` — это explicit состояние FSM, не computed property. Это упрощает webhook-логику селлера.

### 5.3 Multi-shipment

Поддерживается через `aliexpress.logistics.sellershipmentfortop` с параметром `sendType` (`all` | `part`). При `sendType=part` указывается список SKU из items, что отгружается. После всех part-отгрузок селлер вручную вызывает finalisation.

### 5.4 Partial cancellation

- Покупатель может открыть dispute на отдельные items (refund-only / refund-and-return).
- Selle-side cancel — только всего ордера, до отгрузки.
- После `SELLER_PART_SEND_GOODS` отмена идёт через dispute-резолюшн, не через cancel API.

### 5.5 Идемпотентность

AliExpress использует `out_order_no` (внешний ID селлера) как natural idempotency key для placement операций. Для shipment-операций ключ — `(orderId, sku, batchNo)`.

---

## 6. Lamoda — закрытая модель, что известно публично

Lamoda публикует REST API в `api.sellercenter.lamoda.ru/docs/` и B2B PHP SDK на GitHub (`lamoda/lamoda-b2b-platform.php-sdk`).

### 6.1 Структура

Endpoints верхнего уровня:

- `/auth/token` — OAuth2 client_credentials
- `/api/v1/orders` — order resource
- `/api/v1/shipments/out` — outbound shipments

Это явно отдельная сущность Shipment, не объединённая с Order — то есть multi-shipment поддерживается на уровне модели.

### 6.2 FSM (по косвенным данным)

Из публичных интеграций (ChannelEngine, AfterShip) известны статусы:

```text
pending → confirmed → packed → ready_for_shipment → shipped → in_transit → delivered → returned / canceled
```

Полная FSM не опубликована публично — закрытая часть SellerCenter docs.

### 6.3 Идемпотентность

Через `client_id` / `client_secret` + business key `seller_order_id` (natural key из системы селлера).

---

## 7. Идемпотентность checkout — сводный pattern

### 7.1 Стандартная схема (Stripe, Shopify, банковские эквайринги)

1. Client генерирует UUID v4 → `idempotency_key`
2. Client отправляет POST с заголовком: `Idempotency-Key: <uuid>`
3. Server:
   - SELECT response WHERE key = uuid
   - Если найден → вернуть сохранённый (status_code, body), НЕ выполнять операцию
   - Если не найден:
     - Захватить lock (SET NX в Redis или INSERT с UNIQUE constraint в БД)
     - Если lock не захвачен → конкурентный запрос → poll/wait и вернуть его результат
     - Иначе: выполнить операцию, сохранить (key, status, body) и вернуть
4. TTL ключа: ≥ 24h

### 7.2 Stripe-specific детали

- `Idempotency-Key` header, до 255 символов.
- Сохраняется и успех, и ошибка — повторный запрос с тем же ключом вернёт ту же ошибку (включая 500).
- Через 24h ключ expires; повторное использование = новая операция.
- **Anti-pattern:** использовать business identifiers (orderId, userId, email) — они мутабельны и conflate identity с intent.
- **Best practice:** ключ структурируется как `{client_id}:{operation}:{intent_uuid}`.

### 7.3 Shopify-specific

- `checkout_token` как natural key.
- На уровне Storefront `cartId` дедуплицирует cart-операции.
- На Order create — никакого client-side ключа: идемпотентность на checkout-токене.

### 7.4 Wildberries / Ozon

- Нет explicit Idempotency-Key.
- Дедупликация через natural keys (`postingNumber`, `assemblyOrderId`).
- **Минус:** клиент сам должен генерировать stable internal IDs для batch-операций.

### 7.5 Чек-лист реализации идемпотентного checkout

- [ ] UUID v4 (никогда не business ID) генерируется на клиенте до отправки.
- [ ] Заголовок `Idempotency-Key` или эквивалент.
- [ ] UNIQUE constraint в БД на колонке `idempotency_key`.
- [ ] Захват lock до дорогих операций (charge, inventory reserve).
- [ ] Persistence результата (status + body) для replay.
- [ ] TTL ≥ 24h.
- [ ] Для long-running операций — отдельный operation-status endpoint, чтобы при retry клиент мог получить текущий статус, а не ждать таймаут.
- [ ] Differentiate 409 Conflict (тот же ключ, другие параметры — likely bug) vs 200 OK (тот же ключ, те же параметры — replay).

---

## 8. Multi-shipment per order — паттерны и trade-offs

### 8.1 Драйверы split shipment

| Драйвер | Пример |
|---|---|
| Multi-node fulfillment | Item A на складе SF, Item B на складе NY |
| Stock unavailability | Часть items in-stock, часть нужно реcток |
| Carrier limits | Объём/вес превышает лимит одной посылки |
| Cross-border | Часть товаров cleared customs, часть нет |
| Different lead times | Pre-order item + ready item |
| Fulfillment channels | FBO + FBS в Ozon, AFN + MFN в Amazon |

Реальный split rate в ритейле: 10–40% от multi-item orders.

### 8.2 Архитектурные паттерны

**Pattern A: Nested aggregates (Shopify)**

```text
Order
  └── FulfillmentOrder[] (по location)
        └── Fulfillment[] (фактические отгрузки)
```

Плюс: чёткая иерархия, customer видит единый Order. Минус: сложная логика агрегированного статуса.

**Pattern B: Posting-first (Ozon)**

```text
Order (виртуальный)
  └── Posting[] (каждый — независимая FSM)
```

Плюс: каждый posting — autonomous; проще horizontal scale. Минус: агрегированный customer view нужно строить отдельно.

**Pattern C: Order + Shipment 1:N (Amazon, Lamoda)**

```text
Order ──[1:N]── Shipment ──[N:M]── OrderItem
```

Плюс: сбалансированно. Минус: нужны явные denorm-поля типа `PartiallyShipped`.

### 8.3 Tracking integration

Универсальная проблема: customer ждёт один tracking link, реальность — N tracking IDs от разных carriers. Решения:

- **Unified tracking page** (Shopify/order status page агрегирует все Fulfillment)
- **Notification per shipment** (Amazon "Item shipped" emails — отдельно по каждому)
- **Customer choice at checkout:** "доставить одной посылкой (медленнее)" vs "доставить частями (быстрее)" — снижает post-sale поддержку.

---

## 9. Partial cancellation — granularity matrix

| Платформа | Granularity отмены | API метод |
|---|---|---|
| Amazon | OrderItem (по факту через quantity reduction) | Order Cancellation Feed + buyer flag `isBuyerRequestedCancel` |
| Shopify | LineItem через Order Editing API | `orderEditBegin → orderEditSetQuantity(0) → orderEditCommit` |
| Wildberries | Сборочное задание (`assemblyOrderId`) | cancel endpoint, item-level не поддерживается |
| Ozon | Posting | `/v3/posting/fbs/cancel` с `cancel_reason_id` |
| AliExpress | Whole order до отгрузки; после — dispute-flow | `aliexpress.trade.cancel.order` + dispute API |
| Lamoda | Order или Shipment (по docs) | `/api/v1/shipments/out/{id}/cancel` (косвенно) |

### 9.1 Compensation patterns

При partial cancellation должны выполниться компенсирующие действия:

1. **Inventory release** — вернуть отменённые units в stock.
2. **Payment refund/void** — частичный refund (если capture был) или partial void (если только authorize).
3. **Loyalty/promotion recalc** — пересчёт скидок (например, "купи 3 — получи 4" при отмене 1 ломает offer).
4. **Tax recalc** — пересчёт налогов на оставшиеся items.
5. **Shipping recalc** — может измениться класс доставки/free-shipping threshold.

Это классический Saga compensation use case. У Shopify Order Editing API всё это hidden; у Wildberries/Ozon — на стороне клиента.

---

## 10. Сравнительная таблица архитектурных решений

| Аспект | Amazon | Shopify | Wildberries | Ozon | AliExpress | Lamoda |
|---|---|---|---|---|---|---|
| Order/Shipment split | Order + Shipment | Order + FulfillmentOrder + Fulfillment | AssemblyOrder + Supply | Posting-first | Order + Logistics | Order + Shipment |
| FSM явная | ✔ Один FSM | ✔ Два независимых FSM (financial + fulfillment) | ✔ Два FSM по ownership (wbStatus + supplierStatus) | ✔ Один + substatus | ✔ Один | Закрыто |
| PartiallyShipped как статус | ✔ | ✔ PARTIALLY_FULFILLED | На уровне Supply | На уровне Order агрегации | ✔ SELLER_PART_SEND_GOODS | ? |
| Partial cancel granularity | OrderItem | LineItem (Order Editing) | AssemblyOrder | Posting | Order/dispute | Shipment |
| Idempotency mechanism | FeedId, natural keys | checkout_token, cartId | natural keys (no header) | natural keys (no header) | out_order_no | client_credentials + natural key |
| Cancel deadline | До Shipped | До Fulfilled | 1 час для buyer / 5 дней для seller-no-action | До delivering | До WAIT_SELLER_SEND_GOODS | До отгрузки |
| Cancel reason taxonomy | Free-text + buyer flag | staffNote | Системные коды | Справочник `cancel_reason_id` | Системные коды | ? |

---

## 11. Выводы и рекомендации для своей системы

### 11.1 Что брать как baseline

1. **Двухуровневая FSM** (Shopify-style): financial state и fulfillment state — независимые. Don't conflate.
2. **Order + Shipment как разные aggregates:** даже если сейчас "1 order = 1 shipment", не ломайте инкапсуляцию — будет легче добавить multi-shipment позже.
3. **Pending как explicit gate:** до перехода в Confirmed/Authorized заказ не должен блокировать stock и не должен иметь финальной цены.
4. **Idempotency-Key header (Stripe-style):** UUID v4 + Redis SET NX + 24h TTL + сохранение полного response.
5. **Cancel reason как справочник** (Ozon-style): не free-text, а enum + опциональный details. Это критично для analytics (тема 8 в roadmap).
6. **Партишн отмен по item, а не по order** (Amazon/Shopify-style) — Wildberries-style "отмена только всего задания" — это compromise при сильном fulfillment-coupling, не делайте так если не вынуждены.

### 11.2 Антипаттерны, которых стоит избегать

- ❌ Булевы поля `is_paid`, `is_shipped`, `is_cancelled` без FSM — приводят к невалидным комбинациям (`is_cancelled=true && is_shipped=true`).
- ❌ Использование `order_id` как idempotency key — ID ещё не существует на момент первого запроса.
- ❌ Single-FSM, смешивающая payment и fulfillment — невозможно выразить "оплачено, но fulfillment отменён".
- ❌ Generic `setStatus(newStatus)` endpoint — открытый mutation не валидирует transitions.
- ❌ Multi-shipment как retrofitted feature — разделите модель сразу.

### 11.3 Open questions для следующих research-тем

- Как именно устроены Saga в checkout (тема 5 — будет рассмотрено).
- Каковы реальные latency-budgets каждого FSM-перехода (не публикуется).
- Как авторитетные OMS (IBM Sterling, Manhattan, Salesforce OMS) формализуют FSM (тема 2).

---

## 12. Источники

### Amazon / SP-API

- Selling Partner API for Orders v0
- Cancel and change orders — Amazon SP-API
- Changes to Orders API for buyer cancellation requests
- Cancel a fulfillment order — MCF
- Guidance for Distributed Order Management on AWS
- Amazon SP-API: Get Orders with Python
- Mastering Amazon Cancelled Orders — Openbridge

### Shopify

- Shopify Order — GraphQL Admin
- FulfillmentOrder — GraphQL Admin
- Fulfillment — GraphQL Admin
- OrderDisplayFinancialStatus enum
- OrderDisplayFulfillmentStatus enum
- Shopify Help — Understanding your order statuses
- AbandonedCheckout — GraphQL Admin

### Wildberries

- WB API — FBS Assembly Orders
- WB API — DBS Orders
- WB API documentation main
- Seller API Marketplace
- WB API Updates Digest November 2025

### Ozon

- Ozon Help — How to Work with API
- Ozon Help — Order Management
- Ozon Help — Working with Orders FBP
- Ozon Help — Cancellation by seller
- OZON Seller API Documentation

### AliExpress

- AliExpress Open Platform — API Reference
- aliexpress.solution.order.info.get
- Aliexpress Open Platform API Instructions
- How to Fulfill Orders via the AliExpress API — Ali2Woo

### Lamoda

- Lamoda SellerCenter REST API Documentation
- Lamoda B2B Platform PHP SDK — GitHub
- LAMODA marketplace guide — ChannelEngine
- Lamoda Tech — GitHub org

### Идемпотентность

- Stripe — Designing robust APIs with idempotency
- Stripe — Idempotent requests API reference
- Stripe — Payment Intents API
- How Stripe Prevents Double Payment Using Idempotent API
- Idempotency in Distributed Systems — Algomaster
- Idempotency Design Patterns Beyond 'Retry Safely'

### Multi-shipment & Split shipment

- Split-Shipment Strategies for E-commerce Logistics — gettransport
- What is a Split Shipment — ShipBob
- Effective Order Splitting — VESYL
- Multi-shipment examples — Optimizely Commerce
- Unified Tracking for Split or Multi-Shipment Orders — wesupplylabs

### FSM & Saga Pattern

- Microservices Pattern: Saga — microservices.io
- State Machine Saga Design Pattern — Speaker Deck
- Building a FSM from Scratch using DDD — SSENSE-TECH
- How we used SAGA and State Machine for distributed transactions
- Solidus State Machines guide

---

## Related

- [[Research - Order Architecture]] — индекс серии Order
- [[Research - Order (1) Domain-Driven Design]] — теоретическая база разделения Order/Shipment/Payment
- [[Research - Order (2) State Machine FSM]] — общая теория FSM для Order
- [[Research - Order (4) OMS Platforms]] — enterprise-OMS (B2B-эталон)
- [[Research - Order (6) Logistics Integration]] — multi-shipment в практике
- [[Research - Order (7) Saga Pattern]] — orchestration в крупных платформах
- [[Research - Cart Architecture (2) Crossborder Marketplace Patterns]] — Wildberries/Ozon для cart
- [[Backend]] — backend dashboard
- [[Loyality Project]]
