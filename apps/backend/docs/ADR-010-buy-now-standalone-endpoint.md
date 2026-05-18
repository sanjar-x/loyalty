---
tags: [project/loyality, backend, adr, order, cart, buy-now]
type: adr
date: 2026-05-18
status: accepted
project: "[[Loyality Project]]"
component: backend
supersedes: "[[backend-tz-partial-checkout]] (2026-04-29 proposal)"
---

# ADR-010 — Buy Now: Standalone Endpoint, Not Partial Cart Checkout

## Status

**Accepted** — 2026-05-18.

Реализация уже в коде с commit `1c2a8a5d feat(order): Buy Now flow —
one-shot SKU checkout without cart` (2026-05-17). ADR
backfilled — фиксируем сделанный выбор и его инварианты, чтобы будущие
читатели не пытались вернуться к альтернативному дизайну, обсуждавшемуся
в `backend-tz-partial-checkout.md` (2026-04-29).

## Context

Бизнес-требование «Купить сейчас» на PDP mini-app: customer нажимает
одну кнопку на странице товара → попадает в мини-checkout (один SKU,
выбор recipient + pickup + delivery_quote) → создаётся Order →
оплата → done. **Корзина customer'а не должна быть затронута.**

В апреле 2026 был подготовлен TZ
([[backend-tz-partial-checkout]], 2026-04-29), предлагавший решить
задачу через расширение существующего `POST /cart/checkout`
параметром `selectedSkuIds: list[uuid]`:

```diff
 InitiateCheckoutRequest:
+    selectedSkuIds:
+      type: array
+      items: { type: string, format: uuid }
+      nullable: true
+      description: «оформить только эти SKU; остальные позиции остаются в active»
```

После анализа этот путь был отвергнут в пользу **отдельного
endpoint'а** `POST /api/v1/orders/buy-now`, который полностью минует
корзину.

## Decision

Buy Now реализован как **standalone endpoint**
`POST /api/v1/orders/buy-now`:

- собственный handler `CreateBuyNowOrderHandler`,
- собственная schema `BuyNowOrderRequest` (sku_id + quantity +
  recipient_id + pickup + delivery_quote_id + idempotency_key),
- собственный idempotency scope `"order.create_buy_now"` (TTL 24h),
- **не трогает** `carts` / `cart_items` / `checkout_snapshots` ни в
  каком виде,
- использует `Order.create(...)` (НЕ `Order.create_walk_in`) →
  `is_walk_in=False`, `refresh_recipient_snapshot` доступен,
- использует phantom `cart_id` (UUID4) для соответствия
  `Order.cart_id` schema-инварианту (колонка nullable=False, но это
  soft link без FK; `cart_id` discriminator уйдёт в
  `Order.creation_source` в Sprint 2 / задача BE-6).

TZ partial-checkout (`backend-tz-partial-checkout.md`) объявлен
**archived** — перенесён в `apps/backend/docs/archive/` с header
«Superseded by ADR-010».

## Consequences

### Positive

- **Нет блокировки корзины.** Customer может одновременно (a) набирать
  корзину для оптовой закупки, (b) сделать Buy Now на «срочную» вещь —
  обе операции независимы.
- **Идемпотентность тривиальная.** `idempotency_key` от клиента →
  scope `"order.create_buy_now"`. Не нужно бороться с race-conditions
  типа «cart frozen во время partial-checkout, в параллельной вкладке
  пользователь меняет cart-item, snapshot drift».
- **Переиспользование без копи-пасты.** `resolve_delivery_quote`
  (`application/_delivery.py`) и ACL-адаптеры (`ICatalogSkuPriceReader`,
  `IRecipientLookup`, `IPaymentGateway`) shared с cart-flow и walk-in.
- **Latency меньше.** Один HTTP round-trip против двух
  (cart-add → checkout). Особенно важно для PDP мини-app.
- **Тестируемость.** Handler покрывается unit-тестами с fake-портами
  (см. `tests/unit/modules/order/test_buy_now_handler.py`, 802 LOC) без
  необходимости поднимать cart-fixtures.

### Negative

- **Дублирование bootstrap-логики.** Authorize payment +
  `attach_payment_intent` + skip-payment short-circuit повторяются
  между `CreateOrderFromCartHandler` и `CreateBuyNowOrderHandler`. Это
  принято как acceptable — оба handler'а уже разделяют common helper'ы
  (`resolve_delivery_quote`, `record_history`); полная унификация
  через generic `OrderCreationStrategy` не оправдана при 2
  потребителях.
- **Analytics discriminator.** Сегодня нельзя отличить Buy Now от
  cart-flow без чтения `idempotency_keys.scope` или сохранения
  `creation_source` в Order. BE-6 (Sprint 2) добавит
  `Order.creation_source` enum, после чего analytics запросы станут
  тривиальными.
- **Фронт обязан реализовать mini-checkout sheet.** Нельзя срезать
  угол и переиспользовать `useCheckoutFlow` (cart-bound) — нужен
  отдельный `useBuyNowCheckout` или обобщение.

### Neutral

- Backend контракт `/cart/checkout` остаётся без изменений (TZ
  proposal никогда не вошёл в код).

## Rationale — почему отвергли TZ partial-checkout

| Критерий | Partial checkout (TZ) | Standalone endpoint (выбрано) |
| --- | --- | --- |
| Блокирует ли корзину? | Да — `frozen` хотя бы по `selectedSkuIds`. Если customer параллельно ещё что-то меняет в cart — race | Нет |
| Сложность idempotency | Высокая — нужно учитывать snapshot drift при mutation in flight | Низкая — обычный `idempotency_key` scope |
| Сложность backend | Расширение существующих FSM (Cart `frozen` partial-state) + новые схемы | Новый handler, переиспользует helper'ы |
| Сложность frontend | Cart UI должен помечать individual items как «in checkout», скрывать кнопки edit/delete | Independent sheet поверх PDP — UI слой полностью отдельный |
| Telemetry | Сложно отличить partial cart-checkout от full-checkout | Endpoint + scope = clean tag |
| UX «Купить сейчас» с PDP | Customer не видит свою корзину → почему она вдруг должна frozen-state? | Совпадает с mental model: «одна кнопка, один товар» |
| `/trash` partial checkout use-case (cart screen, выбор подмножества чекбоксами) | Поддерживается из коробки | **Не поддерживается** — нужен отдельный feature, см. §Related Decisions |

## Invariants (locked)

> Эти инварианты — часть контракта Buy Now. Нарушение требует нового
> ADR или PR с правкой этого ADR + обновлённым тест-покрытием в
> `tests/architecture/`.

### I1 — Buy Now не модифицирует корзину customer'а

Handler `CreateBuyNowOrderHandler` **не выполняет** ни одной из:

- чтения `carts` / `cart_items` строк customer'а (за исключением
  опционального audit-логирования, но это пока не реализовано и не
  будет добавлено без отдельного ADR);
- записи / мутации `carts` / `cart_items`;
- порождения событий `Cart*Event` (CartItemAddedEvent, CartFrozenEvent
  и т.п.);
- использования cart-flow `idempotency_key` scope.

Корзина customer'а на момент до и после Buy Now-запроса
**эквивалентна**. Идемпотентность Buy Now не связана с состоянием
cart.

**Тест:** `tests/unit/modules/order/test_buy_now_handler.py::*` (нет
обращений к cart-fakes); `tests/architecture/test_boundaries.py`
запрещает import'ы `cart.*` из `order.application.commands.create_buy_now_order`
(см. `ALLOWED_CROSS_MODULE` whitelist, который содержит только
`("order","cart"): {"src.modules.order.infrastructure.adapters.cart_snapshot_reader"}`
— этот адаптер реальный handler не использует).

### I2 — Recipient указывается inline; нет combined endpoint

`BuyNowOrderRequest.recipient_id` — **required**. Backend **никогда**
не предоставит combined endpoint типа `POST /orders/buy-now` с inline
`recipient` payload (как `AdminCreateWalkInOrderRequest`).

**Причина:**

- DDD-граница между `recipient` и `order` bounded contexts.
- Atomicity «recipient+order» обеспечивается клиентом:
  1. `POST /recipients` — создать recipient, получить `recipient_id`.
  2. `POST /orders/buy-now` с этим `recipient_id`.
- Если customer прервёт flow между шагами — он получит «orphan»
  recipient row в своём профиле, но это не data corruption (recipient
  принадлежит идентичности и видим в `/recipients` UI).

**Walk-in admin flow** (`POST /admin/orders`) — исключение из этого
правила, т.к. admin провизионирует Identity + Customer + Recipient
inline в одной транзакции для walk-in customer'а, которого не
существовало в системе. Это inverted use-case (admin-driven, не
customer-driven), и domain-инвариант `Order.is_walk_in=True`
дискриминирует его явно.

**Если в будущем встанет требование atomic «recipient+order» для
customer-flow** — это отдельный ADR; вероятная реализация — через
saga / payload contract (`POST /orders/buy-now-with-new-recipient`),
не через перегрузку текущего endpoint.

**Тест:** `BuyNowOrderRequest.recipient_id: uuid.UUID` (без
`Optional`); 422 на отсутствие — покрыто
`test_orders_api.py::test_buy_now_with_missing_sku_returns_4xx`
(recipient-422 surface'ится той же дорогой).

### I3 — `is_walk_in=False` for Buy Now orders

`CreateBuyNowOrderHandler` использует `Order.create(...)` (не
`Order.create_walk_in`). Это означает:

- `Order.is_walk_in == False`;
- `refresh_recipient_snapshot` команда работает (customer владеет
  Recipient row);
- `mark_paid_offline` НЕ применима (Buy Now всегда через
  PaymentIntent, даже под skip-payment short-circuit);
- `cart_id` — phantom UUID4 (soft link, нужен для NOT NULL ограничения
  колонки; не указывает на реальный cart).

### I4 — Использовать `resolve_delivery_quote` (общий helper)

`CreateBuyNowOrderHandler` обязан вызывать
`src.modules.order.application._delivery.resolve_delivery_quote`,
а не дублировать ownership/currency/expiry проверки. Это гарантирует,
что cart-flow и Buy Now ведут себя одинаково в edge-cases
(expired quote, wrong customer, currency mismatch).

## Related decisions

- **Cart `/trash` partial checkout** — отдельный сценарий
  (cart-screen, выбор подмножества чекбоксами). НЕ покрывается этим
  ADR. Если потребуется — реализуем через `selectedSkuIds` на
  `/cart/checkout` (тот самый TZ proposal, но в узком scope `/trash`).
- **`Order.creation_source` enum (BE-6, Sprint 2)** — добавит
  `BUY_NOW` discriminator для analytics. Не меняет ADR-инвариантов,
  только улучшает observability.
- **SPEC `order-procurement-production-grade-2026-05.md`** — общая
  procurement-цепочка (CDEK booking, supplier-type branching).
  Влияет на Buy Now только через downstream consumers, не через
  endpoint design.

## Related

- [[buy-now-audit-2026-05]] — audit, родительский для этого ADR
- [[order-procurement-production-grade-2026-05]] — общая
  procurement-дорожка
- [[backend-tz-partial-checkout]] — отвергнутый TZ (archived)
- [[ADR-001 Clean Architecture Modular Monolith]] — фон по DDD-границам
- [[ADR-008 Multi-Package Modular Monorepo]] — фон по структуре
  modules / shared kernel
- [[Loyality Project]]
