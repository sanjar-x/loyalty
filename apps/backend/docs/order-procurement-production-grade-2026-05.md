# SPEC — Order Procurement Production-Grade (2026-05-18)

> **Назначение.** Дорожная карта по доведению цепочки «PAID → PROCURED
> → ARRIVED_IN_RU → IN_LAST_MILE → AWAITING_PICKUP → DELIVERED» до
> production-уровня для **всех** путей создания Order (cart-flow,
> Buy Now, walk-in). Выделена отдельно от
> [[buy-now-audit-2026-05]] потому, что задачи не Buy Now-специфичны:
> закрытие этих gap'ов нужно для общего MVP-launch, не только для
> «нажимаемой» Buy Now кнопки.
>
> **Объём — ориентировочно 2-3 недели** (1-2 backend инженера) при
> готовности всех зависимостей (CDEK/Yandex SPEC, catalog stock,
> DobroPost rate-limit ответ).
>
> **Связанные документы:**
> - `apps/backend/docs/buy-now-audit-2026-05.md` — родительский аудит
> - `apps/backend/docs/audit-order-event-chains-2026-05.md` — историческая карта event-chains (Sprint 1, GAP A/B закрыты)
> - vault `Projects/loyality/backend/SPEC - Yandex Delivery Group 6 — Warehouse & Shipment Management (LOG-004).md`
> - vault `Projects/loyality/backend/Researches/Order/` — Research Order (1-9)

---

## 1. Текущий статус procurement-цепочки

| Шаг | Triggered by | Side effect | Реальный/stub? |
| --- | --- | --- | --- |
| PENDING → PAID | `PaymentCapturedEvent` → `PaymentCapturedConsumer` → `MarkOrderPaidHandler` | FSM transition + `OrderPaidEvent` в outbox | ✅ real |
| PAID → PROCURED | Manager `POST /admin/orders/{id}/procure {incomingDeclaration}` | (a) PSP capture (no-op если уже captured), (b) FSM transition + `OrderProcuredEvent` в outbox | ✅ real |
| PROCURED → cross-border booking | `OrderProcuredEvent` → `OrderProcuredConsumer.book_cross_border` | DobroPost shipment booked, `attach_cross_border_shipment` | ⚠ **DobroPost stub** (env-flag `DOBROPOST_USE_STUB=true` по умолчанию) |
| webhook 648/649 → ARRIVED_IN_RU | `DobroPostStatusUpdatedEvent` → `DobroPostStatusUpdatedConsumer` → `MarkOrderArrivedInRuHandler` | (a) FSM transition, (b) sync `russian_carrier.book_last_mile`, (c) `attach_last_mile_shipment` | ⚠ **CDEK / Yandex stub** (`RussianCarrierGatewayStub` — генерирует псевдо-shipment_id из SHA-256) |
| webhook → IN_LAST_MILE | `RussianCarrierTrackingEvent` (LOG-002 bridge) → `RussianCarrierTrackingConsumer` → `MarkOrderInLastMileHandler` | FSM transition | ⚠ Producer есть (logistics IngestTrackingHandler), но **нет real carrier** = некому emit'ить webhook |
| AWAITING_PICKUP / DELIVERED | Тот же consumer по карте статусов | FSM | ⚠ Зависит от real carrier feed |

**Ключевой gap:** между `mark_arrived_in_ru` и `mark_in_last_mile` сейчас
сидит **`RussianCarrierGatewayStub`**, который НИЧЕГО не отправляет
реальному перевозчику. После DobroPost-arrival посылка физически в РФ,
но без CDEK/Yandex booking она лежит на складе и не доставляется
customer'у. Это **deal-breaker для launch** — независимо от того,
каким путём заказ создан.

---

## 2. Gap-описание (расширенно из buy-now-audit)

### 2.1 BE-2 — Real CDEK / Yandex / Boxberry / Pochta last-mile booking

**Severity:** blocker для production launch (не только Buy Now).

**Где:** `apps/backend/src/modules/order/infrastructure/adapters/russian_carrier_gateway.py`.

**Что сейчас:**

```python
class RussianCarrierGatewayStub(IRussianCarrierGateway):
    async def book_last_mile(...) -> uuid.UUID:
        seed = f"lastmile:{order_id}:{cross_border_shipment_id}:..."
        shipment_id = uuid.UUID(bytes=hashlib.sha256(seed.encode()).digest()[:16])
        self._logger.info("russian_carrier.stub.book_last_mile", ...)
        return shipment_id
```

— ни одного HTTP-вызова к реальному carrier. `last_mile_shipment_id` записывается в Order, но в logistics-модуле никакой `Shipment` row не появляется.

**Что нужно:**

1. Реальный adapter `RussianCarrierGatewayReal`, который маршрутизирует по `pickup_point.carrier`:
   - `cdek` → `logistics.application.commands.CreateCdekShipmentHandler` (logistics-публичный command-handler).
   - `yandex` → `CreateYandexDeliveryShipmentHandler`.
   - `boxberry` / `pochta` → отложить (Phase 2, см. §4 ниже).
2. Идемпотентность: использовать `idempotency_key = f"order:{order_id}:last_mile"` так же, как DobroPost-adapter (`{order_id}:dobropost`).
3. Failure → graceful `OrderHold(reason=BOOKING_FAILED)` через тот же паттерн, что `OrderProcuredConsumer` (см. строки 109-131). Это значит: вынести `MarkOrderArrivedInRuHandler` step «book_last_mile sync» в отдельный consumer на `OrderArrivedInRuEvent`, аналогично ORD-006.
4. Settings flag `RUSSIAN_CARRIER_USE_STUB: bool` (mirror `DOBROPOST_USE_STUB`) для местного dev / CI.

**Зависимости:**

- LOG-004 SPEC для Yandex (`SPEC - Yandex Delivery Group 6`) — посмотреть, какие public command-handlers готовы.
- CDEK уже seeded (`seed/logistics/seed_cdek.py`), `provider_accounts` table; public command-handler в logistics требует ревизии.

**Тесты:**

- Unit: `tests/unit/modules/order/test_russian_carrier_gateway.py` — routing по carrier, idempotency, exception → propagate.
- Integration: `tests/integration/modules/order/test_arrived_in_ru_to_last_mile.py` — full chain, реальный logistics adapter (carrier API via httpx-mock).

### 2.2 BE-3 — Supplier-type branching (CROSS_BORDER / LOCAL / mixed)

**Severity:** blocker для LOCAL Buy Now / cart-flow; major для mixed-supplier cart.

**Где:**

- `apps/backend/src/modules/order/application/commands/procure_order.py:108` (всегда capture + emit OrderProcured)
- `apps/backend/src/modules/order/application/consumers/order_procured.py:103` (всегда DobroPost.book_cross_border)
- `apps/backend/src/modules/order/application/commands/mark_order_arrived_in_ru.py:62` (всегда book_last_mile)

**Что сейчас:** `OrderItem.supplier_type` записывается, но никем не читается. Все orders проходят как cross-border.

**Что нужно:**

#### 2.2.1 Domain-rule: order = single supplier-type

Запретить mixed-supplier order на уровне `Order.create()`:

```python
@classmethod
def create(cls, *, items: list[OrderItem], ...) -> Order:
    if not items:
        raise OrderEmptyError()
    types = {item.supplier_type for item in items}
    if len(types) > 1:
        raise MixedSupplierTypeError(types=sorted(t.value for t in types))
    ...
```

Buy Now это всегда 1 item → ограничение noop. Cart-flow должен сегментировать корзину на 2 order'a (cross-border + local) — это front-end решение, backend просто валидирует.

#### 2.2.2 FSM-ветка для LOCAL

Открытый вопрос **Q3**: пропускать ли cross-border ступени (PROCURED → ARRIVED_IN_RU) для LOCAL-supplier'а или гнать через те же ступени с no-op shipment'ами?

**Рекомендуемый вариант (с подтверждением продукта):**

- LOCAL Order skips DobroPost: `procure(local=True)` → новый event `OrderLocalProcuredEvent` → consumer сразу вызывает `book_last_mile`. FSM упрощённая: `PAID → PROCURED → IN_LAST_MILE → AWAITING_PICKUP → DELIVERED`.
- Migration: добавить enum-shortcut в `_ALLOWED_TRANSITIONS`: `PROCURED → IN_LAST_MILE` (минуя `ARRIVED_IN_RU`).
- Alternative: оставить ARRIVED_IN_RU как «cross-border-only» step, для LOCAL не использовать вовсе. Domain знает разницу через `items[0].supplier_type` (gated single-supplier-type инвариантом из 2.2.1).

#### 2.2.3 Consumer routing

`OrderProcuredConsumer` должен branch'ить:

```python
async def handle(self, payload: dict) -> None:
    ...
    order = await self._order_repo.get(order_id)
    if all(item.supplier_type is SupplierType.LOCAL for item in order.items):
        # LOCAL: skip DobroPost, book last-mile сразу
        ...
    else:
        # CROSS_BORDER: book DobroPost (как сейчас)
        ...
```

**Тесты:**

- Domain unit: `Order.create` отвергает mixed-supplier order.
- Consumer unit: LOCAL не вызывает DobroPost; CROSS_BORDER не вызывает CDEK напрямую.
- Integration: LOCAL Order проходит full FSM без DobroPost.

### 2.3 BE-7 — Inventory pre-check

**Severity:** minor (UX); зависит от готовности stock-tracking в catalog.

**Где:** `apps/backend/src/modules/order/application/commands/create_buy_now_order.py:149`, `admin_create_walk_in_order.py`, `create_order_from_cart.py`.

**Что нужно:**

1. Расширить `CatalogSkuSnapshot` полем `available_stock: int | None` (None = stock не отслеживается).
2. `CatalogSkuPriceReader.get_many` подтягивает `SUM(inventory)` или эквивалент из catalog-stock (если есть колонка `skus.stock_left`).
3. Buy Now / cart / walk-in handler проверяет `snapshot.available_stock is not None and snapshot.available_stock < quantity` → 422 `INSUFFICIENT_STOCK`.

**Зависимость:** **Q8** — нужен ответ catalog-команды, есть ли `stock_left` / `inventory` таблица. Если нет — этот gap балансируется на самой реализации stock tracking.

---

## 3. Открытые вопросы (перенесено из buy-now-audit раздела 4)

### Q3 — LOCAL skip cross-border?

**Контекст:** §2.2.2. Решение продукта необходимо до старта Sprint 1 этого SPEC. Без него непонятно, как проектировать FSM-ветку.

**Опции:**

- **A (рекомендуется):** LOCAL пропускает `ARRIVED_IN_RU`, FSM = `PAID → PROCURED → IN_LAST_MILE → AWAITING_PICKUP → DELIVERED`. Кратчайший путь, отражает физику (LOCAL товар уже в РФ).
- **B:** LOCAL проходит те же ступени с no-op shipment'ами (`cross_border_shipment_id = uuid.UUID(int=0)`). Сохраняет единый FSM, но запутывает аналитику.

### Q6 — DobroPost rate-limit?

**Контекст:** при ramp-up customer-flow процессит много `OrderProcuredEvent` → много DobroPost booking запросов. Circuit-breaker (`DOBROPOST_CIRCUIT_FAILURE_THRESHOLD=5`) защищает от каскадного сбоя, но при rate-limit'е customer'ы будут массово видеть ON_HOLD.

**Нужно:** уточнить у DobroPost спеца / в их docs:

- Per-account QPS limit.
- Bulk endpoint (POST many shipments) — есть ли?
- Strategy при 429: backoff (есть в `BaseClient`) или queueing на нашей стороне.

### Q7 — CDEK / Yandex / Boxberry / Pochta carrier readiness

**Контекст:** §2.1. Точка опоры — vault `SPEC - Yandex Delivery Group 6` (LOG-004) для Yandex; для CDEK SPEC не зафиксирован, требует ревизии.

**Нужно ответить:**

- Какой carrier идёт первым для production launch?
- Все ли public command-handlers (`CreateCdekShipmentHandler` и т.п.) реально готовы или только seeded provider_accounts?
- Готов ли webhook ingest для CDEK / Yandex tracking events (LOG-002 закрыл общую bridge, но per-carrier mapping в `russian_carrier_status_map.py` нужно ревьюнуть)?

### Q8 — Stock tracking в catalog

**Контекст:** §2.3. Нужен ответ catalog-команды:

- Есть ли уже колонка `skus.stock_left` / отдельная таблица `inventory`?
- Какой источник истины: ручной admin-input или sync с supplier-marketplace?
- Optimistic locking / reservation на момент создания order (zoom: что делать с unpaid pending orders, держат ли они stock)?

Без ответа BE-7 балансируется ⇒ не оценить.

---

## 4. Phasing

### Phase 1 (~1 неделя, после Q3/Q7 ответов)

- §2.2.1 single-supplier domain rule + migration (cart-flow front может уже сегментировать).
- §2.2.3 consumer routing.
- §2.2.2 FSM-ветка для LOCAL (по выбранной опции).
- Unit + integration тесты.

### Phase 2 (~1 неделя, после CDEK SPEC готов)

- §2.1 `RussianCarrierGatewayReal` для CDEK (1-й carrier).
- Выносим `book_last_mile` из sync `MarkOrderArrivedInRuHandler` в consumer на `OrderArrivedInRuEvent` (ORD-006-style, с ON_HOLD fallback).
- Integration test: full PAID → DELIVERED chain через httpx-mock для CDEK.

### Phase 3 (~3-5 дней, после Yandex LOG-004 готов)

- §2.1 Yandex adapter, routing по `pickup_point.carrier`.
- `RUSSIAN_CARRIER_USE_STUB=false` в prod env.
- E2E на staging: реальный CDEK или Yandex tracking webhook.

### Phase 4 (после Q8 ответа)

- §2.3 inventory pre-check.

### Phase 5 (Q6 после ramp-up)

- DobroPost rate-limit handling (queueing / smoothing).

---

## 5. Definition of done

- [ ] Реальный CDEK booking работает: ARRIVED_IN_RU → real CDEK API call → IN_LAST_MILE с реальным tracking number.
- [ ] LOCAL-supplier orders проходят FSM без DobroPost-вызова.
- [ ] Mixed-supplier orders запрещены на уровне domain.
- [ ] Failure CDEK → `OrderHold(BOOKING_FAILED)` с admin-triage из dashboard.
- [ ] Integration coverage: PAID → DELIVERED для CROSS_BORDER + для LOCAL.
- [ ] `RUSSIAN_CARRIER_USE_STUB=false` в Railway production env.
- [ ] Inventory pre-check включён для все order-create путей (после Q8).
- [ ] DobroPost rate-limit ответ зафиксирован; circuit-breaker правки внесены при необходимости.

---

## 6. Связи

- **Родительский audit:** [[buy-now-audit-2026-05]].
- **Историческая база:** [[audit-order-event-chains-2026-05]].
- **Affects:** order, logistics, payment модули; catalog (inventory).
- **Triggered by:** ответы продукта на Q3 / Q6 / Q7 / Q8 + готовность LOG-004 / CDEK SPEC.

---

*Документ создан 2026-05-18 как разветвление из Buy Now аудита. Не
блокирует Sprint 1 Buy Now flow — выполняется параллельно по своей
timeline.*
