---
tags:
  - project/loyality
  - backend
  - order
  - ddd
  - research
type: research
date: 2026-04-29
aliases: [Order DDD, Order Aggregates, Bounded Contexts]
cssclasses: [research]
status: active
parent: "[[Research - Order Architecture]]"
project: "[[Loyality Project]]"
component: backend
---

# Research — Order (1) Domain-Driven Design

> DDD для e-commerce Order: агрегаты, bounded contexts, value objects, domain events и отношения с Cart / Payment / Shipment / Inventory. Опора на Eric Evans (Blue Book), Vaughn Vernon (Red Book), Martin Fowler, Chris Richardson, Greg Young.

## TL;DR — ключевые выводы

1. Order — aggregate root, OrderLine — child entity внутри Ordering BC. Это каноничный пример из всех учебников DDD.
2. Cart, Order, Payment, Shipment, Inventory — РАЗНЫЕ bounded contexts. Один Order-aggregate не должен включать Payment и Shipment как child entities — это violation Vernon's "small aggregates" rule.
3. Vernon's 4 правила агрегатов: (1) model true invariants in consistency boundaries, (2) design small aggregates, (3) reference other aggregates by identity, (4) use eventual consistency outside the boundary.
4. Одна транзакция = один агрегат. Save one Order per transaction, не Order + Payment + Inventory. Cross-aggregate consistency — через domain events / sagas.
5. Money, Address, Email, Quantity — value objects, не string/decimal. Это ubiquitous language в коде.
6. Domain Events ≠ Saga ≠ Process Manager. Event — fact happened. Saga — sequence of local transactions с компенсациями. Process Manager — stateful orchestrator, который держит state machine workflow'a.
7. Choreography vs Orchestration: choreography для loose-coupled flows (events), orchestration для complex stateful workflows (process manager). Большие системы используют оба.

---

## 1. Базовые понятия DDD — ubiquitous language

### 1.1 Стратегические vs тактические паттерны

**Стратегические (большой масштаб):**

- **Bounded Context** — логическая граница, внутри которой модель имеет одно значение слов.
- **Ubiquitous Language** — общий язык внутри одного BC между разработчиками и domain experts.
- **Context Map** — диаграмма отношений между BC.
- **Subdomain** — Core / Supporting / Generic.

**Тактические (внутри BC):**

- **Entity** — объект с идентичностью.
- **Value Object** — иммутабельный объект без идентичности.
- **Aggregate** — кластер связанных сущностей с одним root.
- **Aggregate Root** — единственная "точка входа" в aggregate.
- **Domain Service** — операция, не принадлежащая одной сущности.
- **Repository** — абстракция персистентности агрегата.
- **Domain Event** — что-то значимое произошло в домене.
- **Factory** — создание сложных агрегатов.

### 1.2 Ubiquitous Language — почему это важно для Order

> "Within a bounded context, everyone — developers, product managers, domain experts — uses the same terms to mean the same things." — Martin Fowler

Конкретный пример из e-commerce: слово **Order** означает разное в разных BC.

| Bounded Context | Что значит "Order" |
|---|---|
| Ordering BC | Намерение покупателя купить (с pricing, customer, items) |
| Shipping BC | Физическая отправка (parcel, carrier, tracking, weight) |
| Billing BC | Финансовая транзакция (invoice, AR, revenue recognition) |
| Inventory BC | Reservation/allocation товара со склада |
| Customer Service BC | Case / interaction / RMA history |

Это не омоним — это разные модели одной концепции, и именно поэтому BC нужны. Пытаться заставить один Order-класс работать во всех контекстах — путь к "Big Ball of Mud".

---

## 2. Order как Aggregate Root — каноничный пример

### 2.1 Структура Ordering aggregate

```text
┌────────────────────── Ordering BC ───────────────────────┐
│                                                          │
│  ┌─────────────────── Order (aggregate root) ────────┐   │
│  │  - id: OrderId (Value Object)                    │   │
│  │  - customerId: CustomerId (id reference!)        │   │
│  │  - status: OrderStatus (enum/state)              │   │
│  │  - placedAt: Timestamp                           │   │
│  │  - shippingAddress: Address (Value Object)       │   │
│  │  - billingAddress: Address (Value Object)        │   │
│  │  - currency: Currency (Value Object)             │   │
│  │  - lines: List<OrderLine>  ◄───── child entities │   │
│  │  - totals: OrderTotals (Value Object)            │   │
│  │                                                  │   │
│  │  + place()                                       │   │
│  │  + addLine(productId, quantity, unitPrice)       │   │
│  │  + removeLine(lineId)                            │   │
│  │  + updateLineQuantity(lineId, quantity)          │   │
│  │  + applyDiscount(promoCode)                      │   │
│  │  + cancel(reason)                                │   │
│  │  + recalculateTotals()                           │   │
│  └──────────────────────────────────────────────────┘   │
│           │                                             │
│           │ owns                                        │
│           ▼                                             │
│  ┌─────────── OrderLine (child entity) ────────────┐   │
│  │  - id: OrderLineId                              │   │
│  │  - productId: ProductId (id reference)          │   │
│  │  - sku: SKU (Value Object)                      │   │
│  │  - quantity: Quantity (Value Object)            │   │
│  │  - unitPrice: Money (Value Object)              │   │
│  │  - discount: Money                              │   │
│  │  - lineTotal: Money                             │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────── Value Objects ─────────────────┐    │
│  │  Money(amount, currency), Address, Email,     │    │
│  │  Quantity, OrderId, SKU, OrderTotals          │    │
│  └───────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Почему Order — aggregate root

Order satisfies все критерии root:

- **Invariant scope:** изменение количества line item должно пересчитать total — invariant `total = sum(line.lineTotal)`.
- **External access point:** внешний код не может напрямую модифицировать `OrderLine` — только через `Order.updateLineQuantity()`.
- **Identity propagation:** `OrderLine` уникален только в контексте Order.
- **Lifecycle ownership:** `OrderLine` создаётся и удаляется через Order.

### 2.3 Почему OrderLine — entity, не value object

OrderLine имеет идентичность в пределах Order:

- Один и тот же продукт может появиться двумя строками (разные размеры, разные цены, разные промо).
- Удаление одной строки не ломает другие.
- Может меняться (quantity update) — а value objects immutable.

В то же время Money, Quantity, SKU — value objects, потому что `$10.00 USD == $10.00 USD` — две равные, неотличимые величины.

### 2.4 Vernon's правила, применённые к Order

| Правило | Как применяется к Order |
|---|---|
| R1: Model true invariants | Order total всегда == sum of line totals. Quantity > 0. Discount ≤ subtotal. |
| R2: Design small aggregates | Order не включает Customer entity, Payment entity, Shipment entity — только id-references. |
| R3: Reference by identity | `customerId: CustomerId`, `productId: ProductId` — не сами объекты. |
| R4: Eventual consistency outside | Order published `OrderPlaced` event; Inventory eventually reserves stock. |

### 2.5 Anti-pattern: God Order

```text
❌ ANTI-PATTERN
Order {
    lines: List<OrderLine>
    customer: Customer       ← полный entity, не reference
    payments: List<Payment>  ← payment как child
    shipments: List<Shipment> ← shipment как child
    invoices: List<Invoice>  ← invoice как child
    auditTrail: List<AuditEntry>
}
```

Проблемы:

1. **Размер транзакции:** одна модификация требует locking всего объёма.
2. **Concurrency:** два изменения шипмента и платежа конфликтуют, хотя логически независимы.
3. **Lifecycle mismatch:** Order создаётся раз, Shipments создаются N раз позже, Payment может быть refunded годом позже.
4. **Performance:** загрузка Order требует загрузки всего графа.
5. **Невозможность scale per BC:** все эти entities должны жить в одной БД.

Правильное решение: разные aggregates в разных BC, связанные через id-references и domain events.

---

## 3. Bounded Contexts для e-commerce — typical decomposition

### 3.1 Каноничный context map

```text
                ┌──────────────┐
                │ Catalog BC   │
                │ (Product,    │
                │  SKU, Price) │
                └──────┬───────┘
                       │ supplies
                       ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Cart BC     │───►│ Ordering BC  │───►│ Payment BC   │
│  (Cart,      │    │ (Order,      │    │ (Payment,    │
│   Item)      │    │  OrderLine)  │    │  Refund)     │
└──────────────┘    └──────┬───────┘    └──────────────┘
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
   │ Inventory BC │ │ Shipping BC  │ │ Customer BC  │
   │ (Stock,      │ │ (Shipment,   │ │ (Customer,   │
   │  Reservation)│ │  Parcel)     │ │  Account)    │
   └──────────────┘ └──────────────┘ └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ Returns BC   │
                    │ (RMA,        │
                    │  Return)     │
                    └──────────────┘
```

### 3.2 Контексты — детальная разбивка

#### 3.2.1 Cart BC

- **Aggregate:** Cart (root) → CartItem[]
- **Value Objects:** CartId, Quantity, PromoCode
- **Behavior:** add/remove items, apply promo, save for later, abandoned cart detection
- **Lifecycle:** ephemeral, может умереть через 30 дней
- **Persistence:** часто Redis/in-memory — не нужна полная транзакционная гарантия

Ключевая идея: Cart — это draft order. Содержит items без обязательств. Нет резерва inventory, нет окончательных цен (могут пересчитаться), нет shipping calculation.

#### 3.2.2 Ordering BC

- **Aggregate:** Order (root) → OrderLine[]
- **Value Objects:** OrderId, Money, Address, OrderStatus
- **Behavior:** place order, cancel, modify, recalculate totals, FSM transitions
- **Lifecycle:** месяцы (для returns) до years (для analytics)
- **Persistence:** строго ACID, обычно SQL

#### 3.2.3 Payment BC

- **Aggregates:** Payment (root) с Authorization, Capture, Refund как child entities
- **Value Objects:** Money, IdempotencyKey, PaymentMethod
- **Behavior:** authorize, capture, void, refund, retry, 3DS challenge
- **External integration:** PSP (Stripe/Adyen) через ACL

#### 3.2.4 Inventory BC

- **Aggregates:** StockItem per (sku, location) — мелкий, для high concurrency
- **Value Objects:** Sku, LocationId, QuantityOnHand, Reservation
- **Behavior:** reserve, release, decrement on ship, increment on return
- **Crucial:** small aggregate per SKU+location — позволяет parallel reservations

#### 3.2.5 Shipping BC

- **Aggregates:** Shipment (root) → Parcel, TrackingEvent
- **Value Objects:** Carrier, TrackingNumber, Weight, Dimensions
- **Behavior:** create shipment, generate label, update tracking, mark delivered

#### 3.2.6 Returns BC

- **Aggregates:** RMA (root) → ReturnLine
- **Value Objects:** RMAId, Reason, Disposition
- **Behavior:** authorize return, receive, inspect, dispatch refund

### 3.3 Context map relationships

| Связь | Тип | Пример |
|---|---|---|
| Cart → Ordering | Customer-Supplier + Anti-Corruption Layer | Cart "promotes" в Order через event/command |
| Ordering → Payment | Customer-Supplier | Order запрашивает Payment для charge |
| Ordering → Inventory | Customer-Supplier | Order резервирует stock |
| Ordering → Shipping | Customer-Supplier | Order создаёт Shipment(s) |
| Catalog → Ordering | Conformist или Open Host Service | Ordering принимает Product как есть, через snapshot |
| External PSP → Payment | Anti-Corruption Layer | Stripe-specific модель не проникает внутрь Payment |

### 3.4 Эрик Эванс о множественных значениях слова

> "In the Ordering context, the word 'Order' refers to the customer's request for products and payment, while in the Shipping context, 'Order' might mean a physical package ready to be dispatched."

Это тот самый случай, ради которого Evans придумал Bounded Context. Не пытайтесь уравнять модели — это создаст плохую абстракцию.

---

## 4. Cargo Shipping — каноничный пример Эванса

### 4.1 О чём пример

В Blue Book Эванс использует cargo shipping domain как сквозной пример. DDD Sample Application (dddsample.sourceforge.net) — running implementation, совместная работа Domain Language (компания Эванса) и Citerus.

### 4.2 Aggregates в Cargo Shipping

| Aggregate | Покрытие |
|---|---|
| Cargo | Booking создание, изменение destination, route assignment, registration of handling events |
| HandlingEvent | Размещён в отдельном агрегате, чтобы избежать deadlocks при обработке быстрых событий |
| Voyage | Маршрут судна |
| Location | Порт |

### 4.3 Урок: HandlingEvent — отдельный aggregate

Эванс намеренно вынес HandlingEvent из Cargo aggregate, хотя по моделированию они тесно связаны. Причина:

- HandlingEvents приходят высоким темпом (порт обрабатывает тысячи в час).
- Если HandlingEvent внутри Cargo aggregate — каждое событие требует locking всего Cargo.
- Отделение позволяет parallel processing без блокировок.

Прямой аналог в e-commerce: TrackingEvent от carrier должен быть отдельным aggregate от Shipment, не его child entity. Тысячи tracking webhook'ов в минуту требуют независимой обработки.

### 4.4 Замечание Эванса о sample app

Эванс изначально хотел сделать пример с двумя BC (cargo shipping + carrier movement / billing) для демонстрации context mapping, но в итоге опубликован один BC. Это сам Эванс называет ограничением учебного примера.

---

## 5. Vernon's "Effective Aggregate Design" — 4 правила в деталях

Vaughn Vernon в трёх частях статей (2011, dddcommunity.org) и в Red Book формулирует 4 правила:

### 5.1 Rule 1: Model True Invariants in Consistency Boundaries

> "An invariant is a business rule that must always be consistent. A properly designed Aggregate can be modified in any way required by the business with its invariants completely consistent within a single transaction."

Применение к Order:

- **Invariant:** `Order.total == sum(line.lineTotal for line in lines)`. Это истинный invariant — после любой операции должно быть true.
- **Invariant:** `OrderLine.quantity > 0`. Если 0 — line должен быть удалён.
- **Invariant:** `Order.status in valid_transitions(previous_status)`. FSM enforced внутри aggregate.

НЕ-invariants (то, что не должно быть в Order aggregate):

- "Inventory должно покрывать заказ" — это invariant Inventory BC, не Order.
- "Payment должен быть успешным" — invariant Payment BC.

### 5.2 Rule 2: Design Small Aggregates

> "A large-cluster Aggregate will never perform or scale well and is more likely to become a nightmare leading only to failure."

Vernon's эмпирика: 70% агрегатов = только Root + value objects. 30% = 2-3 entities.

Применение: `Order = root + List + value objects`. Не помещайте в Order'е Customer-entity, Payment-entity, Shipment-entity, History-entity.

### 5.3 Rule 3: Reference Other Aggregates by Identity

> "One Aggregate may hold references to the Root of other Aggregates, but this does not place the referenced Aggregate inside the consistency boundary."

```text
✔ ПРАВИЛЬНО:                ❌ НЕПРАВИЛЬНО:
Order {                     Order {
  customerId: CustomerId       customer: Customer  // полный entity
  productIds: ProductId[]      products: Product[] // полные entities
}                           }
```

Зачем:

- Меньше memory footprint.
- Aggregate boundaries чёткие.
- Eventual consistency outside boundary возможна (Customer может быть updated параллельно).
- Тесты проще — не нужно строить полный граф.

### 5.4 Rule 4: Use Eventual Consistency Outside the Boundary

> "Any rule that spans Aggregates will not be expected to be up-to-date at all times."

Если `Order.place()` должен также zarezервировать inventory:

- ❌ Внутри одной транзакции lock'нуть Order и InventoryItem.
- ✔ Order publishes `OrderPlaced` event → Inventory subscribes → Inventory reserves в своей транзакции.

Цена: между этими событиями — небольшое окно несогласованности (может быть пара миллисекунд, может быть — секунды). Это acceptable для большинства e-commerce операций. Compensating transaction (cancel order, если inventory fail) — стандартная Saga.

---

## 6. Value Objects — как обогатить ubiquitous language

### 6.1 Anti-pattern: primitive obsession

```text
❌ Order {
    totalAmount: BigDecimal
    currency: String
    customerEmail: String
    shippingStreet: String
    shippingCity: String
    shippingZip: String
}
```

Проблемы:

- Можно сложить два totalAmount в разных currency.
- Email без валидации, может быть "asdf".
- Address раскинут по 5 полям без cohesion.

### 6.2 С Value Objects

```kotlin
✔ Order {
    total: Money              // {amount, currency} с валидацией
    customerEmail: Email      // валидируется в конструкторе
    shippingAddress: Address  // immutable, validates internally
}

class Money {
    val amount: BigDecimal
    val currency: Currency

    operator fun plus(other: Money): Money {
        require(this.currency == other.currency)
        return Money(amount + other.amount, currency)
    }
}
```

### 6.3 Типичные Value Objects в Order domain

| VO | Назначение |
|---|---|
| OrderId | Strongly-typed id, не путается с CustomerId |
| Money(amount, currency) | Денежная сумма с currency-safe арифметикой |
| Quantity(value, unit) | Не путается с другими integer |
| Address | Immutable, validates на конструкторе |
| Email | Валидируется regex'ом, не string |
| PhoneNumber | E.164-formatted |
| SKU | Unique product identifier |
| Discount(percent OR amount) | Discriminated union |
| OrderStatus | Enum + valid transitions FSM |
| PromoCode | Не string |
| TaxRate | Percent с округлением политикой |
| IdempotencyKey | UUID v4 |

### 6.4 Money — самый важный VO

Из всех VOs Money — must-have в любой системе с деньгами. Минимальные операции:

- `+`, `-`, `*` (на skalar, не на Money)
- `compareTo` с currency check
- `convert(targetCurrency, rate)`
- `round(precision, mode)` — banking rounding rules
- Никогда `*` на другую Money — это бессмысленно.

Использование `BigDecimal` для денег — пол-решения. Money — полное решение.

---

## 7. Domain Events — что произошло в домене

### 7.1 Определение

> "Domain Events are messages that capture something important that happened in the domain."

Признаки domain event:

- **Past tense** — `OrderPlaced`, `PaymentCaptured`, `ShipmentDispatched`. Не `PlaceOrder` (это command).
- **Immutable** — нельзя изменить факт постфактум.
- **Self-contained** — несёт всю необходимую информацию для подписчиков.
- **Domain-meaningful** — на ubiquitous language, не technical (`RowInserted`).

### 7.2 Примеры событий в Order lifecycle

```text
CartCheckoutStarted          (Cart BC → Ordering BC)
OrderPlaced                  (Ordering BC)
OrderLineAdded               (Ordering BC, internal)
StockReserved                (Inventory BC)
StockReservationFailed       (Inventory BC) — triggers compensation
PaymentAuthorized            (Payment BC)
PaymentCaptureFailed         (Payment BC) — triggers compensation
OrderConfirmed               (Ordering BC) — после payment + inventory ok
ShipmentCreated              (Shipping BC)
ShipmentDispatched           (Shipping BC)
ShipmentDelivered            (Shipping BC)
OrderFulfilled               (Ordering BC)
ReturnRequested              (Returns BC)
RefundIssued                 (Payment BC)
OrderClosed                  (Ordering BC) — terminal
```

### 7.3 Internal vs Integration events

- **Internal domain events** — публикуются внутри одного BC, для координации aggregates внутри.
- **Integration events** — публикуются между BC, через message broker.

Часто эти разделяют: `OrderPlaced` (internal — слышит только Ordering BC) vs `OrderPlacedIntegrationEvent` (на bus, упрощённая schema, контракт между BC).

### 7.4 Domain Events vs CRUD Events

- ❌ **CRUD-style:** `OrderUpdated { id, fields: {...} }` — без бизнес-смысла.
- ✔ **Domain-style:** `OrderShippingAddressChanged`, `OrderItemQuantityIncreased`, `OrderCancelled`. Каждое событие — конкретное бизнес-действие.

---

## 8. Sagas — distributed transactions для checkout

### 8.1 Проблема

Checkout затрагивает несколько BC: Order create, Inventory reserve, Payment capture, Shipment create. Они в разных БД (Vernon's small aggregates). 2PC не работает на cloud-scale. Решение: Saga — sequence of local transactions с compensations.

### 8.2 Choreography vs Orchestration

#### 8.2.1 Choreography (event-driven)

Каждый сервис реагирует на события:

```text
OrderService:
  receive PlaceOrder command
  create Order (status = PENDING)
  publish OrderPlaced

InventoryService:
  subscribe OrderPlaced
  try reserve stock
  publish StockReserved or StockReservationFailed

PaymentService:
  subscribe StockReserved
  try authorize + capture
  publish PaymentCaptured or PaymentFailed

OrderService:
  subscribe PaymentCaptured → mark Order CONFIRMED
  subscribe PaymentFailed → mark Order CANCELLED, publish OrderCancelled

InventoryService:
  subscribe OrderCancelled → release reservation (compensation)
```

**Плюсы:** loose coupling, нет single point of failure orchestrator'a.
**Минусы:** workflow логика разбросана по сервисам — трудно увидеть "общую картину". Никто не знает, что workflow застрял.

#### 8.2.2 Orchestration (process manager / saga orchestrator)

Один центральный orchestrator знает всю последовательность:

```text
CheckoutOrchestrator (state machine):
  state CREATING_ORDER:
    send CreateOrder command → OrderService
    on OrderCreated → state RESERVING_STOCK
    on OrderCreationFailed → state FAILED

  state RESERVING_STOCK:
    send ReserveStock command → InventoryService
    on StockReserved → state CHARGING_PAYMENT
    on StockReservationFailed → send CancelOrder, state FAILED

  state CHARGING_PAYMENT:
    send Charge command → PaymentService
    on PaymentCaptured → state CONFIRMING_ORDER
    on PaymentFailed → send ReleaseStock, send CancelOrder, state FAILED

  state CONFIRMING_ORDER:
    send ConfirmOrder → OrderService
    on OrderConfirmed → state COMPLETED
```

**Плюсы:** одно место для понимания workflow, легко debug, легко добавить timeout/retry.
**Минусы:** orchestrator — single point of failure (mitigates через replication), tighter coupling.

### 8.3 Saga vs Process Manager — разница

Часто эти термины смешивают. Точное определение:

| Концепция | Что это |
|---|---|
| Saga (pure) | Sequence of local transactions с compensations. Может быть stateless choreography. |
| Process Manager | Stateful orchestrator с собственной FSM, координирующий workflow. |
| Saga Orchestrator | Реализация Saga через Process Manager. |

> "The Saga itself has no state. A Process Manager can be modelled as a state machine. It makes decisions based not only on incoming events but also the current state of the process."

В большинстве реальных систем под "Saga" имеют в виду Saga Orchestrator = Process Manager.

### 8.4 Outbox pattern — обязательная пара к Sagas

Проблема: как atomically (1) сохранить state в БД и (2) опубликовать event в message broker?

Решение Transactional Outbox:

1. В рамках одной DB-транзакции пишем agregate state и event в outbox таблицу.
2. Отдельный worker читает outbox и публикует в broker.
3. После успешной публикации — mark as published.

Это гарантия at-least-once delivery. Подписчики должны быть idempotent.

Парная Inbox pattern — на стороне consumer'a: dedup по event_id.

### 8.5 Когда choreography, когда orchestration

| Сценарий | Pattern |
|---|---|
| 2-3 шага, простая последовательность | Choreography |
| 5+ шагов, ветвления, сложные timeouts | Orchestration |
| Высокий throughput, loose coupling важно | Choreography |
| Бизнес-критично, нужно видеть state workflow | Orchestration |
| Длинные workflows (дни-недели — return process) | Orchestration (с durable state) |

В крупных системах — обе техники в разных частях. Quick low-stakes flows (notification fan-out) — choreography. Critical financial flows (checkout, refund) — orchestration с Temporal/Camunda/AWS Step Functions.

---

## 9. Event Sourcing для Order (опционально, не обязательно)

### 9.1 Идея

Вместо хранения current state в одной строке, хранить последовательность событий и replay'ить для восстановления state.

```text
events:
  [OrderPlaced(items=[...])]
  [DiscountApplied(code=NY10, amount=$10)]
  [PaymentCaptured(amount=$45)]
  [ShipmentCreated(carrier=DHL)]
  [ShipmentDispatched(tracking=...)]
  [ItemReturned(lineId=2, quantity=1)]
  [PartialRefundIssued(amount=$15)]

current state of Order = replay all events
```

### 9.2 Плюсы для Order

- **Полный audit trail** — кто, когда, что сделал. Compliance, dispute resolution.
- **Time travel** — какой был state Order в момент X.
- **Multiple read models (CQRS)** — материализованные views для analytics, customer-facing display, ops dashboard — все генерируются из event stream.
- **Easier debugging** — можно replay events в test environment.

### 9.3 Минусы

- **Event versioning** — schema events меняется со временем; нужны upcasters.
- **Snapshots** — для long-lived aggregates (год+ событий) replay медленный, нужны snapshots.
- **Read complexity** — для сложных query нужны projections.
- **Eventual consistency** для read — между event append и projection update.

### 9.4 Когда применять для Order

✔ Применять, если:

- Compliance требует полного audit trail (B2B, finance, regulated).
- Бизнес часто меняет правила и нужно retroactively rebuild views.
- Нужен complex temporal analytics.

❌ Не применять для:

- Cart aggregate — слишком эфемерный.
- Inventory — нужен low-latency read.
- Простой B2C ecommerce без compliance — overengineering.

---

## 10. CQRS — отделение чтения от записи

### 10.1 Идея

Command side — модель для write (DDD aggregates). Query side — модель для read (denormalized projections).

```text
Write side (Ordering BC):
  - Order aggregate (DDD, normalized, transactional)
  - Repository pattern
  - Domain events

Read side:
  - OrderListView (для admin dashboard)
  - CustomerOrderHistoryView (для customer page)
  - SalesReportView (для analytics)
  - Each populated from domain events via projections
```

### 10.2 Часто пара с Event Sourcing

CQRS + ES — типичная комбинация: events — write store, projections — read stores.

Но CQRS возможен без ES: можно иметь обычную SQL-aggregate persistence + denormalized read replicas, обновляемые через events.

### 10.3 Когда применять

- Read-heavy workloads, разные read shapes.
- Сложные queries не помещаются в normalized aggregate.
- Нужны materialized views с разной refresh rate.

❌ Не применять для CRUD-простых случаев — overhead не оправдан.

---

## 11. Anti-Corruption Layer (ACL) для интеграций

### 11.1 Проблема

Платёжный провайдер Stripe имеет свою модель: PaymentIntent, Charge, Refund, Customer. Если эти концепты "просочатся" в Payment BC, переход на Adyen потребует переписать половину кода.

### 11.2 Решение

ACL — слой translator между внешним API и внутренней моделью:

```text
External Stripe API
       │
       ▼
  ┌─────────────────────────┐
  │   ACL (translator)      │
  │   StripePaymentAdapter  │
  └─────────┬───────────────┘
            │ translates to internal model
            ▼
   Payment BC internal model:
       Payment (aggregate)
         Authorization
         Capture
         Refund
```

Внутренняя модель Payment BC не знает о Stripe-специфичных концептах. При смене провайдера меняется только адаптер.

### 11.3 ACL в e-commerce — типичные места

| Интеграция | ACL для |
|---|---|
| Payment provider (Stripe / Adyen / СБП) | Payment BC |
| Shipping carrier (DHL, UPS, СДЭК) | Shipping BC |
| Tax engine (Avalara, TaxJar) | Pricing BC |
| Address validation (SmartyStreets) | Customer BC |
| ERP (NetSuite, SAP) | Многие BC через single ACL service |

---

## 12. Реальные примеры из open-source

### 12.1 ttulka/ddd-example-ecommerce

Pure DDD реализация e-commerce на Java/Spring. BC: Catalog, Cart, Ordering, Shipping, Payment, Warehouse. Хорошая reference-имплементация для изучения.

### 12.2 Eric Evans cargo shipping

DDD Sample (dddsample.sourceforge.net) — официальный пример Эванса. Хотя это shipping, не ecommerce, многие паттерны применимы 1:1.

### 12.3 Microsoft eShopOnContainers

.NET reference application для DDD + microservices + CQRS + Event Sourcing. Большой, но иллюстративный.

### 12.4 Cosmic Python

Книга "Architecture Patterns with Python" (Percival, Gregory) показывает DDD + CQRS + Event-driven на компактном примере с Allocation domain — параллельно ecommerce ordering.

---

## 13. Чек-лист DDD для Order — практический

### 13.1 Стратегический уровень

- [ ] Идентифицированы bounded contexts (Cart, Ordering, Payment, Inventory, Shipping, Returns, Customer, Catalog)
- [ ] Составлен context map с типами связей (Customer-Supplier, ACL, Conformist, etc.)
- [ ] Каждый BC имеет свой ubiquitous language, документированный
- [ ] Core domain выделен из supporting/generic subdomains
- [ ] Команды организованы вокруг BC (Conway's law)

### 13.2 Тактический уровень — Ordering BC

- [ ] Order — aggregate root с явными invariants
- [ ] OrderLine — child entity, не value object
- [ ] Money, Address, Email — value objects, не primitives
- [ ] OrderId — strongly-typed, не UUID/long
- [ ] Все mutations Order проходят через методы aggregate root
- [ ] Repository интерфейс — для Order, не для OrderLine
- [ ] Cross-aggregate references — by id, не by full object
- [ ] Одна транзакция — один aggregate save
- [ ] Domain events публикуются на ключевых state transitions
- [ ] FSM Order статусов реализован внутри aggregate
- [ ] Factory для сложных создаваний (`OrderFactory.fromCart(cart)`)

### 13.3 Интеграционный уровень

- [ ] Domain events имеют past-tense имена и domain meaning
- [ ] Outbox pattern для reliable event publishing
- [ ] Inbox pattern или idempotent consumers для events
- [ ] Saga / Process Manager для checkout workflow
- [ ] Compensating transactions определены для каждого failure point
- [ ] ACL для каждого external integration (PSP, carriers)
- [ ] Integration events версионированы

---

## 14. Anti-patterns DDD для Order — что НЕ делать

| Anti-pattern | Почему плохо | Как правильно |
|---|---|---|
| Anemic domain model — Order — просто bag of fields, логика в OrderService | DDD теряется, превращается в transaction script | Поведение в aggregate root |
| God Aggregate — Order содержит Payment, Shipment, Customer | Concurrency conflicts, slow loads | Separate aggregates, id references |
| Cross-aggregate references — `Order.customer: Customer` | Aggregate boundaries размыты | `Order.customerId: CustomerId` |
| Multi-aggregate transactions — save Order + Payment в одном tx | Distributed locking, deadlocks | Saga + eventual consistency |
| Primitive obsession — Money as BigDecimal | Currency confusion bugs | Money value object |
| CRUD events — OrderUpdated, OrderModified | Теряется domain meaning | Domain events: OrderShippingAddressChanged |
| Shared database between BC | Нарушение boundaries, coupling | Каждый BC — своя БД |
| Generic OrderStatus enum (CREATED/UPDATED/DELETED) | Нет domain semantics | FSM с явными business states |
| No Anti-Corruption Layer для Stripe/carriers | Vendor lock-in | ACL adapter |
| Domain events as DTOs between BC без mapping | Schema coupling | Integration events с stable schema |

---

## 15. Связь с другими темами research

- **Тема 1 (E-commerce гиганты)** — Shopify Order vs OrderSummary == DDD discriminate immutable Order vs mutable view. Salesforce то же самое.
- **Тема 4 (FSM)** — реализуется внутри Order aggregate как value object/enum + transition rules.
- **Тема 5 (Saga)** — настоящая глава этой темы продолжается в теме 5; здесь даны базовые концепты.
- **Тема 6 (Payments)** — Payment BC + ACL для PSP — основной паттерн.
- **Тема 7 (Logistics)** — Shipping BC + ACL для carrier — основной паттерн.
- **Тема 9 (Returns)** — Returns BC, отдельный aggregate RMA.

---

## 16. Источники

### Foundational books

- "Domain-Driven Design: Tackling Complexity in the Heart of Software" — Eric Evans (2003) — Blue Book
- "Implementing Domain-Driven Design" — Vaughn Vernon (2013), sample chapter — Red Book

### Vaughn Vernon — Effective Aggregate Design

- Effective Aggregate Design Part I: Modeling a Single Aggregate
- Effective Aggregate Design Part II: Making Aggregates Work Together
- Effective Aggregate Design Part III: Gaining Insight Through Discovery
- Aggregate Design Rules according to Vernon's Red Book — ArchiLab
- Rule: Design Small Aggregates — InformIT
- Rule: Model True Invariants in Consistency Boundaries
- Rule: Reference Other Aggregates by Identity
- Rule: Use Eventual Consistency Outside the Boundary
- Reasons to Break the Rules

### Bounded Contexts & Strategic Design

- Defining Bounded Contexts — Eric Evans at DDD Europe — InfoQ
- Bounded Context — Martin Fowler bliki
- Ubiquitous Language — Martin Fowler bliki
- Domain-driven design — Wikipedia
- DDD and Bounded Context — InformIT
- Using bounded context for effective DDD — TechTarget
- Open Group: DDD Strategic Patterns

### Context Mapping

- Context Map — Context Mapper
- Customer/Supplier — Context Mapper
- Shared Kernel — Context Mapper
- Anticorruption Layer — Context Mapper
- Context Mapping — DevIQ

### Aggregates — practical

- DDD Aggregate — Martin Fowler bliki
- DDD Aggregates: Consistency Boundary — James Hickey
- Understanding Aggregates and Boundaries in DDD
- Mastering Transactions: The Power of Aggregates in DDD
- Aggregates and Consistency Boundaries — Cosmic Python
- Designing DDD aggregates — Albert Llousas
- SAP Curated Resources — How to model aggregates
- SAP Curated Resources — How to develop aggregates

### Cargo Shipping example

- DDD Sample Application — Eric Evans
- DDD Cargo Shipping Example — O&B Insights
- DDD Cargo Shipping — Adapting and Learning
- Cargo shipping example — eventsourcing docs

### E-commerce DDD examples

- ttulka/ddd-example-ecommerce — GitHub
- Spring Boot DDD E-Commerce Order Management — DEV
- Service boundaries identification example in e-commerce — HackerNoon
- Implementing Cart Service with DDD & Hexagonal — Walmart Global Tech
- Microservices Powered By DDD — DZone

### Sagas & Process Managers

- Saga Pattern — microservices.io
- Saga Design Pattern — Azure Architecture Center
- Process Managers and Sagas in DDD — Hossein Nejati Javaremi
- Process Manager vs Saga Confusion — Driggl
- Saga and Process Manager — Event-Driven.io
- Saga Patterns: Choreography vs Orchestration
- Saga Orchestration vs Choreography Trade-off
- Event Choreography & Orchestration (Sagas) — CodeOpinion

### Event Sourcing & CQRS

- Event Sourcing Pattern — Azure Architecture Center
- CQRS Pattern — Azure Architecture Center
- Event Sourcing Pattern — microservices.io
- CQRS and Event Sourcing in Java — Baeldung
- Developing Transactional Microservices Using Aggregates, Event Sourcing and CQRS — InfoQ
- Live projections for read models — Kurrent

### Value Objects & Entities

- Value Objects in .NET — Thinktecture
- Entities and Value Objects — Abraham Berg
- Exploring Value Objects in DDD
- DDD Modelling — Aggregates vs Entities

---

## Related

- [[Research - Order Architecture]] — индекс серии Order
- [[Research - Order (2) State Machine FSM]] — реализация invariants на уровне FSM
- [[Research - Order (3) E-commerce Giants]] — практика Order ≠ Shipment у Amazon/Shopify
- [[Research - Order (5) Payment Integration]] — Payment как отдельный BC
- [[Research - Order (6) Logistics Integration]] — Shipment как отдельный BC
- [[Research - Order (7) Saga Pattern]] — eventual consistency между BC через domain events
- [[Research - Cart Architecture (3) DDD Patterns]] — DDD для Cart BC (parallel research)
- [[ADR-001 Clean Architecture Modular Monolith]] — backend архитектурная база
- [[Backend]] — backend dashboard
- [[Loyality Project]]
