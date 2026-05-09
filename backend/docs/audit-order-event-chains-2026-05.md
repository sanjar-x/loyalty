# Order Event-Chain Audit — Sprint 1 (2026-05-09)

**Scope**: Sprint 1 / B1 audit перед подключением Frontend Admin Orders UI и
последующим Sprint 2 (Logistics Shipments UI). Цель — понять, какие из
шести критичных Order-FSM-переходов реально несут downstream side-effects,
где cross-border / last-mile booking фактически выполняется, и где
есть разрывы, способные привести к "204 OK на API, но процесс не стартовал".

**Method**: traversal от каждого `order.<transition>()` метода в
`src/modules/order/domain/entities.py` через эмитируемый событием
ID, проверка каждого `register_event_handler(...)` в
`src/infrastructure/outbox/tasks.py` и `src/modules/*/infrastructure/tasks.py`,
и cross-check с командами `src/modules/order/application/commands/*` на
предмет sync side-effects.

---

## Резюме

| Event                            | Outbox consumer? | Sync side-effect в command            | Статус            |
| -------------------------------- | ---------------- | ------------------------------------- | ----------------- |
| `OrderCreatedEvent`              | ❌ нет           | PaymentIntent.authorize() в handler   | OK (audit only)   |
| `OrderPaidEvent`                 | ❌ нет           | —                                     | OK (audit only)   |
| `OrderProcuredEvent`             | ❌ нет           | DobroPost.book_cross_border() в handler| **GAP B**        |
| `OrderArrivedInRuEvent`          | ❌ нет           | russian_carrier.book_last_mile() в handler | **GAP C**    |
| `OrderEnteredLastMileEvent`      | ❌ нет           | —                                     | **GAP A — блокер**|
| `OrderDeliveredEvent`            | ❌ нет           | —                                     | OK (audit only)   |

**Вердикт**: цепочка собирается синхронно прямо в command-handler'ах, но
пайплайн **разрывается на стадии IN_LAST_MILE → AWAITING_PICKUP →
DELIVERED**: нет производителя `RussianCarrierTrackingEvent`, на который
подписан `RussianCarrierTrackingConsumer`. После последовательности
`procure → arrived_in_ru` Order застревает в `ARRIVED_IN_RU` навсегда
(если только webhook DobroPost не сообщит о следующем терминальном
статусе или менеджер не дёрнет admin endpoint — которого тоже нет).

Для запуска MVP нужны два решения:

1. **GAP A** — обязательно к Sprint 2. Без этого frontend admin сможет
   создать заказ → принять оплату → сделать procure → дождаться
   `ARRIVED_IN_RU` через DobroPost webhook, но дальше last-mile карта
   будет показывать stale статус, потому что Order FSM никогда не
   двинется в IN_LAST_MILE.
2. **GAP B** — рекомендуется до MVP. Сейчас sync DobroPost booking в
   `ProcureOrderHandler` без retry, риск split-state (capture made,
   shipment not booked, DobroPost down).

GAP C/D — info-only, можно отложить на post-MVP.

---

## Карта event → consumer → command-handler → side effects

### 1. `OrderCreatedEvent`

**Эмитируется**: `Order.create()` → `customer POST /api/v1/orders` →
`CreateOrderFromCartHandler.handle()` (`commands/create_order_from_cart.py:265`).

**Outbox consumers**: нет. Falls в "unknown event_type" branch
`src/infrastructure/outbox/relay.py:_EVENT_HANDLERS.get(event_type) is None`
→ помечается processed, payload остаётся в БД на 7 дней до prune.

**Sync side-effects в `CreateOrderFromCartHandler`** (всё в одном UoW):
- `idempotency_store.reserve(scope="order.create", key=...)` — TTL 24 часа
- `cart_snapshot_reader.get(cart_id, snapshot_id)` — читает frozen snapshot
- `recipient_lookup.get(snapshot.recipient_id)` — ownership check
- `Order.create(...)` (PENDING) → `OrderCreatedEvent` в outbox
- `payment_gateway.authorize()` → создаёт PaymentIntent в state
  `INITIATED → AUTHORIZED` → `PaymentAuthorizedEvent` в outbox (тоже без
  consumer'а)
- `order.attach_payment_intent(intent_id)` — заполняет
  `payment_intent_id`, FSM остаётся в PENDING
- `idempotency_store.attach_result(order_id)`
- `uow.commit()` — атомарно: order row + outbox rows + idempotency row +
  PaymentIntent row.

**Cart side**: `cart.mark_ordered()` вызывается **отдельно**, в
`cart.application.commands.confirm_checkout.ConfirmCheckoutHandler` (НЕ
здесь). Frontend ожидает следующий call — `POST /cart/checkouts/{id}/confirm`.
Если frontend пропустит этот шаг, cart останется в `FROZEN` до timeout
(`CHECKOUT_TTL_MINUTES=15`) и затем перейдёт в `ACTIVE` lazy при
следующем GET. **Не разрыв, но повод задокументировать**: процесс
оформления — три POST-а, не один.

**Статус**: OK (audit only).

---

### 2. `OrderPaidEvent`

**Эмитируется**: `order.mark_paid(payment_intent_id)` из
`MarkOrderPaidHandler` (`commands/mark_order_paid.py:50`).

**Триггер handler'а**: `PaymentCapturedEvent` (выпускается
`PaymentIntent.capture()` в `payment.commands.capture_payment_intent`).
В `register_event_handler`:

```
src/modules/order/infrastructure/tasks.py:297
register_event_handler("PaymentCapturedEvent", _on_payment_captured)
```

→ kicks `order_on_payment_captured_task` (TaskIQ, max_retries=3,
retry_on_error=True, timeout=30) → `run_inbox_idempotent` обёртка →
`PaymentCapturedConsumer.handle(payload)` → `MarkOrderPaidCommand`
→ `MarkOrderPaidHandler.handle()`.

**Side-effects**: только FSM (PENDING → PAID) + history write +
`OrderPaidEvent` в outbox.

**Outbox consumers для `OrderPaidEvent`**: нет.

**Статус**: OK. Цепь PaymentCaptured → MarkOrderPaid работает корректно.
Любой downstream (fulfillment notification, accounting) пока не
требуется.

---

### 3. `OrderProcuredEvent` ⚠ GAP B

**Эмитируется**: `order.procure(declaration, admin_id)` из
`ProcureOrderHandler` (`commands/procure_order.py:107`).

**Триггер**: `POST /api/v1/admin/orders/{order_id}/procure` (admin endpoint,
`router_admin.py:198`). RequirePermission(`orders:procure`).

**Outbox consumers для `OrderProcuredEvent`**: нет.

**Sync side-effects в `ProcureOrderHandler`** (всё в одном UoW, шаги
1→2→3 строго в этом порядке):

1. `order_repo.get_for_update(order_id)` — `SELECT FOR UPDATE`
2. Validate: status==PAID, declaration parses, no other order owns this
   `incoming_declaration` (UNIQUE)
3. `payment_gateway.capture(intent_id, idempotency_key=f"order:{order_id}:capture")`
   — провайдер списывает hold → `PaymentCapturedEvent` будет эмитнут
   позже в payment-side commit; сейчас просто side-effect провайдера
4. `dobropost_gateway.book_cross_border(order_id, identity_id, declaration, idempotency_key=f"order:{order_id}:dobropost")`
   — POST /api/shipment в DobroPost (или stub UUID), возвращает
   `cross_border_shipment_id: UUID`
5. `order.procure(declaration, admin_id)` — FSM PAID→PROCURED →
   `OrderProcuredEvent`
6. `order.attach_cross_border_shipment(shipment_id)` — заполняет
   `cross_border_shipment_id` на order и всех `OrderItem`
7. `record_history(actor=manager:admin_id, pre=PAID)`
8. `uow.commit()`

### 🛑 GAP B — risks & failure mode

- **Sync booking с retry только на admin retry.** Если DobroPost API
  возвращает 5xx или таймаут, exception → `__aexit__` UoW →
  `session.rollback()` → DB-state не меняется. Но **`gateway.capture()`
  уже отработал** на стороне платёжного провайдера; idempotency_key
  гарантирует, что повторный вызов capture вернёт OK без двойного
  списания, но сам факт списания **уже произошёл**. Если DobroPost
  окончательно недоступен (часами), order застрянет в PAID, capture
  выполнен, `cross_border_shipment_id=None`. Refund нужно будет
  делать вручную через `force-cancel` → CancelOrderHandler.refund.
- **Split-state risk во время transaction**: если процесс упадёт между
  шагом 4 (DobroPost вернул shipment_id) и шагом 8 (commit), мы получим
  shipment в DobroPost, но не в нашей DB. Idempotency_key спасёт при
  retry — DobroPost вернёт тот же UUID. Но если retry никогда не
  произойдёт (admin закрыл tab), shipment в DobroPost будет orphan'ом.

### Рекомендации (опционально, не для Sprint 1)

- **R-B1 (минимум)**: добавить наблюдение — Prometheus counter
  `procure_failures_total{stage}` с этикетками `capture` / `dobropost` /
  `commit`. Видимость гарантирует, что split-state не пропадёт.
- **R-B2 (правильно)**: разнести три шага через outbox:
  1. `procure` — только FSM transition + `OrderProcuredEvent` (без
     side-effects).
  2. Outbox consumer `order.OrderProcured` → `CapturePaymentTask`
     (idempotent, retry).
  3. После capture → `PaymentCapturedEvent` → ... ну, тут получается
     loop, потому что `PaymentCapturedEvent` уже триггерит
     `MarkOrderPaid`. Нужен отдельный `BookCrossBorderTask`,
     триггерящийся от `OrderProcuredEvent`.
  4. После DobroPost → `attach_cross_border_shipment` через отдельный
     command, идемпотентный по `incoming_declaration`.

  Цена: ещё ~150 строк кода + 2 новых TaskIQ task + миграция payment
  flow на event-driven.

  Я бы рекомендовал R-B1 для MVP и отложить R-B2 на post-MVP, если
  не появится конкретный incident с DobroPost timeout.

**Статус**: OK с известным risk. Frontend может полагаться на текущий
sync-flow (либо успех с 204, либо exception → 5xx → менеджер видит
error и retry'ит).

---

### 4. `OrderArrivedInRuEvent` ⚠ GAP C

**Эмитируется**: `order.mark_arrived_in_ru()` из
`MarkOrderArrivedInRuHandler` (`commands/mark_order_arrived_in_ru.py:60`).

**Триггер handler'а**: `DobroPostStatusUpdatedEvent` со статусом
`status_id ∈ {648, 649}` (DobroPost map → `DobroPostFsmAction.ARRIVED_IN_RU`).
Webhook → `IngestDobroPostWebhookHandler` → `enqueue_external_event` →
outbox row → relay → `_on_dobropost_status` →
`order_on_dobropost_status_task` → `DobroPostStatusUpdatedConsumer.handle()`
→ `arrived_handler.handle(MarkOrderArrivedInRuCommand)`.

**Outbox consumers для `OrderArrivedInRuEvent`**: нет.

**Sync side-effects в `MarkOrderArrivedInRuHandler`**:

1. `order_repo.get_for_update(order_id)`
2. Validate: status==PROCURED, cross_border_shipment_id is not None
3. **`order.mark_arrived_in_ru()`** — FSM PROCURED→ARRIVED_IN_RU + event
4. `russian_carrier.book_last_mile(order_id, cross_border_shipment_id, pickup_point, idempotency_key)`
   — sync вызов CDEK/Yandex (сейчас stub)
5. `order.attach_last_mile_shipment(last_mile_shipment_id)`
6. `record_history`, `uow.register_aggregate(order)`, `uow.commit()`

### 🟡 GAP C — Order статус: micro

Шаг 3 (FSM transition) идёт **до** шага 4 (booking). Если booking
падает, exception → UoW rollback откатит всё включая FSM (in-memory
изменения не персистятся). Так что атомарность не нарушена.

**Однако**: TaskIQ `max_retries=3` + `retry_on_error=True` — после трёх
неудачных booking'ов task попадает в `failed_tasks` table (DLQ через
`DLQMiddleware`). Заказ остаётся в PROCURED. Никакой автоматической
эскалации нет. Менеджер должен заметить через admin UI и вмешаться.

**Рекомендация**: post-MVP можно вынести `book_last_mile` в отдельный
TaskIQ task, триггерящийся от `OrderArrivedInRuEvent` через outbox —
тогда retry логика будет более прозрачна и можно ввести exponential
backoff независимо от ретраев `DobroPostStatusUpdatedEvent` consumer'а.

**Статус**: OK с приемлемым risk. Frontend может полагаться на то, что
после ARRIVED_IN_RU `last_mile_shipment_id` будет заполнен (либо при
первой попытке, либо после max 3 retry; иначе — manual intervention
admin'а).

---

### 5. `OrderEnteredLastMileEvent` 🛑 GAP A — БЛОКЕР

**Эмитируется**: `order.mark_in_last_mile()` из
`MarkOrderInLastMileHandler` (`commands/mark_order_in_last_mile.py:48`).

**Outbox consumers для `OrderEnteredLastMileEvent`**: нет (audit only —
ОК).

**Триггер handler'а**: `RussianCarrierTrackingEvent` (см.
`src/modules/order/infrastructure/tasks.py:301`):

```python
register_event_handler("RussianCarrierTrackingEvent", _on_russian_carrier)
```

→ `order_on_russian_carrier_task` → `RussianCarrierTrackingConsumer.handle()`:
- `canonical_status` ∈ `{"IN_TRANSIT", "OUT_FOR_DELIVERY"}` →
  `MarkOrderInLastMileCommand`
- `canonical_status == "AT_PICKUP_POINT"` → `MarkOrderAwaitingPickupCommand`
- `canonical_status == "DELIVERED"` → `MarkOrderDeliveredCommand`
- `canonical_status` ∈ `{"RETURN_TO_SENDER", "REFUSED", "FAILURE"}` →
  `MarkOrderReturningToWarehouseCommand`

### 🛑 КРИТИЧНЫЙ РАЗРЫВ

**Нет ни одного места в коде, которое эмитит `RussianCarrierTrackingEvent`**.
Проверено:

```
grep -rn "RussianCarrierTrackingEvent" src/
src/modules/order/infrastructure/tasks.py:7    (docstring)
src/modules/order/infrastructure/tasks.py:301  (register_event_handler)
```

Никаких `enqueue_external_event(event_type="RussianCarrierTrackingEvent", …)`,
никаких domain event'ов с `event_type = "RussianCarrierTrackingEvent"`.

**Что происходит сейчас**:

CDEK/Yandex webhook прилетает на
`POST /api/v1/webhooks/logistics/{provider_code}` →
`logistics.router_webhooks.receive_webhook` → `IngestTrackingHandler`
обновляет `Shipment.tracking_events`, эмитит
`ShipmentTrackingUpdatedEvent` → outbox → `_logistics_event_logger`
(structured-log only). Никто не транслирует это в действия Order.

**Последствие**: после `MarkOrderArrivedInRuHandler` (sync booking
last-mile) Order попадает в `ARRIVED_IN_RU` с заполненным
`last_mile_shipment_id`, но дальше **никогда не двинется**:

- IN_LAST_MILE — не наступит
- AWAITING_PICKUP — не наступит
- DELIVERED — не наступит
- (последствие: `order_close_window_cron` (daily 04:00 UTC) никогда не
  переведёт заказ в CLOSED — он смотрит только DELIVERED → CLOSED)

Frontend Admin UI будет показывать stale `ARRIVED_IN_RU` для всех
заказов в last-mile стадии. Customer App «In transit» / «Ready for
pickup» / «Delivered» статусы не будут срабатывать.

### Решение GAP A — три варианта

**Вариант 1 (минимальный, рекомендую для MVP)** — bridge logistics →
order через outbox. В `src/modules/logistics/infrastructure/tasks.py`
заменить `_logistics_event_logger("shipment.tracking_updated")` на
консьюмер, который:

1. Читает `ShipmentTrackingUpdatedEvent.payload`.
2. Проверяет провайдера: `provider_code in {"cdek", "yandex", ...}`
   (то есть russian carriers, не DobroPost).
3. Конвертирует `provider_status_code` → canonical_status (через
   маппинг внутри логистики).
4. `IUnitOfWork.enqueue_external_event(event_type="RussianCarrierTrackingEvent", payload={"shipment_id": ..., "canonical_status": ..., "last_mile_shipment_id": ...}, event_id=uuid5(...))`.

Это самый дешёвый путь — переиспользует существующий
`RussianCarrierTrackingConsumer`. ~80 строк кода + регистрация +
unit/integration тесты.

**Вариант 2 (правильнее)** — добавить cross-module ACL adapter в
order: `order.infrastructure.adapters.shipment_tracking_listener`,
подписанный на `ShipmentTrackingUpdatedEvent` напрямую, без
промежуточного transformation event'а. Требует добавить
`("order", "logistics")` whitelist в `ALLOWED_CROSS_MODULE` (в нем
сейчас `set()` — placeholder, всё ещё разрешён 0 импортов).

**Вариант 3 (если не успеваем)** — добавить admin endpoint
`POST /admin/orders/{id}/transition` (с body `target_status`), чтобы
менеджер мог вручную двигать FSM из админки. Это deletes автоматизацию,
но позволит запустить MVP до интеграции CDEK/Yandex polling. Для MVP
с малым потоком заказов — приемлемо как fallback.

**Я рекомендую Вариант 1** для Sprint 2. Если не успеваем — добавить
Вариант 3 как safety net.

---

### 6. `OrderDeliveredEvent`

**Эмитируется**: `order.mark_delivered()` из `MarkOrderDeliveredHandler`
(`commands/mark_order_delivered.py`).

**Триггер handler'а**: `RussianCarrierTrackingConsumer` с
`canonical_status="DELIVERED"`. **Зависит от GAP A** — пока нет
производителя `RussianCarrierTrackingEvent`, этот handler никогда не
вызывается.

**Outbox consumers для `OrderDeliveredEvent`**: нет.

**Side-effects**: только FSM + history.

### Что должно слушать `OrderDeliveredEvent` post-MVP

- **Referral activation** (ADR-006 §6): `OrderDeliveredEvent` —
  trigger для `lifetime_share` и активации `Referral` (CREATED →
  ACTIVATED → REWARDED). Phase 2 referral'а будет требовать этот
  consumer. Когда дойдёт — добавить в `referral.infrastructure.tasks.py`.
- **Customer notification** (push/email "Заказ доставлен, оставьте
  отзыв") — типичный customer-engagement consumer. Не для MVP.

**Статус**: OK для MVP (audit only).

---

## Список найденных gaps

| # | Severity | Тема | Действие | Когда |
|---|----------|------|----------|-------|
| **A** | 🛑 BLOCKER | `RussianCarrierTrackingEvent` никем не эмитится — Order застревает в ARRIVED_IN_RU | Реализовать Вариант 1: bridge `ShipmentTrackingUpdatedEvent` → `RussianCarrierTrackingEvent` в logistics tasks | **Sprint 2** перед публикацией Logistics UI |
| **B** | 🟡 RISK | Sync DobroPost booking в ProcureOrderHandler без retry; capture может пройти без booking при DobroPost down | Добавить Prometheus counter + reconciliation report. Полная переработка через outbox — post-MVP | Pre-MVP (наблюдение); post-MVP (rework) |
| **C** | 🟢 INFO | book_last_mile в MarkOrderArrivedInRuHandler — sync, retry max 3, потом DLQ | Acceptable. Возможно вынести в отдельный outbox task post-MVP | Post-MVP |
| **D** | 🟢 INFO | Все Order*Event audit-only; нет customer notifications, нет referral activation | Customer notifications — post-MVP. Referral activation — Sprint Referral Phase 2 | Post-MVP |

---

## Дополнительные находки (не входили в B1)

- **`OrderRefundedEvent`** эмитируется `order.cancel()` если `was_paid`,
  но никто не подписан. Refund фактически выполняется **до** FSM
  transition в `CancelOrderHandler` (sync `gateway.refund()` перед
  `order.cancel()`), так что событие — audit only. ОК.
- **Cart.mark_ordered** вызывается в `cart.confirm_checkout`, не
  автоматически после Order.create. Это сознательно: customer flow —
  три шага POST /orders → POST /cart/checkouts/{id}/confirm. Если
  frontend забудет confirm — cart сам откатится в ACTIVE через
  `CHECKOUT_TTL_MINUTES=15` lazy timeout (`is_freeze_expired`).
  Стоит задокументировать.
- **`payment_auth_expiry_cron`** отсутствует — задача B3 в этом спринте
  как раз закрывает этот gap для PaymentIntent в `AUTHORIZED` после
  истечения 7-дневного hold'а.

---

## Связанные документы

- `[[ADR-001 Clean Architecture Modular Monolith]]`
- `[[ADR-005a Pricing → Catalog ACL Inversion]]` — паттерн port в чужом
  domain'е, реализация в своём infrastructure (для R-B2 / Variant 1
  GAP A — тот же паттерн)
- `[[ADR-006 Referral Module Architecture]]` §6 — `OrderDeliveredEvent`
  как trigger для tier evaluation
- `backend/CLAUDE.md` — Outbox event handlers & consumer registry
- `docs/Order/Research - Order (2) State Machine FSM.md` §15 — FSM
  reference, использовалось при cross-checking transition rules
