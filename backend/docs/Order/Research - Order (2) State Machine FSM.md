---
tags:
  - project/loyality
  - backend
  - order
  - fsm
  - state-machine
  - research
type: research
date: 2026-04-29
aliases: [Order FSM, Order State Machine, Order Status Model]
cssclasses: [research]
status: active
parent: "[[Research - Order Architecture]]"
project: "[[Loyality Project]]"
component: backend
---

# Research — Order (2) State Machine FSM

> Канонические статусы Order, FSM-переходы, terminal states, compensating transitions, идемпотентность переходов, замена boolean-флагов на FSM. Включает разделение на ортогональные FSM (financial + fulfillment).

## TL;DR — ключевые выводы

1. Order — это FSM-aggregate, а не CRUD-сущность с кучей булевых флагов. Финальная модель: state колонка (enum), таблица разрешённых переходов, явная FSM в коде.
2. Канонический FSM: `Created → Paid → Fulfilled → Shipped → Delivered → Closed` + ветви `Cancelled`, `Refunded`, `Returned`. Реальные системы делят его на две ортогональные FSM (financial + fulfillment), как Shopify.
3. Boolean explosion (`is_paid`, `is_shipped`, `is_cancelled`) — главный антипаттерн. 8 boolean флагов = 256 потенциальных комбинаций, из которых валидно ~10. FSM делает невалидные состояния непредставимыми.
4. Idempotent transitions: `transition(X→X)` — no-op (re-delivery same event). `transition(X→Y) valid` → execute. `transition(X→Z) invalid` — reject с 409 Conflict, не silently игнорировать.
5. Compensating transitions ≠ inverse transitions. `Shipped → Returned` — не "обратный путь" к Created, а forward переход к новому terminal-у. История сохраняется.
6. Terminal states (Cancelled, Closed, Refunded) — не имеют outgoing transitions. Гарантируются constraint'ом БД и кодовым FSM.
7. Guard conditions проверяют не только current state, но и контекст (payment captured? inventory reserved?). Без guards FSM — игрушка.
8. Реализация: enum + transition table + repository pattern для простых случаев; библиотеки (Spring State Machine, XState, python-statemachine, Akka FSM) для сложных; event sourcing — top-tier.
9. **Loyality FSM (см. §15)** — специфичная для проекта: cross-border dropship без собственного склада. Состояния: `PENDING → PAID → PROCURED → ARRIVED_IN_RU → IN_LAST_MILE → AWAITING_PICKUP → DELIVERED → CLOSED` + `ON_HOLD` (semantic lock для passport-fail / customs-rejected / stuck-in-CN). Между `PAID` и `PROCURED` — **manual manager-action** (вручную выкупить в китайском маркетплейсе и вставить китайский трек), который запускает создание DobroPost shipment. Между `PROCURED` и `ARRIVED_IN_RU` — автоматический переход по webhook ДоброПост (status_id 648/649). Order : Shipment = **1 : 2** (cross-border + last-mile).

---

## 1. Зачем нужна FSM для Order — мотивация

### 1.1 Реальная история без FSM

Типичная Order-таблица в legacy системе:

```sql
CREATE TABLE orders (
    id            BIGINT PRIMARY KEY,
    is_created    BOOLEAN,
    is_paid       BOOLEAN,
    is_fulfilled  BOOLEAN,
    is_shipped    BOOLEAN,
    is_delivered  BOOLEAN,
    is_cancelled  BOOLEAN,
    is_returned   BOOLEAN,
    is_refunded   BOOLEAN,
    paid_at       TIMESTAMP,
    shipped_at    TIMESTAMP,
    -- ...20+ more columns
);
```

Проблемы:

1. `is_cancelled = TRUE && is_shipped = TRUE` — возможно? Иногда да, иногда нет.
2. `is_paid = FALSE && is_refunded = TRUE` — bug, но БД позволяет.
3. Order check status: `if (o.is_paid && !o.is_cancelled && !o.is_returned && o.is_shipped && !o.is_delivered)` — 5 boolean условий, нечитаемо.
4. Каждый новый статус → новая колонка → миграция всех queries.
5. Тестировать невозможно: 2^8 = 256 комбинаций boolean флагов.

### 1.2 Реальная история с FSM

```sql
CREATE TABLE orders (
    id              BIGINT PRIMARY KEY,
    state           VARCHAR(32) NOT NULL,
    state_updated_at TIMESTAMP NOT NULL,
    -- timestamps только для states которые произошли:
    paid_at         TIMESTAMP,
    shipped_at      TIMESTAMP,
    delivered_at    TIMESTAMP,
    cancelled_at    TIMESTAMP,
    -- ...
    CONSTRAINT valid_state CHECK (state IN (
        'created', 'paid', 'fulfilled', 'shipped',
        'delivered', 'cancelled', 'refunded', 'returned', 'closed'
    ))
);
```

Преимущества:

1. Невалидные состояния невозможны — state всегда одно из enum значений.
2. Запросы простые: `WHERE state = 'shipped'`.
3. Новый статус → добавление в enum, никаких миграций boolean колонок.
4. Тестировать ясно: 9 states × N events = M valid transitions.

### 1.3 Принцип: "make illegal states unrepresentable"

Знаменитая фраза Yaron Minsky (Jane Street). FSM — конкретный инструмент применения этого принципа к Order.

---

## 2. Канонический Order FSM

### 2.1 Базовая модель — happy path

```text
                 ┌──────────────────────────────┐
                 │   Created (initial)          │
                 │   * order_id, items, totals  │
                 │   * stock not reserved yet   │
                 │   * payment not initiated    │
                 └────────────┬─────────────────┘
                              │ event: PaymentAuthorized
                              ▼
                 ┌──────────────────────────────┐
                 │   Paid                       │
                 │   * payment captured/auth'd  │
                 │   * stock reserved           │
                 └────────────┬─────────────────┘
                              │ event: FulfillmentStarted
                              ▼
                 ┌──────────────────────────────┐
                 │   Fulfilled (in_progress)    │
                 │   * picked, packed           │
                 │   * carrier assigned         │
                 └────────────┬─────────────────┘
                              │ event: ShipmentDispatched
                              ▼
                 ┌──────────────────────────────┐
                 │   Shipped                    │
                 │   * tracking number issued   │
                 └────────────┬─────────────────┘
                              │ event: DeliveryConfirmed
                              ▼
                 ┌──────────────────────────────┐
                 │   Delivered                  │
                 │   * customer received        │
                 └────────────┬─────────────────┘
                              │ event: ReturnPeriodElapsed
                              ▼
                 ┌──────────────────────────────┐
                 │   Closed (terminal)          │
                 └──────────────────────────────┘
```

### 2.2 Полная модель с ветвями

```text
Created ─────► Paid ─────► Fulfilled ─────► Shipped ─────► Delivered ─────► Closed (T)
   │             │             │                │               │
   │             │             │                │               │
   ▼             ▼             ▼                ▼               ▼
Cancelled    Cancelled    Cancelled       (no cancel,       Returned ─────► Refunded (T)
   (T)       + Refund      + Refund        return only)
                (T)        + StockRelease
                                                              (or partial)
                                                              ▼
                                                         PartiallyReturned
                                                              │
                                                              ▼
                                                         PartiallyRefunded
```

(T) — terminal state.

### 2.3 Полная transition table

| From state | Event | To state | Guards | Side effects |
|---|---|---|---|---|
| Created | PaymentAuthorized | Paid | `payment.amount == order.total` | Reserve stock, send confirmation email |
| Created | OrderCancelled | Cancelled | – | Release any soft holds |
| Created | PaymentFailed | Cancelled | – | Notify customer |
| Paid | FulfillmentStarted | Fulfilled | Stock reserved | Trigger pick/pack |
| Paid | OrderCancelled | Cancelled | – | Refund payment, release stock |
| Fulfilled | ShipmentDispatched | Shipped | Carrier confirmed | Send tracking email |
| Fulfilled | OrderCancelled | Cancelled | – | Refund + release + abort fulfillment |
| Shipped | DeliveryConfirmed | Delivered | – | Trigger return-window timer |
| Shipped | DeliveryFailed | DeliveryFailed | – | Reschedule or return-to-sender |
| Delivered | ReturnRequested | ReturnInProgress | Within return window | Generate RMA |
| Delivered | ReturnPeriodElapsed | Closed | – | Mark final |
| ReturnInProgress | ReturnReceived | Returned | – | Inspect items |
| Returned | RefundIssued | Refunded | Inspection passed | Capture refund |
| Returned | PartialRefundIssued | PartiallyRefunded | Some items kept | Partial refund |
| Cancelled | – | (terminal) | – | – |
| Refunded | – | (terminal) | – | – |
| Closed | – | (terminal) | – | – |

### 2.4 Two-FSM model (Shopify-style)

В реальности один FSM не описывает Order адекватно. Лучшая модель — две ортогональные FSM:

```text
Financial FSM:
Pending → Authorized → Paid → PartiallyRefunded → Refunded
            └─► Voided

Fulfillment FSM:
Unfulfilled → InProgress → PartiallyFulfilled → Fulfilled
                  └─► OnHold
                  └─► RequestDeclined
```

Эти FSM независимы: Order может быть `Paid + Unfulfilled` (нормально перед отгрузкой) или `PartiallyRefunded + Fulfilled` (вернули один item из трёх отгруженных). Один FSM с product-of-states вёл бы к explosion (5×5=25 vs 5+5=10).

Это formally называется orthogonal regions в UML statechart.

---

## 3. Terminal states

### 3.1 Что такое terminal state

Terminal state = состояние, из которого нет исходящих transitions. После попадания в terminal state:

- Aggregate immutable (с точки зрения lifecycle).
- Записи остаются в БД для audit/reporting.
- Никакое event не может вывести из terminal.

Из источника:

> "Terminal states must be empty and may have an annotated postcondition. Terminal states are distinguished into success and failure states. No outgoing transitions may be attached to terminal states."

### 3.2 Какие states terminal в Order

| State | Тип |
|---|---|
| Closed | success terminal — happy path complete |
| Cancelled | failure terminal — never delivered |
| Refunded | success terminal — fully refunded after return |

### 3.3 Анти-паттерн: terminal state с outgoing transition

Иногда возникает желание: "ну ладно, из Cancelled можно перейти обратно в Created, если customer передумал".

❌ Не делайте этого. Создайте новый Order. Аргументы:

- Audit confusion: какой `cancelled_at`? Стереть?
- Saga compensations уже выполнились — released inventory, refund issued, customer notified.
- Аналитика поломана: cancel rate включает "псевдо-cancelled".
- Side-effects идемпотентность теряется.

Правильное решение: Cancelled — terminal. Customer передумал — новый Order. Это honest и audit-safe.

### 3.4 Quasi-terminal: long-running terminals

Closed — terminal, но customer всё равно может через год прийти с warranty claim или dispute. Решение:

- Сам Order в Closed остаётся.
- Создаётся отдельный aggregate WarrantyClaim или Dispute со своим FSM.
- Cross-aggregate references по id.

Это применение Vernon's "small aggregates" rule из темы 3.

---

## 4. Compensating transitions vs forward transitions

### 4.1 Различие

**Forward transition:** progressive движение по lifecycle (Created → Paid → Shipped).

**Compensating transition:** undo предыдущего forward transition при failure. Это не обратный edge в FSM — это новый forward edge в другое (часто terminal) состояние с компенсирующими side effects.

```text
❌ Не делайте:
Paid → Created (откат, потому что payment failed)

✔ Делайте:
Paid → Cancelled (forward, с compensation: release stock, refund payment)
```

Почему это важно: forward-only edges означают, что timestamp монотонно растёт, audit log линеен, side effects не нужно "откатывать", только "компенсировать".

### 4.2 Compensating actions per transition

| Forward transition | Compensating action (если failure далее по pipeline) |
|---|---|
| Created → Paid | Refund payment |
| Paid → Fulfilled | Release inventory reservation, Refund |
| Fulfilled → Shipped | Recall shipment (если возможно) или return-to-sender |
| Shipped → Delivered | Customer return (RMA), refund |
| Delivered → Returned | Restock inventory, Issue refund |

### 4.3 Saga = sequence of forward transitions с compensations

Saga — это именно эта модель:

1. Forward step → success → next forward step.
2. Forward step → failure → execute compensations for already-completed forward steps в reverse order.
3. Saga приводит aggregate либо в success-terminal (Delivered/Closed), либо в failure-terminal (Cancelled/Refunded).

> "If forward progress is not possible, it should be possible to transition backwards to the initial state through backwards transitions known as compensating actions."

В FSM-нотации это: каждое intermediate state имеет edge в failure-terminal, и этот edge несёт compensation.

### 4.4 Пример: PaymentFailed compensation chain

```text
Created → Paid (payment authorized) → Fulfilled (picked) → ❌ Shipping fails permanently
                                                              │
                                                              ▼
                                                        Cancelled
                                                        ├ Compensation 1: Cancel shipment label
                                                        ├ Compensation 2: Restock inventory
                                                        ├ Compensation 3: Refund payment
                                                        └ Compensation 4: Notify customer
```

Все compensations должны быть idempotent — если retry compensation, не должно ломаться (см. §6).

---

## 5. Boolean flags → FSM — рефакторинг

### 5.1 Знаки того, что нужна FSM

- В коде десятки `if (entity.isX && !entity.isY && entity.isZ)`.
- Регулярно появляются bug reports вида "Order shipped, но payment failed".
- Новый статус добавляется через "ну добавим ещё один boolean".
- Тесты не покрывают всех combination — да и не могут, их 2^N.

### 5.2 Replace State-Altering Conditionals with State (Joshua Kerievsky)

Каноничный refactoring. Шаги:

1. **Identify state-driven behavior** — найдите методы, ветвящиеся по комбинации booleans.
2. **Extract states as enum** — `OrderState { Created, Paid, ... }`.
3. **Add transition table** — карта `(state, event) → newState`.
4. **Replace boolean reads projection:** `isPaid := state in {Paid, Fulfilled, Shipped, Delivered, Returned, Refunded}`.
5. **Replace boolean writes** с явными transitions: `order.markPaid()` → `transition(state, PaymentAuthorized)`.
6. **Delete boolean columns** в БД, миграция: `state := derive_from_booleans(...)`.
7. **Add CHECK constraint:** `state IN (...)`.
8. **Add transition validation** в repository.

### 5.3 Migration plan для существующей системы

Это non-trivial миграция. Рекомендованный подход:

**Phase 1 — добавить колонку без удаления**

```sql
ALTER TABLE orders ADD COLUMN state VARCHAR(32);
UPDATE orders SET state = CASE
    WHEN is_returned THEN 'returned'
    WHEN is_refunded THEN 'refunded'
    WHEN is_cancelled THEN 'cancelled'
    WHEN is_delivered THEN 'delivered'
    WHEN is_shipped THEN 'shipped'
    WHEN is_fulfilled THEN 'fulfilled'
    WHEN is_paid THEN 'paid'
    ELSE 'created'
END;
ALTER TABLE orders ALTER COLUMN state SET NOT NULL;
ALTER TABLE orders ADD CONSTRAINT valid_state CHECK (state IN (...));
```

**Phase 2 — dual-write**

Код пишет одновременно в booleans и в state. Booleans — для backward compat с старыми consumers. Логика в новом коде читает только state.

**Phase 3 — найти все consumers booleans**

Grep по кодовой базе, миграция запросов, контроль через linter.

**Phase 4 — drop booleans**

После того как все consumers переехали:

```sql
ALTER TABLE orders DROP COLUMN is_paid, DROP COLUMN is_shipped, ...;
```

### 5.4 Что оставить, а что убрать

✅ **Оставить (timestamps):**

- `paid_at`, `shipped_at`, `delivered_at`, `cancelled_at` — полезны для analytics и SLA tracking.
- Они denormalized projection, но не противоречат FSM (`timestamp != null ⇔ state was/is X`).

❌ **Убрать (booleans):**

- `is_paid`, `is_shipped`, `is_cancelled` — derivable из state.
- Если в коде остаётся "удобный" boolean — `def is_paid(self): return self.state in {...}` — это проекция, не storage.

---

## 6. Idempotent transitions

### 6.1 Проблема

В distributed системе одно и то же событие может прийти дважды:

- Webhook retry от payment provider.
- Kafka at-least-once delivery.
- Network timeout + client retry.

Если `transition(Created → Paid)` исполняется дважды, что должно произойти?

### 6.2 Три уровня idempotency

**Level 1: same-state idempotent (no-op)**

```text
current_state = Paid
event = PaymentAuthorized
target_state = Paid

→ Уже в Paid. No-op. Return success.
```

Это самый частый случай — duplicate event delivery. Не throw error, просто success.

**Level 2: forward-progress idempotent**

```text
current_state = Shipped
event = PaymentAuthorized

→ Forward уже произошёл. PaymentAuthorized был обработан, мы в Shipped.
→ No-op. Return success.
```

Логика: "я уже прошёл через состояние, в которое этот event привёл бы". Обычно проверяется через event_id в outbox/inbox таблице.

**Level 3: invalid transition (reject)**

```text
current_state = Cancelled
event = ShipmentDispatched

→ Cancelled — terminal, исходящих нет.
→ Reject 409 Conflict. Логируется в alert channel.
```

### 6.3 Реализация — atomic check-and-set

```sql
-- Pessimistic пример (Postgres):
UPDATE orders
SET state = 'paid', paid_at = NOW()
WHERE id = $1
  AND state = 'created'    -- guard: must be in expected state
  AND NOT EXISTS (
      SELECT 1 FROM processed_events
      WHERE event_id = $2  -- idempotency check
  );

INSERT INTO processed_events(event_id) VALUES($2)
ON CONFLICT DO NOTHING;
```

Один atomic update:

- Если row updated → transition successful.
- Если no rows updated → либо state уже не "created" (transition concurrent), либо event уже processed.

### 6.4 Idempotency keys для domain events

Каждое domain event получает unique `event_id` (UUID). Consumer хранит processed event_ids в inbox table:

```sql
CREATE TABLE inbox_events (
    event_id UUID PRIMARY KEY,
    consumer  VARCHAR(64),
    processed_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

Consumer:

1. Begin transaction.
2. `INSERT INTO inbox_events (event_id, consumer) VALUES (...) ON CONFLICT DO NOTHING RETURNING *` — если ничего не возвращает, event already processed → commit, no-op.
3. Apply state transition.
4. Commit.

Это inbox pattern — pair с outbox pattern (тема 5).

### 6.5 Race conditions

Naive deduplication anti-pattern:

```text
1. SELECT FROM inbox WHERE event_id = X       -- not found
2. ... process event ...
3. INSERT INTO inbox (event_id)                -- success
```

Между шагами 1 и 3 второй concurrent worker может пройти то же самое — оба обработают.

Правильно: atomic INSERT с UNIQUE constraint, и либо обрабатываем (если INSERT успешен), либо skip (если duplicate key error).

---

## 7. Guard conditions

### 7.1 Что такое guard

Guard = boolean expression, который evaluates во время transition. Если false — transition не происходит.

В UML notation: `event[guard] / action`.

### 7.2 Guards в Order FSM

```text
Created → Paid    [payment.amount >= order.total]
Paid → Fulfilled  [stock.reserved == order.line_count]
Fulfilled → Shipped [carrier.label_generated]
Shipped → Delivered [delivery.signed_for OR delivery.left_at_door]
Delivered → ReturnInProgress [now() < delivered_at + return_window]
```

### 7.3 Guard order

Если несколько transitions с одного state на одно event, проверяются по порядку declaration. Первый с true guard — wins.

```text
event: PaymentReceived
transitions:
  Created --[amount >= total]-->         Paid
  Created --[amount > 0 && < total]-->   PartiallyPaid
  Created --[amount == 0]-->             remains Created (no-op)
```

### 7.4 Guards без side effects

> "Guard expressions should have no side effects."

Guards — это только predicate. Side effects (обновить inventory, отправить email) принадлежат actions на entry/exit/transition.

Anti-pattern:

```text
guard: {
    if (stock.tryReserve()) return true;   ❌ side effect!
    return false;
}
```

Правильно: reserve stock — это action, не guard. Guard проверяет что-то уже сделанное: `stock.is_reserved`.

---

## 8. Hierarchical state machines (HSM) для Order

### 8.1 Зачем

Простой Order FSM имеет 8-12 states. С добавлением OnHold (fraud check), WaitingForCustomerInput, Backordered — состояния разрастаются. UML statecharts вводят hierarchical states для уменьшения размерности.

### 8.2 Пример

```text
Order
├── Active (composite)
│   ├── Created
│   ├── Paid
│   ├── Fulfilled
│   ├── Shipped
│   └── Delivered
│
├── OnHold (composite, can enter from any Active sub-state)
│   ├── FraudReview
│   ├── PaymentPending
│   └── ManualReview
│
└── Terminal
    ├── Cancelled
    ├── Refunded
    └── Closed
```

OnHold ловит общее поведение для всех "frozen" состояний (никаких automatic transitions, требует manual intervention) без дублирования этой логики на каждом sub-state.

### 8.3 Orthogonal regions

Когда нужны две независимые FSM на одном aggregate (Shopify-style financial + fulfillment), это формально orthogonal regions:

```text
Order (composite)
├── Region A: Financial
│   Pending → Authorized → Paid → PartiallyRefunded → Refunded
│
└── Region B: Fulfillment
   Unfulfilled → InProgress → PartiallyFulfilled → Fulfilled
```

Aggregate state = (RegionA state, RegionB state). 5 × 5 = 25 combined states, но управляются 5 + 5 = 10 transition rules.

### 8.4 Когда применять

- Простой 6-state FSM — оставьте flat.
- 10+ states с явными группами — вводите hierarchy.
- Две независимые dimensions (financial vs fulfillment, business vs system) — orthogonal regions.

Не overengineering: для 80% e-commerce достаточно flat FSM.

---

## 9. Реализация FSM в коде

### 9.1 Naive — switch/case

```python
def transition(order, event):
    if order.state == 'created':
        if event == 'payment_authorized':
            order.state = 'paid'
            order.paid_at = now()
            return
        if event == 'cancel':
            order.state = 'cancelled'
            return
    elif order.state == 'paid':
        if event == 'fulfillment_started':
            order.state = 'fulfilled'
            return
        # ...
    raise InvalidTransition(order.state, event)
```

❌ Растёт квадратично. Нечитаемо. Плохо тестируется.

### 9.2 Transition table

```python
TRANSITIONS = {
    ('created', 'payment_authorized'): 'paid',
    ('created', 'cancel'): 'cancelled',
    ('paid', 'fulfillment_started'): 'fulfilled',
    ('paid', 'cancel'): 'cancelled',
    ('fulfilled', 'shipment_dispatched'): 'shipped',
    # ...
}

def transition(order, event):
    key = (order.state, event)
    if key not in TRANSITIONS:
        raise InvalidTransition(order.state, event)
    order.state = TRANSITIONS[key]
```

✔ Чисто, легко тестируется, transitions видны декларативно.

Расширение — добавить guards и actions:

```python
TRANSITIONS = {
    ('created', 'payment_authorized'): {
        'to': 'paid',
        'guard': lambda o, e: e.amount >= o.total,
        'action': lambda o, e: o.set_paid_at(now()),
    },
    # ...
}
```

### 9.3 State pattern (объектно-ориентированный)

```python
class OrderState(ABC):
    @abstractmethod
    def authorize_payment(self, order, event): ...
    @abstractmethod
    def cancel(self, order, event): ...

class CreatedState(OrderState):
    def authorize_payment(self, order, event):
        order.transition_to(PaidState())
    def cancel(self, order, event):
        order.transition_to(CancelledState())

class PaidState(OrderState):
    def authorize_payment(self, order, event):
        pass  # idempotent no-op
    def cancel(self, order, event):
        # compensation: refund payment
        order.transition_to(CancelledState())
    # ...
```

✔ Каждое state's behavior изолировано. Тесты на state-by-state basis.
❌ Boilerplate растёт.

### 9.4 Библиотеки

| Язык/Стек | Библиотека | Плюсы |
|---|---|---|
| Java/Spring | Spring State Machine | Зрелая, hierarchical, persistence, события |
| TypeScript/JS | XState | Statecharts, visualization, типизация, фронт+бэк |
| Python | python-statemachine | Декораторы, guards, validators |
| Scala/Akka | Akka FSM / Akka Typed Persistence | Actor-based, persistent |
| .NET | Stateless | Lightweight, fluent API |
| Erlang | gen_statem | Built-in OTP |

XState пример:

```typescript
const orderMachine = createMachine({
  id: 'order',
  initial: 'created',
  states: {
    created: {
      on: {
        PAYMENT_AUTHORIZED: {
            target: 'paid',
            guard: ({event}) => event.amount >= context.total,
        },
        CANCEL: 'cancelled',
      }
    },
    paid: {
      entry: 'reserveStock',
      on: { FULFILLMENT_STARTED: 'fulfilled' }
    },
    cancelled: { type: 'final' },  // terminal
    // ...
  }
});
```

XState decora plus: визуализация в Stately Studio, можно показать domain experts.

### 9.5 Database-driven FSM

```sql
CREATE TABLE order_state_transitions (
    from_state VARCHAR(32),
    event      VARCHAR(64),
    to_state   VARCHAR(32),
    PRIMARY KEY (from_state, event)
);
```

Configuration в БД — гибко, но усложнить debugging. Подходит, когда non-developers должны менять transitions (admin UI). Risky: легко поломать целостность, нужен валидатор.

### 9.6 Event sourcing — FSM derived from events

В event-sourced подходе state не хранится — derive'ится replay'ем events:

```text
events:
  [OrderCreated]
  [PaymentAuthorized]
  [StockReserved]
  [ShipmentDispatched]

current state = fold(events, apply_event_to_state, initial=None)
              = Shipped
```

`apply` функция и есть transition function FSM. Snapshots ускоряют replay для long-lived aggregates.

> "The benefit of event sourcing is that you never need to store State itself. Instead, you rely on the Output of a service to reconstitute state."

---

## 10. Persistence — как хранить FSM

### 10.1 Минимум

```sql
CREATE TABLE orders (
    id              BIGINT PRIMARY KEY,
    state           VARCHAR(32) NOT NULL,
    state_updated_at TIMESTAMP NOT NULL,
    state_version   INT NOT NULL DEFAULT 0,  -- optimistic locking
    -- ...domain fields
    CONSTRAINT valid_state CHECK (state IN (
        'created', 'paid', 'fulfilled', 'shipped',
        'delivered', 'cancelled', 'returned',
        'refunded', 'closed'
    ))
);
```

### 10.2 State history (audit log)

```sql
CREATE TABLE order_state_history (
    id            BIGSERIAL PRIMARY KEY,
    order_id      BIGINT REFERENCES orders(id),
    from_state    VARCHAR(32) NOT NULL,
    to_state      VARCHAR(32) NOT NULL,
    event_type    VARCHAR(64) NOT NULL,
    event_id      UUID UNIQUE NOT NULL,  -- idempotency
    actor         VARCHAR(128),
    metadata      JSONB,
    occurred_at   TIMESTAMP NOT NULL
);

CREATE INDEX idx_history_order ON order_state_history(order_id, occurred_at);
```

UNIQUE на event_id обеспечивает idempotency: дубликатное событие даст constraint violation, обработчик может safely retry.

### 10.3 Optimistic locking

```sql
UPDATE orders
SET state = 'paid', state_version = state_version + 1, state_updated_at = NOW()
WHERE id = $1
  AND state = 'created'
  AND state_version = $2;  -- expected version

-- if 0 rows updated: либо state changed by concurrent, либо version mismatch
```

### 10.4 Postgres CHECK constraint для terminal states

Постгрес CHECK не может references rows previous state. Но можно через trigger:

```sql
CREATE OR REPLACE FUNCTION enforce_order_transitions() RETURNS TRIGGER AS $$
BEGIN
    IF OLD.state IN ('cancelled', 'refunded', 'closed')
       AND NEW.state != OLD.state THEN
        RAISE EXCEPTION 'Cannot transition from terminal state %', OLD.state;
    END IF;
    -- Можно добавить полную transition table check здесь
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER order_state_transition_check
BEFORE UPDATE ON orders
FOR EACH ROW
WHEN (OLD.state IS DISTINCT FROM NEW.state)
EXECUTE FUNCTION enforce_order_transitions();
```

Это последний рубеж защиты. Основная проверка — в коде, БД — defensive.

---

## 11. Тестирование FSM

### 11.1 Что тестировать

1. **Each valid transition:** для каждого `(state, event) → newState` в transition table написать test.
2. **Each invalid transition rejected:** для каждого `(state, event)` НЕ в table — должна быть `InvalidTransitionError`.
3. **Idempotency:** дважды apply same event → итог как от одного раза.
4. **Guards:** valid с true guard, rejected с false guard.
5. **Terminal states:** no outgoing transitions.
6. **Compensating transitions:** correct cleanup.
7. **Concurrent transitions:** только один преуспеет (optimistic lock).

### 11.2 Property-based testing

Используйте hypothesis (Python) или fast-check (TS) для генерации последовательностей событий и проверки инвариантов:

- Order никогда не оказывается в state, не определённом enum.
- Total денег монотонно неубывает (без partial refunds — иначе сложнее).
- `paid_at != null ⇔ state ∉ {created, cancelled}`.
- Состояние всегда reachable из `created` через valid transitions.

### 11.3 Visual model checking

XState и Stately Studio позволяют визуализировать statechart и проверить его mathematically для unreachable states, dead ends, missing transitions.

---

## 12. Антипаттерны FSM для Order

| Антипаттерн | Описание | Правильно |
|---|---|---|
| Boolean explosion | 8 boolean флагов вместо state column | Single state column + FSM |
| Status as string без validation | state колонка без CHECK, любая строка | CHECK constraint + enum |
| Generic CRUD events | `OrderUpdated` event без semantic | Domain events: `OrderShipped` |
| God state machine | Один FSM на 30+ states | Hierarchical или orthogonal regions |
| Implicit transitions | Transition выполняется через `setStatus()` без validation | Explicit named operations: `markShipped()` |
| Reverse transitions | `Cancelled → Created` | Forward-only, terminal final |
| Side effects в guards | Guard reserves stock | Guards читают, actions пишут |
| Synchronous side effects в transitions | Send email внутри DB transaction | Outbox pattern, separate worker |
| State + boolean combinations | `state = 'paid' + is_refunded = true` | Только state — derive booleans |
| Magic transitions | `is_paid = true` через UPDATE без проверки | Пройти через FSM |
| No idempotency | Re-delivery event ломает state | Inbox pattern + atomic check-and-set |
| Tied to UI labels | State names = UI strings | State — domain concept; UI label — projection |

---

## 13. Real-world FSM — соответствие Теме 1

Связь с Темой 1 (E-commerce гиганты):

| Платформа | Подход |
|---|---|
| Amazon SP-API | Один FSM с PartiallyShipped как first-class state |
| Shopify | Two orthogonal FSMs (financial + fulfillment) |
| Wildberries | Two FSMs by ownership (wbStatus + supplierStatus) |
| Ozon | One FSM + substatuses (orthogonal sub-regions) |
| AliExpress | One FSM с SELLER_PART_SEND_GOODS first-class |

Все они применяют принципы из этой темы: явный enum, valid transitions, terminal states, domain events для transitions.

---

## 14. Чек-лист — FSM-grade Order

- [ ] state — enum/varchar с CHECK constraint, не boolean флаги
- [ ] Valid transitions documented (table или declarative DSL)
- [ ] Каждый transition имеет уникальный event id (idempotency)
- [ ] Guards отделены от actions (guards без side effects)
- [ ] Terminal states явно помечены, no outgoing transitions
- [ ] Compensating transitions определены для каждого failure scenario
- [ ] State transitions audit logged (`order_state_history` table)
- [ ] Optimistic locking через `state_version` или `updated_at`
- [ ] DB trigger как defensive layer (forbidden transitions)
- [ ] Idempotent transitions: same-state event → no-op
- [ ] Invalid transitions → 409 Conflict с alert
- [ ] Inbox/Outbox patterns для distributed event delivery
- [ ] Two-FSM model рассмотрена (financial + fulfillment)
- [ ] FSM покрыт тестами: each valid + each invalid + idempotency
- [ ] State machine визуализирован для onboarding domain experts
- [ ] State имена на ubiquitous language, не технические
- [ ] Нет «magic» transitions через прямые UPDATE
- [ ] Booleans derived as projections, не stored

---

## 15. Loyality FSM: cross-border dropship (manager-purchase + 2-leg shipment)

> Конкретная FSM для нашего проекта Loyality. Отличается от каноничной (§2) тем, что **товара нет на складе на момент Order'а** — менеджер выкупает его на китайском маркетплейсе вручную, и доставка состоит из двух последовательных Shipment-ов (cross-border + last-mile). Эта секция фиксирует целевую FSM модуля `order` для будущей реализации.

### 15.1 Бизнес-контекст

Loyality — каталог товаров, скопированных из китайских маркетплейсов (Poizon / Taobao / 1688), с публикацией для российских покупателей. **Собственного склада нет.** Поток:

1. Customer заказывает в каталоге, выбирает российский ПВЗ, оплачивает.
2. Менеджер видит новый paid order в админке, вручную выкупает в китайском маркетплейсе.
3. Менеджер вставляет китайский tracking number в карточке Order'а.
4. Backend автоматически создаёт DobroPost shipment (cross-border CN→RU + таможенное оформление).
5. После прибытия в РФ — backend автоматически создаёт last-mile shipment у российского carrier'а до выбранного ПВЗ.
6. Customer забирает в ПВЗ.

Подробно flow и shipment-цепочка описаны в [[Research - Order (6) Logistics Integration]] §16.

### 15.2 Order FSM — целевая модель

```text
                  ┌──────────────┐
                  │   PENDING    │ initial — заказ создан, оплата не подтверждена
                  └──────┬───────┘
                         │ event: PaymentCaptured
                         ▼
                  ┌──────────────┐
                  │     PAID     │ оплата прошла, ждёт менеджера для выкупа
                  └──────┬───────┘
                         │ event: ManagerProcured (китайский трек привязан)
                         ▼
                  ┌──────────────┐
                  │   PROCURED   │ DobroPost cross-border shipment создан
                  └──────┬───────┘
                         │ event: CrossBorderArrived (status_id ∈ {648, 649} от ДоброПост)
                         ▼
                  ┌──────────────────┐
                  │  ARRIVED_IN_RU   │ товар на складе ДоброПост в РФ
                  └──────┬───────────┘
                         │ event: LastMileShipmentCreated (российский carrier подтвердил)
                         ▼
                  ┌──────────────┐
                  │ IN_LAST_MILE │ российский carrier везёт к ПВЗ
                  └──────┬───────┘
                         │ event: DeliveredToPickupPoint
                         ▼
                  ┌──────────────────┐
                  │  AWAITING_PICKUP │ customer должен забрать (срок хранения ~7 дней)
                  └──────┬───────────┘
                         │ event: CustomerPickedUp
                         ▼
                  ┌──────────────┐
                  │  DELIVERED   │ terminal-success
                  └──────┬───────┘
                         │ event: ReturnPeriodElapsed
                         ▼
                  ┌──────────────┐
                  │   CLOSED (T) │
                  └──────────────┘
```

### 15.3 Полная transition table (с ветвями отмены/возврата)

| From | Event | To | Guards | Side effects (compensations) |
|------|-------|-----|---------|-------------------------------|
| PENDING | PaymentCaptured | PAID | `payment.amount == order.total` | Уведомление менеджеру в админ-панель |
| PENDING | PaymentFailed | CANCELLED | – | – |
| PENDING | OrderCancelled (customer) | CANCELLED | – | Void payment authorization |
| PAID | ManagerProcured(`incomingDeclaration`) | PROCURED | `len(incomingDeclaration) < 16`, формат трека | **Создать DobroPost Shipment** (`POST /api/shipment`); установить статус Order → PROCURED |
| PAID | OrderCancelled (manager) | CANCELLED + REFUND | reason ∈ {OUT_OF_STOCK_AT_SUPPLIER, FRAUD, BAD_ADDRESS} | Refund customer'у через PSP |
| PAID | OrderCancelled (customer) | CANCELLED + REFUND | до начала выкупа | Refund customer'у |
| PROCURED | CrossBorderArrived | ARRIVED_IN_RU | `dobropost.status_id ∈ {648, 649}` | **Создать last-mile Shipment** у российского carrier'а |
| PROCURED | DobroPostCustomsRejected | CANCELLED + REFUND + RECALL | `dobropost.status_id ∈ {541..546, 590xxx}` | Refund customer; алерт менеджеру для решения судьбы посылки в РФ-складе |
| PROCURED | DobroPostPassportInvalid | ON_HOLD (semantic lock) | webhook DaData: `passportValidationStatus=false` | Escalation customer service для запроса корректных паспортных данных; cross-border остановлен на таможне |
| ON_HOLD | PassportFixed | PROCURED | новые паспортные данные → `PUT /api/shipment` к ДоброПост | – |
| ON_HOLD | OrderCancelled | CANCELLED + REFUND | manual decision | Recall товара или списание (rare) |
| PROCURED | StuckInCN (timeout > 14 дней) | ON_HOLD (semantic lock) | nightly cron job детектирует | Алерт менеджеру; manual investigation в китайском маркетплейсе |
| ARRIVED_IN_RU | LastMileShipmentCreated | IN_LAST_MILE | российский carrier подтвердил создание | Email customer'у с tracking российского carrier'а |
| ARRIVED_IN_RU | LastMileCreationFailed | ARRIVED_IN_RU (retry) | – | Retry с другим carrier'ом (failover); алерт после N неуспешных попыток |
| IN_LAST_MILE | DeliveredToPickupPoint | AWAITING_PICKUP | – | Notification customer'у "готов к выдаче" |
| IN_LAST_MILE | LastMileFailed (return-to-sender) | RETURNING_TO_RU_WAREHOUSE | carrier-side failure | – |
| AWAITING_PICKUP | CustomerPickedUp | DELIVERED | – | Trigger return-window timer (по закону РФ — 14 дней) |
| AWAITING_PICKUP | StoragePeriodExpired | RETURNING_TO_RU_WAREHOUSE | срок хранения в ПВЗ истёк (7 дней дефолт) | Carrier авто-возврат на склад |
| AWAITING_PICKUP | CustomerRefused | RETURNING_TO_RU_WAREHOUSE | customer не пришёл / отказался | – |
| RETURNING_TO_RU_WAREHOUSE | ReturnedToWarehouse | NOT_DELIVERED | – | Списание / повторная попытка / refund по решению менеджера |
| DELIVERED | ReturnRequested | RETURN_IN_PROGRESS | в пределах 14-дневного окна | Создать reverse last-mile shipment, RMA |
| DELIVERED | ReturnPeriodElapsed | CLOSED | – | Финализация |
| RETURN_IN_PROGRESS | ReturnReceived | RETURNED | – | Inspection + refund |

### 15.4 Two-FSM модель: Order FSM ⊥ Shipment-chain FSM

Loyality применяет принцип Shopify-style ortogonal FSMs (см. §2.4), но в специфичной форме: **Order FSM ортогонален Shipment-chain FSM**, а не financial/fulfillment.

**Order FSM (бизнес-уровень):**

```text
PENDING → PAID → PROCURED → ARRIVED_IN_RU → IN_LAST_MILE → AWAITING_PICKUP → DELIVERED → CLOSED
                    │             │              │
                    └────► ON_HOLD                └──┐
                                                     ▼
                                          RETURNING_TO_RU_WAREHOUSE → NOT_DELIVERED
                                                     │
                                                     ▼
                                                CANCELLED + REFUND
```

**Shipment-chain FSM (физический уровень):**

```text
[Shipment #1: DobroPost cross-border]
DRAFT → CREATED → IN_TRANSIT_CN → AT_CUSTOMS_CN → AT_CUSTOMS_RU → CLEARED → READY_FOR_LAST_MILE → HANDED_OVER
   │
   ▼
[Shipment #2: Russian carrier last-mile]   ← создаётся когда #1 в HANDED_OVER
PRE_TRANSIT → IN_TRANSIT → AT_PICKUP_POINT → DELIVERED
                              │
                              └──► STORAGE_EXPIRED → RETURNED
```

Order FSM «следует» за финальными статусами Shipment-chain, но не равен им. Например, когда Shipment #1 переходит в `READY_FOR_LAST_MILE` (status_id=648 у ДоброПост) — Order переходит в `ARRIVED_IN_RU`. Это связь через event-listening.

### 15.5 ON_HOLD как semantic lock

Состояние `ON_HOLD` — типичный пример **semantic lock countermeasure** из теории Saga (§4.3): aggregate помечается «временно заморожен», compensations не выполняются автоматически, ждёт ручного решения менеджера.

Триггеры `PROCURED → ON_HOLD`:

- `passportValidationStatus=false` от DaData webhook ДоброПост.
- Cross-border shipment застрял в Китае > 14 дней без прогресса (nightly cron).
- Таможенный отказ (статусы 541–546, 590xxx у ДоброПост).
- Manual override менеджером (подозрение на fraud у customer'а).

Пока Order в `ON_HOLD`:

- Никаких автоматических compensation-actions.
- Customer видит "Товар на проверке, мы свяжемся" (без деталей).
- Алерт в Slack/Telegram канал customer service.
- TTL: если 30 дней нет действий — автоматически `CANCELLED + REFUND`.

### 15.6 Persistence (postgres-схема)

```sql
CREATE TABLE orders (
    id                BIGINT PRIMARY KEY,
    state             VARCHAR(32) NOT NULL,
    state_updated_at  TIMESTAMP NOT NULL,
    state_version     INT NOT NULL DEFAULT 0,

    -- Customer
    customer_id       BIGINT NOT NULL,

    -- Pricing (RUB на момент checkout'а; CNY у источника пересчитывается)
    total_rub         NUMERIC(12,2) NOT NULL,
    cny_rate_at_checkout NUMERIC(12,4) NOT NULL,

    -- Manager-driven fields
    incoming_declaration  VARCHAR(16),         -- китайский трек, заполняет менеджер на PAID → PROCURED
    procured_by_admin_id  BIGINT,              -- какой менеджер выкупил
    procured_at           TIMESTAMP,

    -- Pickup-point preference (заполняется customer'ом на checkout, может меняться до создания last-mile)
    preferred_pickup_carrier  VARCHAR(16),     -- 'cdek' | 'yandex' | 'boxberry' | 'pochta'
    preferred_pickup_point_id VARCHAR(64),

    -- Hold-state metadata
    hold_reason        VARCHAR(64),
    hold_started_at    TIMESTAMP,

    -- FSM enforcement
    CONSTRAINT valid_state CHECK (state IN (
        'pending', 'paid', 'procured', 'on_hold',
        'arrived_in_ru', 'in_last_mile', 'awaiting_pickup',
        'delivered', 'returning_to_ru_warehouse', 'not_delivered',
        'return_in_progress', 'returned', 'closed', 'cancelled'
    ))
);

-- История переходов
CREATE TABLE order_state_history (
    id          BIGSERIAL PRIMARY KEY,
    order_id    BIGINT REFERENCES orders(id),
    from_state  VARCHAR(32) NOT NULL,
    to_state    VARCHAR(32) NOT NULL,
    event_type  VARCHAR(64) NOT NULL,
    event_id    UUID UNIQUE NOT NULL,        -- идемпотентность
    actor_type  VARCHAR(16) NOT NULL,        -- 'customer' | 'manager' | 'system' | 'webhook'
    actor_id    VARCHAR(64),
    metadata    JSONB,
    occurred_at TIMESTAMP NOT NULL
);

-- Цепочка shipments (Loyality-specific)
CREATE TABLE shipment_legs (
    order_id            BIGINT REFERENCES orders(id),
    leg                 VARCHAR(16) NOT NULL,   -- 'cross_border' | 'last_mile'
    shipment_id         BIGINT REFERENCES shipments(id),
    parent_shipment_id  BIGINT REFERENCES shipments(id),  -- last_mile.parent = cross_border.id
    PRIMARY KEY (order_id, leg)
);
```

### 15.7 Idempotency специфичных переходов

| Переход | Idempotency-key | Защита |
|---------|----------------|--------|
| `PAID → PROCURED` | `(order_id, incomingDeclaration)` | UNIQUE constraint в `orders.incoming_declaration`; повторный POST с тем же треком — no-op |
| Создание DobroPost shipment | `incomingDeclaration` (natural key для DobroPost) | DobroPost API сам отдаёт `409 Conflict` при дубле |
| Создание last-mile shipment | `order_id` (один last-mile per order) | UNIQUE constraint в `shipment_legs(order_id, leg='last_mile')` |
| Webhook DobroPost (status update) | `(shipmentId, statusDate, status)` composite | inbox table (см. §6.4) |
| Webhook Russian carrier | per-carrier composite key (см. §11.2 в Logistics) | inbox table |

### 15.8 Таблица соответствия Order FSM ↔ DobroPost статусы ↔ Russian carrier статусы

| Order state | DobroPost (status_id) | Russian carrier (canonical) | Что видит customer |
|-------------|----------------------|------------------------------|---------------------|
| `PENDING` | – | – | "Заказ создан, ожидает оплаты" |
| `PAID` | – | – | "Оплачено, ожидает обработки" (1–2 дня) |
| `PROCURED` | 1, 2, 3, 4, 5 | – | "Товар выкуплен, готовится к отправке из Китая" |
| `PROCURED` | 6, 7 | – | "Покинул Китай, на таможне" |
| `PROCURED` | 8, 500, 510, 520-532, 540, 570, 591 | – | "На таможне в России" |
| `ON_HOLD` | 541–546, 590xxx | – | "Товар на проверке, мы с вами свяжемся" |
| `ARRIVED_IN_RU` | 648, 649, 9 | PRE_TRANSIT | "Прибыл в Россию, передан в доставку" |
| `IN_LAST_MILE` | – | IN_TRANSIT, OUT_FOR_DELIVERY | "В пути к пункту выдачи" |
| `AWAITING_PICKUP` | – | AT_PICKUP_POINT | "Готов к выдаче" |
| `DELIVERED` | – | DELIVERED | "Получен" |
| `NOT_DELIVERED` | – | RETURN_TO_SENDER, REFUSED | "Возврат, обратитесь в поддержку" |
| `CANCELLED` | (любой) | (любой) | "Отменён, средства возвращены" |

### 15.9 Loyality-anti-patterns специфичных для FSM

| Anti-pattern | Почему плохо | Правильно |
|---|---|---|
| Объединять `PAID` и `PROCURED` в один статус | Теряется граница «менеджер ещё не работал vs уже выкупил» — не построить SLA по time-to-procure | Отдельный `PROCURED` с `procured_at` и `procured_by_admin_id` |
| Создавать DobroPost shipment на checkout | Товара ещё нет, китайского трека нет — DobroPost откажет | Создание на event `ManagerProcured` (PAID → PROCURED) |
| Создавать last-mile shipment на checkout | Carrier требует адрес отправителя — а товар ещё не в РФ | Создание на event `CrossBorderArrived` (PROCURED → ARRIVED_IN_RU) |
| Идти из `PAID` сразу в `IN_TRANSIT` без `PROCURED` | Скрывает manual-step менеджера; невозможно ответить «выкупили или нет» | Явное состояние `PROCURED` |
| Не иметь `ON_HOLD` | Все edge-cases (паспорт fail, таможня rejected, stuck in CN) идут сразу в CANCELLED — теряются попытки fix | `ON_HOLD` как semantic lock с TTL 30 дней до auto-cancel |
| Customer-фасинг статус = DobroPost status_id | "Status 542" customer'у — непонятно | Mapping (см. §15.8) → 5 укрупнённых статусов |
| Создание Order сразу как `PAID` | Если payment 3DS challenge — Order может упасть в висячее состояние | `PENDING` как явное preliminary, `PAID` только после `PaymentCaptured` |
| Менеджер закрывает Order после ввода трека | Order ≠ DobroPost shipment, дальше есть last-mile | Order закрывается **только** на `CustomerPickedUp` |

### 15.10 Чек-лист — Loyality FSM

- [ ] States: PENDING, PAID, PROCURED, ON_HOLD, ARRIVED_IN_RU, IN_LAST_MILE, AWAITING_PICKUP, DELIVERED, RETURNING_TO_RU_WAREHOUSE, NOT_DELIVERED, RETURN_IN_PROGRESS, RETURNED, CLOSED, CANCELLED
- [ ] Поле `orders.incoming_declaration` обязательно для PROCURED+
- [ ] `procured_by_admin_id`, `procured_at` для аудита manager-actions
- [ ] `preferred_pickup_carrier` + `preferred_pickup_point_id` собираются на checkout, изменяемы только до `IN_LAST_MILE`
- [ ] Event `ManagerProcured` запускает создание DobroPost shipment асинхронно
- [ ] Event `CrossBorderArrived` (по DobroPost webhook status_id ∈ {648, 649}) запускает создание last-mile shipment
- [ ] `ON_HOLD` имеет TTL 30 дней → auto-CANCELLED + REFUND если не разблокирован
- [ ] Webhook DobroPost passport-validation: на `false` → Order → `ON_HOLD`
- [ ] Cron `stuck_in_cn_detector`: PROCURED + last DobroPost event > 14 дней → ON_HOLD
- [ ] Customer-facing статусы — это 5 укрупнённых маппингов (см. §15.8), не raw `status_id`
- [ ] DELIVERED → CLOSED через 14 дней (return window по закону РФ)

---

## 16. Связь с другими темами research

- **Тема 1 (E-commerce гиганты)** — каждая платформа имеет свою FSM, мы их там разобрали.
- **Тема 2 (OMS)** — Salesforce OMS, IBM Sterling — реализуют конфигурируемые pipelines, фактически параметризуемые FSM.
- **Тема 3 (DDD)** — FSM реализуется внутри Order aggregate как value object/method. Order is its own state machine.
- **Тема 5 (Saga)** — FSM = sequence of forward steps with compensations. Saga orchestrator = FSM workflow.
- **Тема 7 (Logistics)** — Shipment FSM — отдельный, со своими transitions (label generated → in transit → out for delivery → delivered → exception).
- **Тема 9 (Returns)** — RMA — отдельный FSM (requested → authorized → in transit → received → inspected → refunded/rejected).

---

## 17. Источники

### State machines — основы

- Finite-state machine — Wikipedia
- UML state machine — Wikipedia
- State Machine Design Pattern — LinkedIn
- State Machines basics — Mark Shead
- Finite State Machine — Our Pattern Language Berkeley
- State Machine Diagram Tutorial — Sparx
- Crash Course in UML State Machines — Quantum Leaps

### Refactoring boolean flags → FSM

- Replace State-Altering Conditionals with State — Joshua Kerievsky / InformIT
- State Pattern — Refactoring Guru
- State Pattern — Source Making
- State Design Pattern in Java — Baeldung
- The Flag Parameter Anti-Pattern — DEV
- No love for boolean parameters — DEV
- Refactoring to remove boolean flag — XState Discussion

### Order state machines — e-commerce

- State machines — commercetools learning
- Best practices for state machines — commercetools
- States API — commercetools
- Model and manage business processes with States — commercetools
- The order cycle state machine — state-machine.io

### Hierarchical & orthogonal

- Hierarchical State Machines (UML Statecharts) — Quantum Leaps
- Orthogonal Regions — miros
- Orthogonal Regions — StaMa
- Statechart elements — itemis

### Guards

- Guard — Statecharts glossary
- Guards — Stately/XState
- Validators and guards — python-statemachine
- Conditional transitions — SMC manual

### Saga & compensating transitions

- Saga — Thom's Blog (Failure Patterns)
- Finite State Machines, HSM, and SAGA — Brian Braatz
- Saga orchestrator as a state machine — GitHub rohsin47
- Saga Pattern with Spring State Machine — LinkedIn
- Saga state machine flight booking — DZone

### Idempotency

- Idempotency in Event-Driven Systems — DZone
- Idempotent Command Handling — Event-Driven.io
- Idempotency in Distributed Systems — Algomaster
- Idempotency Design Patterns Beyond 'Retry Safely'
- Microservices Idempotent Consumer Pattern — Java Design Patterns
- How to Handle Idempotency in Microservices — OneUptime
- Idempotent Cloud Functions for duplicate events

### FSM libraries

- Spring State Machine — Baeldung
- Akka FSM — Akka docs
- Akka Persistent FSM
- Akka Typed FSM (recommended replacement)
- XState — Stately docs
- python-statemachine docs

### Event sourcing & FSM

- Event Sourcing Pattern — Azure
- Building an Event-Sourced Aggregate — Marten
- How to get current entity state from events — Event-Driven.io
- Relationship between state machines and event sourcing — eulerfx gist
- Event Sourcing Pattern — AWS Prescriptive Guidance
- Event Sourcing — microservices.io

### Database constraints for FSM

- PostgreSQL CHECK Constraints docs
- PostgreSQL CHECK Constraints tutorial
- Conditional check constraints — tutorialpedia

### Visual references

- Online Shopping State Diagram — Creately
- Online shopping state diagram — Gleek
- State Diagrams use case — Eraser
- Ecommerce Retail Order State Diagram — Venngage

---

## Related

- [[Research - Order Architecture]] — индекс серии Order
- [[Research - Order (1) Domain-Driven Design]] — Order как aggregate root, инварианты
- [[Research - Order (3) E-commerce Giants]] — реальные FSM Amazon/Shopify/Wildberries
- [[Research - Order (5) Payment Integration]] — отдельная Payment FSM (financial)
- [[Research - Order (6) Logistics Integration]] — отдельная Shipment FSM (fulfillment)
- [[Research - Order (7) Saga Pattern]] — compensating transitions через saga
- [[Backend]] — backend dashboard
- [[Loyality Project]]
