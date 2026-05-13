---
tags:
  - project/loyality
  - backend
  - order
  - saga
  - distributed-transactions
  - outbox
  - research
type: research
date: 2026-04-29
aliases: [Saga Pattern, Distributed Transactions, Choreography vs Orchestration, Outbox Inbox]
cssclasses: [research]
status: active
parent: "[[Research - Order Architecture]]"
project: "[[Loyality Project]]"
component: backend
---

# Research — Order (7) Saga Pattern

> Choreography vs Orchestration, Outbox/Inbox patterns, eventual consistency Cart → Order → Inventory → Payment → Shipment, компенсирующие действия, pivot transactions, semantic locks. Истоки: Hector Garcia-Molina & Kenneth Salem (1987) — "Sagas".

## TL;DR — ключевые выводы

1. **Saga = последовательность local transactions с компенсациями.** Не «распределённый ACID», а eventual consistency через бизнес-уровень компенсирующих действий.
2. **2PC мёртв для микросервисов.** Lock'и держатся через RPC, single coordinator = SPOF, не работает с heterogeneous БД и external services (PSP). Saga — стандарт de-facto.
3. **Compensation ≠ rollback.** Payment не rolled back — он refunded. Inventory не «восстановлен» — он released. Shipment не «отменён мгновенно» — он cancelled или intercepted. Это бизнес-операции с side effects, а не undo.
4. **Outbox + Inbox** — обязательная пара для reliable messaging. Outbox решает «atomically save state + publish event»; Inbox обеспечивает idempotent consumption.
5. **Choreography для простого, Orchestration для сложного.** Реальные системы используют оба: choreography для loose-coupled fan-out, orchestration (Temporal / Step Functions / Camunda) — для checkout как business-critical flow.
6. **Pivot transaction** — «точка невозврата»: после неё компенсации больше не возможны (например, передача груза курьеру).
7. **Semantic locks** — flag в записи `TENTATIVE`/`PENDING` с TTL-based expiry — стандарт для inventory reservations.
8. **Inventory reservation с TTL** — практичный паттерн: reservation создаётся на 15–30 минут, expire'ется автоматически, не нужно компенсировать, если customer не закончил checkout.

---

## 1. Зачем Saga — почему 2PC не работает

### 1.1 Что такое 2PC (Two-Phase Commit)

```text
Coordinator                Participants (DB1, DB2, DB3)
    │                              │
    │── Phase 1: PREPARE ──────────►
    │                              │
    │◄── prepared / abort ─────────│
    │                              │
    │── Phase 2: COMMIT/ROLLBACK ──►
    │                              │
    │◄── ack ──────────────────────│
```

Гарантирует ACID across multiple БД. Используется в legacy enterprise (XA transactions, Java JTA).

### 1.2 Почему 2PC не подходит для микросервисов и checkout

| Проблема | Описание |
|---|---|
| Single point of failure | Coordinator падает между phase 1 и phase 2 → participants виснут с locked rows |
| Locks через RPC | Inventory database держит row locks, пока Payment service отвечает. Performance умирает |
| Heterogeneous systems | Stripe/Adyen/SBP не поддерживают XA. Carrier API тоже. Нельзя prepare→commit с external partner |
| Latency | Synchronous round-trips на N participants — checkout будет 2-5 секунд |
| Long-running | Checkout может включать 3DS challenge — это минуты. 2PC не для long transactions |
| Cloud incompatibility | Cloud DBs (DynamoDB, Cosmos, Aurora) обычно не поддерживают XA |
| Coupling | All participants должны быть available одновременно. Failure одного — failure всей транзакции |

### 1.3 Saga: историческая справка

Концепт opublikована Hector Garcia-Molina и Kenneth Salem в 1987 году в Princeton paper "Sagas". Цель paper'а — long-running transactions в БД (часы/дни), которые держать ACID lock'и было бы катастрофой.

Идея: разбить long transaction на последовательность коротких local transactions. Если один шаг fail — выполнить compensating transactions для уже завершённых шагов в обратном порядке. Это не rollback, это semantically reverse операции.

---

## 2. Базовая модель Saga для checkout

### 2.1 Линейный happy path

```text
Step 1: Order Service           CreateOrder(state=PENDING)
              │
              ▼
Step 2: Inventory Service       ReserveStock(items, ttl=15min)
              │
              ▼
Step 3: Payment Service         AuthorizePayment(amount, idempotency_key)
              │
              ▼
Step 4: Payment Service         CapturePayment(paymentId)  ◄── pivot transaction
              │
              ▼
Step 5: Order Service           ConfirmOrder(state=PAID)
              │
              ▼
Step 6: Shipment Service        CreateShipment(orderId)
              │
              ▼
Step 7: Order Service           MarkFulfilled(state=FULFILLED)
```

### 2.2 Compensation chain при failure

Если step 6 (CreateShipment) fails:

```text
Reverse order:
   Compensate step 5: RevertOrderToPending — N/A, just don't confirm
   Compensate step 4: RefundCapturedPayment(paymentId)
   Compensate step 3: VoidAuthorization (если ещё не captured)
   Compensate step 2: ReleaseStockReservation(reservationId)
   Compensate step 1: CancelOrder(state=CANCELLED)
```

Ключевая идея: compensations — это forward operations с обратным эффектом. Они новые транзакции, не undo.

### 2.3 Compensable vs retryable transactions

В каноничном Garcia-Molina papers Saga steps делятся на:

- **Compensable transactions** — могут быть semantically отменены compensating transactions (ReserveStock, AuthorizePayment).
- **Pivot transaction** — "точка невозврата". После pivot compensation уже не имеет смысла или невозможна (CapturePayment у некоторых PSPs, ShipmentDispatched).
- **Retryable transactions** — после pivot. Должны быть idempotent retry-safe (UpdateAnalytics, NotifyCustomer).

```text
Compensable │ Compensable │ Compensable │ PIVOT │ Retryable │ Retryable
   (undoable)              ↑           (no undo)
                       point of no return
```

---

## 3. Choreography — event-driven Saga

### 3.1 Идея

Нет central coordinator. Каждый сервис подписывается на events и реагирует своими actions, публикуя следующие events.

### 3.2 Checkout choreography пример

```text
[OrderService]
  receive POST /checkout
  CreateOrder (state = PENDING)
  publish OrderCreated(orderId, items, customerId, total)
       │
       ▼
[InventoryService]
  subscribe OrderCreated
  try reserve stock for each item
  ├─ success → publish StockReserved(orderId, reservationId, expires_at)
  └─ failure → publish StockReservationFailed(orderId, reason)

[PaymentService]
  subscribe StockReserved
  call PSP authorize+capture
  ├─ success → publish PaymentCaptured(orderId, paymentId, amount)
  └─ failure → publish PaymentFailed(orderId, reason)

[OrderService]
  subscribe PaymentCaptured → transition Order → CONFIRMED, publish OrderConfirmed
  subscribe PaymentFailed → publish OrderCancelled

[InventoryService]
  subscribe OrderCancelled → release reservation, publish StockReleased
  subscribe StockReservationFailed → no action (no reservation to release)

[ShipmentService]
  subscribe OrderConfirmed
  create shipment, generate label
  publish ShipmentCreated(orderId, trackingNumber)

[OrderService]
  subscribe ShipmentCreated → transition Order → FULFILLED
```

### 3.3 Плюсы choreography

- **Loose coupling.** OrderService не знает, что есть PaymentService и ShipmentService.
- **Высокий throughput.** Нет central bottleneck.
- **Resilience.** Падение одного service не блокирует остальной flow моментально (pending events накапливаются в broker).
- Подходит для event-driven архитектуры — естественно ложится на Kafka/RabbitMQ/SNS+SQS.

### 3.4 Минусы choreography

- **Распылённая бизнес-логика.** "Где определена checkout flow?" — нигде в одном месте.
- **Hard to debug.** Залип saga в середине — никто не знает где.
- **Циклические зависимости** — если service A слушает события service B, и B слушает A, легко создать loop.
- **Implicit coupling.** Хотя сервисы не знают друг о друге явно, изменение event schema ломает всех subscribers.
- **No global timeout/retry policy.** Каждый service сам реализует свой retry/timeout.
- **Sturdy of failure paths.** Compensations должны быть распределены по сервисам — каждый сам инициирует свой rollback.

### 3.5 Когда выбрать choreography

- Простые workflow (2-3 шага).
- Нет необходимости в централизованной visibility.
- Loose coupling важнее, чем audit/debug.
- Event-driven архитектура уже есть (Kafka).

---

## 4. Orchestration — central coordinator Saga

### 4.1 Идея

Один центральный orchestrator (saga orchestrator / process manager) знает всю последовательность шагов, command'ит каждый сервис и собирает ответы. Сервисы не знают друг о друге — общаются только с orchestrator.

### 4.2 Checkout orchestration пример

```text
CheckoutOrchestrator (state machine):

  state INIT:
    on StartCheckout →
      send CreateOrder command to OrderService
      transition CREATING_ORDER

  state CREATING_ORDER:
    on OrderCreated →
      send ReserveStock command to InventoryService
      save reservation request
      transition RESERVING_STOCK
    on OrderCreationFailed →
      transition FAILED (no compensations needed)

  state RESERVING_STOCK:
    on StockReserved →
      send AuthorizePayment command to PaymentService
      transition CHARGING_PAYMENT
    on StockReservationFailed →
      send CancelOrder command (compensation)
      transition COMPENSATING

  state CHARGING_PAYMENT:
    on PaymentAuthorized →
      send CapturePayment command (pivot)
      transition CAPTURING_PAYMENT
    on PaymentFailed →
      send ReleaseStock command (compensation)
      send CancelOrder command (compensation)
      transition COMPENSATING

  state CAPTURING_PAYMENT:
    on PaymentCaptured →
      send ConfirmOrder command
      send CreateShipment command
      transition CONFIRMING

  state CONFIRMING:
    on OrderConfirmed && ShipmentCreated →
      send MarkFulfilled command
      transition COMPLETED

  state COMPENSATING:
    on all compensations acknowledged →
      transition FAILED

  state COMPLETED: (terminal)
  state FAILED: (terminal)
```

### 4.3 Плюсы orchestration

- **Centralized business logic.** Workflow видно в одном месте.
- **Easy debugging.** Можно посмотреть state orchestrator instance.
- **Global timeouts/retries.** Orchestrator управляет policies.
- **Versioning.** Workflow versioning легче, чем версионирование events.
- **Visibility.** Метрики per-step, alert если saga зависла.
- **Compensation logic** в одном месте — легче гарантировать правильный reverse order.

### 4.4 Минусы orchestration

- **Tighter coupling.** Сервисы зависят от orchestrator API.
- **Risk of god-object.** Orchestrator вырастает в монолит.
- **SPOF** (mitigates через replication).
- **Performance overhead.** Каждый step — round-trip через orchestrator.

### 4.5 Реализации orchestration

| Платформа | Подход | Когда выбрать |
|---|---|---|
| Temporal.io | Workflows-as-code (Java/Go/TS/Python) | Modern, code-first, durable execution, type-safe |
| AWS Step Functions | JSON Amazon States Language | AWS-native, ограниченный по выразительности |
| Camunda 8 (Zeebe) | BPMN visual modeling | Enterprise с business analysts, regulated industries |
| Apache Airflow | DAG в Python | Batch / data pipelines, не для checkout |
| Netflix Conductor | JSON workflow | Large-scale, OSS |
| Spring State Machine | In-app FSM | Single-service workflows, не distributed |
| Apache Seata | TCC + Saga в Java | Java ecosystem, China-developed |

### 4.6 Когда выбрать orchestration

- Checkout — критичный бизнес-flow с 5+ шагами.
- Сложные ветвления (3DS, fraud check, partial payment).
- Нужна visibility и audit.
- Длинные workflows (return process — недели).
- Регулируемые отрасли (compliance audit trail).

---

## 5. Outbox pattern — atomic state save + event publish

### 5.1 Проблема dual-write

```python
def place_order(order):
    db.save(order)             # transaction 1: SQL DB
    kafka.publish(OrderCreated) # transaction 2: Kafka
```

Что если:

- DB save succeeded, но process crashed до Kafka publish? → Order создан, события нет, downstream не знает.
- Kafka publish succeeded, но DB save failed? → Event опубликован о несуществующем Order.

Нет общей транзакции между БД и broker. Это classic dual-write problem.

### 5.2 Решение: Transactional Outbox

```python
def place_order(order):
    with db.transaction():
        db.save(order)
        db.save_to_outbox(OrderCreated)
    # commit one transaction
```

Отдельный relay process читает outbox table и публикует в broker:

```text
┌────────────────┐    ┌──────────────────┐    ┌──────────┐
│  OrderService  │    │  Outbox Relay    │    │  Kafka   │
│                │    │  (Debezium CDC)  │    │          │
│  ┌──────────┐  │    └─────┬────────────┘    └────┬─────┘
│  │ orders   │  │          │                      │
│  ├──────────┤  │          │                      │
│  │ outbox   │◄─┼──────────┘                      │
│  └──────────┘  │  reads outbox                   │
│                │                                 │
└────────────────┘  publishes events ──────────────►
```

### 5.3 Outbox table schema

```sql
CREATE TABLE outbox (
    id              BIGSERIAL PRIMARY KEY,
    aggregate_type  VARCHAR(64) NOT NULL,   -- e.g. 'Order'
    aggregate_id    VARCHAR(64) NOT NULL,   -- e.g. order id
    event_type      VARCHAR(64) NOT NULL,   -- e.g. 'OrderCreated'
    event_id        UUID UNIQUE NOT NULL,   -- idempotency for consumers
    payload         JSONB NOT NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    published_at    TIMESTAMP,
    -- Optional: traceparent для distributed tracing
    traceparent     VARCHAR(64)
);

CREATE INDEX idx_outbox_unpublished ON outbox(created_at)
WHERE published_at IS NULL;
```

### 5.4 Два способа публикации

#### 5.4.1 Polling publisher

Background worker раз в N мс читает unpublished events:

```sql
SELECT * FROM outbox
WHERE published_at IS NULL
ORDER BY id
LIMIT 100;
```

Публикует в Kafka, помечает `published_at`. Простой подход, но добавляет latency (poll interval).

#### 5.4.2 Change Data Capture (CDC) — Debezium

Debezium читает write-ahead log БД (Postgres WAL, MySQL binlog) и publishes изменения в Kafka в реальном времени. Нет polling overhead.

> "Debezium tails the transaction log (WAL) of the order service's Postgres database in order to capture any new events in the outbox table and propagates them to Apache Kafka."

Преимущества:

- Latency ~ms.
- Нет нагрузки на БД от polling.
- Гарантированно опубликует commit'нутые в БД transactions, даже после restart.

Недостатки:

- Operational complexity (Kafka Connect cluster, monitoring).
- Schema evolution Debezium connector.

### 5.5 Гарантии delivery

> "This solution guarantees at-least-once delivery, since Kafka Connect services ensure that each connector is always running; to ensure exactly-once delivery, the consuming client must be Idempotent."

At-least-once + idempotent consumer = exactly-once семантика бизнес-эффекта.

### 5.6 Outbox best practices

- [ ] Outbox table в той же DB schema что и aggregate (одна транзакция)
- [ ] `event_id` UUID v4, UNIQUE constraint
- [ ] Index на `(published_at IS NULL, created_at)` для эффективного poll
- [ ] Размер outbox мониторить (alert если backlog > X)
- [ ] Retention policy: cleanup published events после M дней (analytics retain в Kafka)
- [ ] Schema events версионирована (CloudEvents spec — хорошая база)
- [ ] Распределённый tracing (`traceparent`) включён в payload
- [ ] Sequence number per aggregate (для ordering guarantees)
- [ ] Partition Kafka topic по `aggregate_id` для ordered consumption per aggregate

---

## 6. Inbox pattern — idempotent consumer

### 6.1 Проблема duplicate delivery

Любой message broker даёт at-least-once, не exactly-once. Consumer может получить дважды:

- Network timeout, broker re-delivers.
- Consumer crashed после processing, до commit offset.
- Producer retried (если outbox есть, retries автоматичны).

Если processing имеет side effects (charge customer, send email, decrement stock), дубликаты опасны.

### 6.2 Решение: Inbox table + dedup

```sql
CREATE TABLE inbox (
    event_id     UUID PRIMARY KEY,         -- из outbox publisher
    consumer     VARCHAR(64) NOT NULL,
    processed_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

Consumer:

```python
def handle_event(event):
    with db.transaction():
        try:
            db.execute("INSERT INTO inbox (event_id, consumer) VALUES (?, ?)",
                       event.id, 'inventory_service')
        except UniqueViolation:
            log.info("Duplicate event %s, skipping", event.id)
            return  # already processed

        # Apply business logic in same transaction
        apply_event(event)
    # commit
```

Atomic INSERT с UNIQUE constraint = race-condition-free dedup.

### 6.3 Inbox + outbox combo

> "The Transactional Outbox + Idempotent Consumer combo was described as a 'gold standard' for no duplicate processing."

Полный paired flow:

```text
[Producer Service]
   ┌─────────────────┐
   │ aggregate +     │  one transaction
   │ outbox          │
   └────────┬────────┘
            ▼
   ┌─────────────────┐
   │ relay (Debezium)│
   └────────┬────────┘
            ▼
   ┌─────────────────┐
   │  Kafka topic    │  at-least-once delivery
   └────────┬────────┘
            ▼
[Consumer Service]
   ┌─────────────────┐
   │ inbox dedup +   │  one transaction
   │ business logic  │
   └─────────────────┘
```

### 6.4 Inbox best practices

- **TTL для inbox:** старые `event_ids` можно удалять (нагрузка не выше определённого окна re-delivery — обычно дни).
- **Composite key (event_id, consumer):** один event_id может обрабатываться разными consumers — каждому свой inbox row.
- **Idempotency должна быть атомарна** с business logic — иначе race.
- **Stricter: business-key-based dedup.** Иногда event_id не подходит (например, разные events приводят к одному business effect). Тогда dedup по `(aggregate_id, operation_type)`.

### 6.5 Альтернативы Inbox

- **Idempotent operations natural-keyed:** UPSERT с `ON CONFLICT` по business id.
- **Conditional state transitions:** `UPDATE ... WHERE state = 'expected_previous_state'` (FSM-aware idempotency).
- **Optimistic locking by version:** `WHERE version = $expected`.

---

## 7. Eventual consistency — практические grants

### 7.1 Что значит eventual consistency для checkout

Пользователь нажал "Place Order". Что он видит сразу:

- "Order received, processing payment..."

Что происходит за следующие секунды:

- t=0ms: Order created, OrderCreated published.
- t=50ms: Stock reserved, StockReserved published.
- t=200ms: Payment authorized.
- t=400ms: Payment captured.
- t=450ms: Order confirmed.
- t=500ms: Shipment created.

UI обычно показывает "Order placed!" сразу после Order create, и dashboard polls для финального статуса.

### 7.2 Окна inconsistency

Между шагами есть windows of inconsistency, которые надо явно дизайнить:

| Window | Длительность | Видно ли user'у |
|---|---|---|
| OrderCreated → StockReserved | ~50ms | Нет (loader) |
| StockReserved → PaymentCaptured | ~300ms (без 3DS), 1-3min (с 3DS) | Да (3DS challenge) |
| PaymentCaptured → ShipmentCreated | ~50ms | Нет |
| ShipmentCreated → CarrierAccepted | минуты-часы | Нет (status updates) |
| ShipmentDispatched → Delivered | дни | Да (tracking) |

### 7.3 Inventory oversell — главный риск

При eventual consistency есть окно, где customer видит "in stock", а реально stock уже зарезервирован/продан.

#### 7.3.1 Naive подход

```text
Проверка stock: at view product → in stock
Customer adds to cart → in stock (still)
Customer checks out → all of a sudden out of stock
```

UX disaster.

#### 7.3.2 Reservation pattern (правильный)

```text
Cart create / view product:    no reservation
Cart checkout (begin):          ReserveStock(items, ttl=15min)
                                ── stock decremented in availability ──
Customer abandons cart:         TTL expires → StockReleased
Customer pays successfully:     ReservationCommitted → permanent decrement
Customer payment fails:         ReleaseStock immediately
```

TTL-based expiry — критичный механизм. Без TTL зависшие reservations накапливаются — phantom out-of-stock.

#### 7.3.3 Реализация с Redis

```text
SET stock:sku123:reservation:{order_id} {qty} EX 900  # 15min TTL
DECRBY stock:sku123:available {qty}
```

Atomic operations через Lua script или Redis transactions. TTL expiry автоматически triggers compensation (stock возвращается в available).

### 7.4 Customer-visible inconsistency: что делать

Иногда inconsistency дойдёт до customer. Стратегии:

1. **Pessimistic UX:** "Order placed, awaiting confirmation." Не показывать сразу "ваш заказ оплачен!"
2. **Optimistic UX с rollback messaging:** "Order placed!" → если payment failed позже, прислать email "Order cancelled, payment issue".
3. **Sync read-after-write:** после place order сразу redirect на page, которая показывает actual status (poll backend).
4. **Webhooks/SSE/WebSocket:** push real-time updates на customer page.

### 7.5 Saga визибилити для customer

Customer хочет видеть "где мой order сейчас". Решение — саму saga state expose в read model:

```text
CheckoutSagaStatus:
  - INITIATED
  - INVENTORY_RESERVED
  - PAYMENT_PROCESSING (3DS active)
  - PAYMENT_FAILED → showing retry option
  - COMPLETED
  - FAILED → showing reason
```

Это не technical implementation detail, это часть UX.

---

## 8. Полный checkout saga — детальный walkthrough

### 8.1 Stages

```text
[Stage 1: Cart → Order]
  Cart Service → emit CartCheckoutStarted(cart_snapshot)
  Order Service ← CartCheckoutStarted
  Order Service → CreateOrder (state=PENDING)
  Order Service → emit OrderCreated

[Stage 2: Order → Inventory Reservation]
  Inventory Service ← OrderCreated
  Inventory Service → reserve stock for each line
  ├─ success → emit StockReserved(reservation_id, expires_at)
  └─ failure → emit StockReservationFailed(reason, items_unavailable)
                    → triggers Compensation 1

[Stage 3: Inventory → Payment]
  Payment Service ← StockReserved
  Payment Service → AuthorizePayment via PSP (Stripe/Adyen/SBP)
  ├─ 3DS required → emit PaymentRequiresAction(redirect_url)
  │                    customer completes 3DS
  │                    Payment Service ← 3DS callback
  ├─ success → emit PaymentAuthorized(amount, payment_id)
  └─ failure → emit PaymentFailed(reason)
                    → triggers Compensation 2

[Stage 4: Payment Capture (PIVOT)]
  Payment Service → CapturePayment
  ├─ success → emit PaymentCaptured ← PIVOT POINT
  └─ failure → manual investigation, partial reversal

[Stage 5: Order Confirmation]
  Order Service ← PaymentCaptured
  Order Service → transition state to CONFIRMED
  Order Service → emit OrderConfirmed

[Stage 6: Shipment Creation]
  Shipment Service ← OrderConfirmed
  Shipment Service → create shipment, generate label
  ├─ success → emit ShipmentCreated(tracking_number)
  └─ failure → manual queue, retry later

[Stage 7: Order Fulfilled]
  Order Service ← ShipmentCreated
  Order Service → transition state to FULFILLED
  Order Service → emit OrderFulfilled
  Notification Service ← OrderFulfilled → send email to customer
```

### 8.2 Compensations таблица

| Failure point | Compensation chain (reverse order) |
|---|---|
| Stage 2 failed | Cancel Order. Cart unchanged (customer can retry). |
| Stage 3 failed (auth) | Release Stock Reservation. Cancel Order. |
| Stage 3 failed (3DS abandoned/timeout) | Release Stock Reservation. Cancel Order (state=ABANDONED). |
| Stage 4 failed (capture) | Void Authorization. Release Stock. Cancel Order. |
| Stage 5 failed (rare) | Refund Payment. Release Stock. Cancel Order. Manual alert. |
| Stage 6 failed | Hold for manual fulfillment OR Refund + Release + Cancel + customer notify. |
| Stage 7 — already terminal-ish | No compensation needed; Order is paid. Manual ops. |

### 8.3 Visualization (orchestration view)

```text
                ┌──────────────────────────────────────┐
                │   CheckoutOrchestrator (Temporal)    │
                │   workflow_id = order_id (idempotent)│
                └─────────────────┬────────────────────┘
                                  │
        ┌─────────┬───────────────┼───────────────┬─────────┐
        ▼         ▼               ▼               ▼         ▼
   ┌────────┐┌─────────┐  ┌─────────────┐  ┌─────────┐ ┌──────────┐
   │Cart    ││Order    │  │Inventory    │  │Payment  │ │Shipment  │
   │Service ││Service  │  │Service      │  │Service  │ │Service   │
   └────────┘└─────────┘  └─────────────┘  └─────────┘ └──────────┘
                  │              │               │           │
                  └──────── domain events ───────┴───────────┘
                                  │
                                  ▼
                          ┌──────────────┐
                          │  Kafka topic │
                          └──────────────┘
                                  │
                ┌─────────────────┼──────────────────┐
                ▼                 ▼                  ▼
           ┌──────────┐      ┌──────────┐      ┌───────────────┐
           │Analytics │      │Email/SMS │      │Loyalty Service│
           │Service   │      │Service   │      │               │
           └──────────┘      └──────────┘      └───────────────┘
```

Synchronous orchestration для critical path; choreography для downstream notifications — обе техники в одной системе.

---

## 9. Compensation patterns — нюансы

### 9.1 Semantic locks (countermeasure A)

Из Garcia-Molina paper: между compensable transaction и pivot существует возможность dirty reads. Чтобы предотвратить:

> "When using the semantic lock countermeasure, a SAGA's compensable transaction sets a flag on each record that it creates or updates, and the flag indicates that the record is tentative."

После PIVOT: state → CONFIRMED. Lock released.

Это та самая причина, почему `state` колонка в Order имеет промежуточные states (PENDING, AWAITING_PAYMENT) — это semantic locks.

### 9.2 Pivot transaction — точка невозврата

```text
Compensable │ Compensable │ PIVOT  │ Retryable │ Retryable
   undoable                point of no return
```

Examples for checkout:

```text
[Order pending] [Stock reserved] [Payment authorized] PIVOT [Payment captured] [Order confirmed] [Shipment created]
                                    ↑                                              ↑                ↑
                                  point of no return        Сложно компенсировать после captured: refund нужен
```

Что считать pivot — бизнес-решение:

- В B2C обычно `PaymentCaptured`. После него compensation — это refund (новая операция, money flow обратно).
- В некоторых системах pivot — `ShipmentDispatched` (после физической отгрузки compensation = return-to-sender, дорого).

### 9.3 Retryable transactions — после pivot

После pivot все steps должны быть idempotent retry-safe:

```text
[Pivot: PaymentCaptured]
       │
       ▼
[Send confirmation email]   ← retryable, idempotent (dedup by event_id)
[Update analytics]          ← retryable, idempotent
[Award loyalty points]      ← retryable, idempotent (dedup by order_id)
[Trigger fulfillment]       ← retryable, idempotent
```

### 9.4 Backward vs forward recovery

- **Backward recovery (compensation)** — основной механизм. Откат через compensating transactions.
- **Forward recovery** — после pivot "fix-forward". Например, capture payment failed → manual capture, не revert.

### 9.5 Когда compensation физически невозможна

- Email уже отправлен customer'у — нельзя "не отправить".
- Inventory уже отгружен → товар уже на грузовике.
- Loyalty points уже потрачены customer'ом.

В таких случаях:

1. **Saga design должна делать physical-effect actions ПОСЛЕ pivot.**
2. **Apologetic compensation:** "send another email — sorry, we cancelled". Не undo, но коммуникация.
3. **Best-effort cleanup:** intercept shipment если возможно.
4. **Acceptance:** некоторые состояния остаются "permanently bad" — compensate через customer service ticket.

---

## 10. Идемпотентность каждого шага — конкретика

### 10.1 Order Service: CreateOrder

- **Idempotency key:** UUID v4 от клиента, или `cart_id` (стабильный).
- **DB:** UNIQUE constraint на `idempotency_key` колонке Order.
- **Behavior:** второй раз с тем же ключом → return existing order (200 OK), не 409.

### 10.2 Inventory Service: ReserveStock

- **Idempotency key:** `reservation_id` = deterministic hash of `(order_id, sku, qty)`.
- **DB:** UPSERT reservation by `reservation_id`.
- **Behavior:** повторный вызов — no-op (already reserved).

### 10.3 Payment Service: AuthorizePayment / CapturePayment

- **Idempotency key:** Stripe-style `Idempotency-Key` HTTP header.
- **PSP:** уже сами idempotent.
- **Local DB:** запись по `idempotency_key`, при повторе — return cached result.

### 10.4 Shipment Service: CreateShipment

- **Idempotency key:** `order_id` (один shipment-set на order).
- **DB:** UPSERT shipment by `order_id`.

### 10.5 Notification Service: SendEmail

- **Idempotency key:** `event_id` (event который триггерит email).
- **DB:** inbox dedup.

---

## 11. Saga execution coordinator — Temporal-style

### 11.1 Что делает Temporal/Camunda/Step Functions

- Persistent state of workflow (durable execution).
- Automatic retries с backoff.
- Timeout enforcement.
- Heartbeat (long-running activities).
- Versioning of workflows.
- History/replay (debugging).
- Visibility UI.

### 11.2 Temporal pseudo-code пример

```typescript
async function checkoutWorkflow(input: CheckoutInput): Promise<Result> {
  const orderId = await createOrder(input);
  let reservationId: string | null = null;
  let paymentId: string | null = null;

  try {
    reservationId = await reserveStock(orderId, input.items, ttl='15m');

    paymentId = await authorizePayment({
      amount: input.total,
      orderId,
      idempotencyKey: orderId,
    });

    // PIVOT
    await capturePayment(paymentId);

    // Retryable steps after pivot
    await confirmOrder(orderId);
    await createShipment(orderId);
    return { success: true, orderId };

  } catch (e) {
    // Compensations in reverse order
    if (paymentId) await voidOrRefundPayment(paymentId);
    if (reservationId) await releaseStock(reservationId);
    await cancelOrder(orderId, reason: e.message);
    throw e;
  }
}
```

Temporal делает workflow durable — даже если сервер падает в середине, workflow продолжается с того же места после restart.

### 11.3 Workflow ID — естественная идемпотентность

В Temporal `workflow_id` — natural idempotency key. Один и тот же `workflow_id` (например, `order_id`) → один и тот же workflow instance, даже при retries client'а.

---

## 12. Cart → Order BC переход — детально

### 12.1 Где Cart живёт

Cart обычно — отдельный BC (см. Тему 3) с эфемерной persistence:

- Redis / DynamoDB / hot SQL table.
- Schema: `cart_id`, `customer_id` (optional, guest carts), `items`, `totals`, `applied_promo`, `expires_at`.
- TTL: 30 дней inactivity.

### 12.2 Cart → Order — checkout transition

При нажатии "Place Order":

1. Cart Service: validate cart (items still exist, prices valid, customer logged in)
2. Cart Service: snapshot cart → freeze prices, items
3. Cart Service: emit `CartCheckoutStarted(cart_snapshot, customer, address, idempotency_key)`
4. Order Service: receive `CartCheckoutStarted`
5. Order Service: CreateOrder from snapshot, state=PENDING
6. Order Service: emit `OrderCreated`
7. Saga proceeds (Stages 2-7)
8. On `OrderConfirmed`: Cart Service → mark cart as converted, no further mutations
9. On `OrderCancelled`: Cart Service → cart remains, customer can retry

### 12.3 Anti-Corruption Layer Cart→Order

Cart model и Order model разные. Не делайте `Order = Cart + extra fields`.

- **Cart:** mutable, no commitment, prices may change.
- **Order:** immutable snapshot, committed pricing, customer info frozen.

ACL на границе: `OrderFactory.fromCartSnapshot(snapshot)` → создаёт Order с copied (snapshotted) данными, не shared references.

### 12.4 Прайсинг при checkout

В момент checkout пересчитываются:

- Final prices (с promo, taxes, shipping).
- Inventory check (reservation potential).
- Address validation, shipping rate.

Если prices изменились между cart view и checkout — должен быть explicit confirmation customer'у. Не silent. Frozen snapshot после confirmation.

---

## 13. Observability — обязательная часть Saga

### 13.1 Что мониторить

- [ ] Saga instance lifecycle (started, completed, failed)
- [ ] Saga step durations (per step latency)
- [ ] Compensation rate (% saga'ов которые triggered compensations)
- [ ] Stuck sagas (no progress for > X minutes)
- [ ] Outbox backlog size (events waiting to publish)
- [ ] Inbox processing lag (event → processing time)
- [ ] Per-step failure rates
- [ ] Stranded inventory reservations (alert if reservation hold > business timeout)
- [ ] Compensation failures (these need human attention)
- [ ] Pivot transaction failure rate (rare but catastrophic)

### 13.2 Distributed tracing

Каждый event в outbox должен нести `traceparent` (W3C Trace Context). Это даёт unified view в Jaeger/Datadog/Tempo:

```text
Trace: checkout-12345
├── span: OrderService.createOrder         [50ms]
├── span: InventoryService.reserve         [80ms]
├── span: PaymentService.authorize         [200ms]
├── span: PaymentService.capture (pivot)   [300ms]
├── span: OrderService.confirm             [40ms]
└── span: ShipmentService.create           [150ms]
total: 820ms
```

### 13.3 Stuck saga remediation

Если saga застряла:

- В choreography: hard to detect, нужен timeout-based monitor по `created_at + state`.
- В orchestration: orchestrator знает state, может alert.

Action options:

- Auto-retry retryable activities.
- Manual intervention queue.
- Force-compensate — manual saga rollback button.
- Force-complete — manual override (эскалация).

---

## 14. Anti-patterns Saga — что НЕ делать

| Anti-pattern | Описание | Правильно |
|---|---|---|
| Synchronous saga via REST chain | Service A calls B which calls C synchronously — это distributed monolith, не saga | Async messaging + compensations |
| No compensations | "Если payment fail, потом разберёмся" | Каждый step имеет compensation, кодом, на этапе дизайна |
| Compensation = inverse SQL | "Просто DELETE то что INSERT'или" | Compensation = бизнес-операция (refund, не DELETE payment) |
| Compensations не idempotent | Refund retry = double refund | Каждая compensation idempotent |
| No timeouts | Saga висит вечно ожидая response | Per-step timeouts + global saga timeout |
| God-orchestrator | Один orchestrator на 50 sagas | Один orchestrator на 1 type of saga |
| Same DB shared между BC | Workaround для transactions | Каждый BC — своя БД, общение через events |
| No outbox | Direct `kafka.publish()` в коде | Outbox + relay |
| No inbox | Consumer без dedup | Inbox table |
| Compensation после pivot | "Если что — рефанд автоматически" | После pivot — fix-forward, manual oversight |
| Saga в синхронном UI | Customer ждёт 5+ секунд checkout | Async UI + status polling |
| Compensation chain неконсистентна | Часть compensations выполнились, часть нет | Persistent saga state + retry compensations |
| Lost compensations | Process died во время compensation | Durable execution (Temporal-style) |
| Cyclic event dependencies | A subscribes to B, B subscribes to A | Чёткое event flow direction |
| Schema events не versioned | Изменение event payload ломает consumers | Schema registry + backward compatibility |

---

## 15. Связь с другими темами

- **Тема 1** — checkout idempotency у Stripe/Shopify — это часть outbox/inbox механики.
- **Тема 2** — IBM Sterling, Manhattan, fabric OMS реализуют orchestration internally; их API — это Saga API.
- **Тема 3** — Sagas работают между BC, координируют aggregates через id references.
- **Тема 4** — Saga state machine = FSM, реализованная через Temporal/Camunda. Compensations = compensating transitions.
- **Тема 6** — Payment integration с idempotency keys и 3DS — это Saga step с особенностями.
- **Тема 7** — Logistics integration — отдельный saga step или sub-saga.
- **Тема 9** — Returns process — самостоятельная saga, часто длинная (недели).

---

## 16. Чек-лист — production-grade checkout Saga

- [ ] Saga design decision: choreography / orchestration / hybrid
- [ ] Workflow engine выбран (Temporal/Step Functions/Camunda/in-house)
- [ ] Каждый step имеет idempotency key
- [ ] Каждый compensable step имеет defined compensation
- [ ] Pivot transaction явно идентифицирован
- [ ] Compensations в reverse order
- [ ] Outbox pattern для всех cross-service events
- [ ] Inbox pattern для всех consumers
- [ ] Event schema versioned (CloudEvents)
- [ ] Distributed tracing (`traceparent` в events)
- [ ] Saga instance state persistent (Temporal/DB)
- [ ] Per-step timeouts + global saga timeout
- [ ] Stuck saga detection + alert
- [ ] Inventory reservation TTL + auto-release
- [ ] Customer-facing saga status visible (web/email)
- [ ] Compensation failures escalate to manual queue
- [ ] Saga metrics: completion rate, compensation rate, latency p99
- [ ] Tests: each step failure → correct compensation chain
- [ ] Tests: idempotency of every step (replay same event 10x)
- [ ] Tests: pivot transaction failure scenarios
- [ ] Runbook for stuck/failed saga manual remediation
- [ ] Saga workflow versioning strategy (для hot updates)

---

## 17. Источники

### Foundational papers

- Garcia-Molina, Hector & Salem, Kenneth (1987). "Sagas." Princeton University. Original paper introducing the concept.
- Saga Transactions: what's old is new again — dimosr

### Saga Pattern overview

- Saga Pattern — microservices.io
- Saga Design Pattern — Azure Architecture Center
- Saga choreography pattern — AWS Prescriptive Guidance
- Saga orchestration pattern — AWS Prescriptive Guidance
- Saga Pattern in Microservices Mastery — Temporal
- Understanding the Saga Pattern — DevX
- How to Implement the Saga Pattern — OneUptime
- Saga Pattern Spring Boot + Orkes Conductor — Baeldung
- Saga Pattern in Distributed Transactions Go Examples
- Saga Pattern in Microservices — Baeldung CS

### 2PC vs Saga vs TCC

- Patterns for distributed transactions — Red Hat Developer
- Distributed transaction patterns compared — Red Hat
- Saga vs 2PC — Baeldung CS
- Saga vs 2PC vs TCC — Atomikos
- Saga vs 2PC — GeeksforGeeks
- Distributed Transaction Masterclass — Developer's Voice
- Mastering Distributed Transactions: 2PC to Saga — Aseem

### Choreography vs Orchestration

- Saga Orchestration vs Choreography — Temporal
- Saga Orchestration vs Choreography Trade-offs — Alok
- Choreography vs Orchestration in Microservices — Sapan Kumar
- Real Tradeoffs of Saga Orchestration vs Choreography — Stackademic
- IEEE comparison Choreography vs Orchestration Saga
- Saga pattern Choreography and Orchestration — Blogs4devs

### Outbox Pattern

- Reliable Microservices Data Exchange With the Outbox Pattern — Debezium
- Revisiting the Outbox Pattern — Decodable
- Outbox Pattern with Apache Kafka — Axual
- Transactional Outbox Pattern — SeatGeek ChairNerd
- Step-by-Step Guide to Transactional Outbox Pattern with Kafka
- Implementing the Outbox Pattern — DZone
- Transactional Outbox with Debezium demo — GitHub
- Kafka Connect Transactional Outbox Debezium — Lydtech
- Outbox pattern for PostgreSQL+Kafka with Debezium — Florian Courouge

### Inbox Pattern / Idempotent Consumer

- Idempotent Consumer Pattern — microservices.io
- Implementing the Inbox Pattern — Milan Jovanović
- Achieving Idempotency with the Inbox Pattern — Rafael Andrade
- Outbox, Inbox patterns and delivery guarantees — Event-Driven.io
- Idempotent Consumer Pattern in .NET — Milan
- Inbox Pattern in Microservices — OneUptime
- Handling duplicate messages — Idempotent consumer pattern — microservices.io
- Awesome Software Architecture — Inbox Pattern

### Kafka Exactly-Once

- Kafka Idempotent Consumer & Transactional Outbox — Lydtech
- Exactly-Once Semantics in Kafka — Conduktor
- Exactly-once Semantics with Kafka Transactions — Strimzi
- Exactly-once Semantics is Possible: Apache Kafka — Confluent
- Idempotent Producer — Apache Kafka
- Idempotent Processing with Kafka — Nejc Korasa
- Reliable Event-Driven with Kafka, Outbox, EOS — JCG

### Workflow Engines

- Temporal Saga implementation — DEV Federico Bevione
- AWS Step Functions vs Temporal — readysetcloud
- Best Temporal alternatives — Akka
- GCP Workflows vs AWS Step Functions vs Temporal — DZone
- BPMN and Microservices Orchestration — Camunda
- Temporal vs Step Functions — Temporal Community Forum

### Inventory Reservation & Eventual Consistency

- Managing Inventory Reservation in SAGA — DEV jackynote
- Inventory Reservation with Redis — OneUptime
- Why Real-Time Inventory Breaks Down — Bizowie
- Eventually Consistent: Not What You Were Expecting — ACM Queue
- 10 Ways to Prevent Overselling in eCommerce — OneCart

### Compensation, Pivot, Semantic Locks

- Implementation Patterns: Outbox, Idempotency, Saga Pivots — System Overflow
- Saga Pattern for Resilient Flight Booking — DZone
- Microservices Patterns: SAGA — Abhinav Thakur
- Saga Design Pattern Building Reliable Workflows — TheLinuxCode

---

## Related

- [[Research - Order Architecture]] — индекс серии Order
- [[Research - Order (1) Domain-Driven Design]] — domain events как messaging contract
- [[Research - Order (2) State Machine FSM]] — FSM как state-машина для Process Manager
- [[Research - Order (5) Payment Integration]] — Payment в качестве saga step с idempotency-keys
- [[Research - Order (6) Logistics Integration]] — Shipment в качестве saga step и pivot
- [[Research - Cart Architecture (5) State Management and UX]] — cart-side state machine
- [[Backend]] — Outbox/Inbox присутствуют в backend архитектуре
- [[Loyality Project]]
