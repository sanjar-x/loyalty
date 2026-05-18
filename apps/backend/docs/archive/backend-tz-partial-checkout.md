---
tags: [project/loyality, backend, api, checkout, cart, tz, archived]
type: tz
date: 2026-04-29
status: archived
audience: backend
superseded_by: "[[ADR-010-buy-now-standalone-endpoint]] (2026-05-18)"
related:
  - "[[SPEC - Frontend Integration Guide]]"
  - "[[BRD Checkout]]"
  - "[[Loyality TRD]]"
---

> [!warning] ARCHIVED — 2026-05-18.
> Этот TZ описывал альтернативный архитектурный подход к Buy Now flow
> (расширение `POST /cart/checkout` параметром `selectedSkuIds`).
> **Не был реализован.** Команда выбрала standalone endpoint
> `POST /api/v1/orders/buy-now`, полностью минующий корзину.
> Решение и сравнение с этим TZ зафиксированы в
> **[[ADR-010-buy-now-standalone-endpoint]]**.
>
> Документ сохранён в archive для исторического контекста и для
> возможного будущего use-case «выбор подмножества в /trash-screen»
> (см. секцию «Related decisions» в ADR-010 — этот scenario не
> покрывается standalone-endpoint решением, при необходимости вернёмся
> к идее `selectedSkuIds` в узком scope).

# TZ — Partial cart checkout (Buy-Now flow) [ARCHIVED]

> **Назначение.** Описывает изменения публичного контракта `Cart Checkout`,
> необходимые для поддержки покупки **подмножества** товаров из корзины
> ("Купить сейчас" с PDP / выборочный чекаут с `/trash`). Текущая
> реализация замораживает корзину целиком, что делает невозможной
> корректную реализацию buy-now без деструктивной обходной логики на
> фронте.

## 1. Контекст

### 1.1 Текущее поведение (v1.0.0, OpenAPI снапшот)

```
POST /api/v1/cart/checkout
Authorization: Bearer
Content-Type: application/json

{ "pickupPointId": "uuid" }
```
**200:**
```json
{
  "attemptId": "uuid",
  "snapshotId": "uuid",
  "expiresAt": "2026-04-28T10:15:00Z"
}
```

Семантика на сегодня:

1. Cart переходит `active → frozen` **целиком**.
2. Создаётся `CheckoutAttempt` + `CheckoutSnapshot` (TTL 15 минут), включающий **все** позиции корзины.
3. `confirm` → cart `frozen → ordered`, **все** позиции уходят в заказ.
4. `cancel` или TTL-expiry → cart `frozen → active` (unfreeze всего).

### 1.2 Бизнес-требование

Frontend должен реализовать UX-сценарий **"Купить сейчас"** на PDP:
- пользователь нажимает "Купить сейчас" на странице товара;
- если в корзине уже есть **другие** товары — оформляется заказ только на этот SKU, **остальные позиции корзины не должны быть затронуты**;
- если корзина пуста или содержит только этот SKU — поведение совпадает с текущим.

Аналогично, `/trash` (страница корзины) уже содержит UI для выбора подмножества позиций (чекбоксы), но без поддержки на бэкенде эта функциональность сейчас работает деструктивно: фронт удаляет невыбранные позиции через `DELETE /cart/items/{sku_id}` перед `/cart/checkout` ([`lib/checkout/useCheckoutFlow.js#prepareCart`](../lib/checkout/useCheckoutFlow.js)). Это:

- **не атомарно**: между `DELETE` и `checkout` пользователь может потерять данные при сбое сети / закрытии вкладки;
- **деструктивно**: пользователь может не понять, что его остальные товары будут удалены навсегда;
- **race-prone**: параллельные сессии в нескольких вкладках могут привести к рассинхрону.

### 1.3 Цель этого TZ

Расширить контракт `/cart/checkout` (и связанные сущности) так, чтобы фронт мог передавать **выбор позиций** атомарно, с гарантиями со стороны бэка. Невыбранные позиции должны оставаться в активной корзине пользователя без потерь.

## 2. Требуемое изменение (high-level)

```
POST /api/v1/cart/checkout
{
  "pickupPointId": "uuid",
  "selectedSkuIds": ["uuid", "uuid"]   // ← НОВОЕ, опциональное
}
```

- При `selectedSkuIds == null` или отсутствует — **обратная совместимость**: текущее поведение (вся корзина).
- При `selectedSkuIds == []` — **422** (`EMPTY_SELECTION`).
- При наличии — в `CheckoutSnapshot` попадают **только** перечисленные SKU; остальные позиции корзины **остаются в `active`**.

## 3. API-контракт (детально)

### 3.1 Diff `InitiateCheckoutRequest`

```diff
 InitiateCheckoutRequest:
   type: object
   required:
     - pickupPointId
   properties:
     pickupPointId:
       type: string
       format: uuid
+    selectedSkuIds:
+      type: array
+      items:
+        type: string
+        format: uuid
+      minItems: 1
+      maxItems: 50            # совпадает с лимитом корзины
+      uniqueItems: true
+      nullable: true
+      description: |
+        Опциональный список SKU из корзины, которые попадут в заказ.
+        Если не передан или null — оформляется вся корзина (legacy-режим).
+        Все UUID должны быть в текущей активной корзине пользователя
+        (или в гостевой корзине по `X-Anonymous-Token`).
+        Дубликаты запрещены.
```

**Замечание:** идентифицируем именно по `sku_id` (а не по `cart_item_id`) — это совпадает с тем, как фронт уже индексирует элементы (`PATCH /cart/items/{sku_id}`, `DELETE /cart/items/{sku_id}`).

### 3.2 Diff `CheckoutInitiatedResponse`

```diff
 CheckoutInitiatedResponse:
   type: object
   required:
     - attemptId
     - snapshotId
     - expiresAt
+    - selectionMode
+    - itemCount
   properties:
     attemptId:
       type: string
       format: uuid
     snapshotId:
       type: string
       format: uuid
     expiresAt:
       type: string
       format: date-time
+    selectionMode:
+      type: string
+      enum: ["full", "partial"]
+      description: |
+        "full" — заморожена вся корзина (legacy).
+        "partial" — заморожены только указанные SKU; остальные остались в active.
+    itemCount:
+      type: integer
+      minimum: 1
+      description: Количество позиций в snapshot (для отображения и логов).
```

Это позволит фронту корректно отрисовать summary-секцию чекаута без лишнего `GET /cart`.

### 3.3 Diff `CartResponse` — добавить флаг partial-freeze

При `selectionMode=partial` корзина **не** меняет глобальный статус на `frozen`. Вместо этого добавляется per-item признак:

```diff
 CartItemResponse:
   ...
+  isFrozen:
+    type: boolean
+    default: false
+    description: |
+      Item зафиксирован в активной попытке оформления.
+      В UI такие позиции должны рендериться как read-only
+      (нельзя менять qty / удалять до confirm/cancel/expire).
```

И на уровне корзины:

```diff
 CartResponse:
   ...
+  hasActiveCheckoutAttempt:
+    type: boolean
+    default: false
+  activeCheckoutAttemptId:
+    type: string
+    format: uuid
+    nullable: true
```

Альтернатива (см. §4) — detached snapshot, при котором cart вообще не меняется. **Рекомендую alternative.**

### 3.4 Новые коды ошибок

| HTTP | Code | Trigger |
|---|---|---|
| 422 | `EMPTY_SELECTION` | `selectedSkuIds` передан и равен `[]` |
| 422 | `UNKNOWN_SKU_IDS` | Некоторые из `selectedSkuIds` отсутствуют в корзине пользователя. `details.unknown_sku_ids: UUID[]` |
| 422 | `DUPLICATE_SKU_IDS` | Дубликаты в массиве. `details.duplicate_sku_ids: UUID[]` |
| 409 | `CHECKOUT_ATTEMPT_IN_PROGRESS` | У пользователя уже есть активный `CheckoutAttempt` (frozen-state, не expired). `details.attempt_id`, `details.expires_at` |
| 409 | `SELECTION_CONFLICT` | Один или несколько SKU из `selectedSkuIds` уже зафиксированы в другой активной попытке (только при design B, in-place freeze) |

**Примечание по `CHECKOUT_ATTEMPT_IN_PROGRESS`:** уже сейчас неявно возможен (если фронт дважды быстро дёрнет `/checkout`), но не выделен отдельным кодом. Предлагаю формализовать.

## 4. Дизайн (два варианта реализации на бэке)

### 4.1 Вариант A — In-place per-item freeze

**Идея:** добавить колонку `cart_items.frozen_attempt_id` (nullable FK на `checkout_attempts.id`). При `partial` — выставляем её для выбранных SKU; все mutations (`PATCH /cart/items/{sku_id}`, `DELETE /cart/items/{sku_id}`) делают `WHERE frozen_attempt_id IS NULL` и возвращают **409** для frozen items.

| Плюсы | Минусы |
|---|---|
| Минимальная миграция БД | Cart "наполовину frozen" — UX-сложность: фронт обязан рендерить per-item state |
| Cart остаётся одной сущностью | Гонки при одновременных попытках усложняют SQL (требуют `SELECT FOR UPDATE` per-row) |
| | Сложнее писать "клиент удалил" → нужна явная разморозка по `attempt_id` |
| | Race: пользователь редактирует qty → backend 409 → UI должен реагировать |

### 4.2 Вариант B — Detached snapshot (рекомендую)

**Идея:** `CheckoutSnapshot` уже хранит копию строк (`snapshot_items`). Усилим этот контракт:

- При `/cart/checkout` создаётся `CheckoutSnapshot` с **копией** выбранных строк (qty, unit_price, sku_id, supplier_type — всё нужное для расчёта тотала).
- **Cart НЕ замораживается**: `cart.status` остаётся `active`, `cart_items.*` не трогаем.
- `confirm` → создаёт Order из snapshot и **удаляет** соответствующие `cart_items` атомарно (одной транзакцией). Невыбранные строки остаются.
- `cancel` / TTL-expire → snapshot помечается `cancelled` / `expired`, cart не трогаем.
- Цена в snapshot фиксируется на момент initiate (как сейчас). При confirm — `price_drift_check` сравнивает текущие цены SKU с зафиксированными; при расхождении (>X%) — 409 `PRICE_CHANGED` (это уже должно быть в текущей реализации как часть BRD).

**Дополнительные требования к Вариант B:**

- **Уникальность активной попытки**: на уровне БД `UNIQUE(cart_id) WHERE status IN ('initiated', 'pending_payment')` — гарантирует, что у одной корзины не может быть двух одновременных снапшотов. Возвращать `CHECKOUT_ATTEMPT_IN_PROGRESS` при попытке создать второй.
- **Валидация на момент confirm**: snapshot хранит `sku_id + qty`; если за время TTL пользователь удалил/уменьшил qty этого SKU в активной корзине, поведение:
  - **Если cart_item ещё содержит >= snapshot.qty** → confirm проходит.
  - **Если меньше** → 409 `CART_DRIFT` с `details.sku_id, details.expected_qty, details.actual_qty`. Фронт показывает реконсилиацию.
- Логически snapshot — read-only DTO, отвязанный от cart_items по семантике, но связанный по FK для трассируемости (`snapshot_items.cart_item_id` nullable, для аудита).

| Плюсы | Минусы |
|---|---|
| Cart полностью свободен — пользователь продолжает шопить | Чуть больше места в БД (но snapshot и так уже есть) |
| Нет per-item locking → проще concurrency | Drift-check при confirm (но это и сейчас должно быть) |
| Multi-tab безопасно: вторая вкладка увидит ту же snapshot, но cart активный | |
| Лёгкий rollback: cancel = drop snapshot | |
| Frontend проще: не нужно рендерить per-item frozen-state | |

**Решение:** **Вариант B** — detached snapshot. Это совпадает с тем, как должна работать классическая e-commerce корзина (Amazon, Wildberries, Ozon — все используют snapshot-pattern для buy-now).

## 5. Семантика по сценариям

### 5.1 `selectedSkuIds = null` (legacy / "Оформить всё")

Текущее поведение сохраняется **дословно**, кроме одного нюанса:

- Если перейдём на Вариант B — cart больше **не** меняет статус на `frozen` глобально. Но фронт сейчас читает `cart.status` для UX-блокировки. Нужна обратная совместимость: при `legacy-mode` (selectedSkuIds=null), снапшот всё равно создаётся со всеми позициями, но cart-level статус **может** оставаться `active`. Фронту это покажется так же, потому что `confirm` всё равно очистит cart.

**Альтернатива для совместимости**: оставить cart-level `frozen` только в legacy-режиме (selectedSkuIds=null). При partial — никогда не frozen. Это предсказуемо и не ломает существующий UI.

### 5.2 `selectedSkuIds = [skuA]`, в корзине {skuA, skuB, skuC}

1. `POST /cart/checkout {pickupPointId, selectedSkuIds:[skuA]}` →
   - Создаём `CheckoutSnapshot{items:[{skuA, qty: cart.qty(skuA)}]}`.
   - `CheckoutAttempt{snapshot_id, mode: "partial"}`.
   - **Cart не меняется**. `GET /cart` всё ещё возвращает 3 позиции.
   - **200**: `{attemptId, snapshotId, expiresAt, selectionMode:"partial", itemCount:1}`.
2. `POST /cart/checkout/confirm {attemptId}` →
   - Проверка `price_drift` для `skuA`.
   - Создаётся `Order` из snapshot.
   - **Атомарно удаляем `cart_items WHERE sku_id = skuA`**.
   - `GET /cart` теперь возвращает 2 позиции (skuB, skuC).
   - **200**: `{orderId}`.
3. `POST /cart/checkout/cancel` (или TTL) →
   - Snapshot → `cancelled`/`expired`.
   - Cart не трогаем.

### 5.3 `selectedSkuIds = [skuA, skuB, skuC]` (все позиции)

Эквивалентно `selectedSkuIds = null` с точки зрения результата. Бэк может оптимизировать (не делать snapshot большой копией), но семантика совпадает.

### 5.4 Параллельный `cart/items` mutation во время initiate

При **Вариант B** cart всегда mutable, поэтому:

- `PATCH /cart/items/{skuA}` пока активный snapshot — **разрешено**. Snapshot уже содержит зафиксированную копию qty, поэтому изменения не повлияют на confirm.
- Но при `confirm` если cart.qty(skuA) < snapshot.qty(skuA) → **409 `CART_DRIFT`** (см. §4.2).
- `DELETE /cart/items/{skuA}` пока snapshot активен → разрешён, но при `confirm` будет drift-fail.

Альтернатива: для UX — на фронте такие SKU рендерим как "В оформлении" с visual lock. Но **бэк не должен это форсить** — это UI-policy.

### 5.5 Гостевая корзина (`X-Anonymous-Token`)

Полностью симметрично авторизованной. Все валидации (`UNKNOWN_SKU_IDS`, `EMPTY_SELECTION` и т.д.) применяются. После `confirm` `Order` всё ещё требует identity (либо guest-checkout email, либо merge'ом в auth). Это вне scope текущего TZ, оставляем как есть.

## 6. Edge cases

| # | Кейс | Ожидаемое поведение |
|---|---|---|
| 1 | Корзина пуста, передан `selectedSkuIds=[someUuid]` | 422 `UNKNOWN_SKU_IDS` |
| 2 | `selectedSkuIds` содержит SKU, который в корзине, но `qty=0` (orphan) | 422 `UNKNOWN_SKU_IDS` (qty=0 = эффективно отсутствует) |
| 3 | `selectedSkuIds=[]` явно | 422 `EMPTY_SELECTION` |
| 4 | `selectedSkuIds` содержит дубликаты `[skuA, skuA]` | 422 `DUPLICATE_SKU_IDS` |
| 5 | `pickupPointId` не привязан к зоне доставки выбранных SKU | Существующая логика `NO_ELIGIBLE_PROVIDERS` / `RATE_CALCULATION_ERROR` (без изменений) |
| 6 | Активная попытка уже существует | 409 `CHECKOUT_ATTEMPT_IN_PROGRESS` (предлагаю `details.attempt_id` чтобы фронт мог `cancel` или дождаться) |
| 7 | Пользователь добавил SKU в корзину **после** initiate, и потом сделал второй initiate с этим SKU | Кейс 6 (есть активная попытка) → 409 |
| 8 | TTL истёк, фронт делает `confirm` | 410 / 409 `ATTEMPT_EXPIRED` (уже должно быть) |
| 9 | Confirm: цена SKU изменилась более чем на 1% | 409 `PRICE_CHANGED` с `details.sku_id, expected, actual` (вне scope, уточнить с продуктом) |
| 10 | Cart содержит cross_border + local SKU, выбран только local | 200, snapshot с одной supplier-группой. Logistics quote должен быть согласован с поставщиками выбранных SKU (это уже логика `/logistics/rates/quote`). |

## 7. Backward compatibility

| Клиент | Поведение |
|---|---|
| Старый фронт (selectedSkuIds не отправляет) | Работает как раньше (legacy-mode). Никакого breaking change. |
| Новый фронт + старый бэк (если зарелизится раньше) | Бэк проигнорирует неизвестное поле. Фронт получит legacy-поведение и должен это уметь обработать (выводить ошибку при попытке partial-checkout). |

**Версионирование**: изменение **аддитивное** — нет нужды бампать `/api/v1` → `/api/v2`. Достаточно минорной ревизии OpenAPI и changelog-нотиса.

## 8. Миграции / DB schema

### Вариант B (рекомендован):

```sql
-- 0042_checkout_snapshot_items_independent.sql
ALTER TABLE checkout_snapshot_items
  ADD COLUMN cart_item_id UUID NULL REFERENCES cart_items(id) ON DELETE SET NULL;

ALTER TABLE checkout_attempts
  ADD COLUMN selection_mode VARCHAR(16) NOT NULL DEFAULT 'full'
    CHECK (selection_mode IN ('full', 'partial')),
  ADD COLUMN selected_sku_ids UUID[] NULL;  -- для аудита, не для логики

-- Гарантия одной активной попытки на корзину
CREATE UNIQUE INDEX uq_checkout_attempts_active_per_cart
  ON checkout_attempts (cart_id)
  WHERE status IN ('initiated', 'pending_payment');
```

### Если Вариант A:

```sql
ALTER TABLE cart_items
  ADD COLUMN frozen_attempt_id UUID NULL REFERENCES checkout_attempts(id) ON DELETE SET NULL;

CREATE INDEX ix_cart_items_frozen_attempt ON cart_items(frozen_attempt_id) WHERE frozen_attempt_id IS NOT NULL;
```

Плюс существенные изменения во всех cart-mutation use-case'ах (везде `WHERE frozen_attempt_id IS NULL`).

## 9. Acceptance criteria

- [ ] `OpenAPI` обновлён с новыми полями `InitiateCheckoutRequest.selectedSkuIds`, `CheckoutInitiatedResponse.selectionMode/itemCount`.
- [ ] Все 5 новых кодов ошибок (`EMPTY_SELECTION`, `UNKNOWN_SKU_IDS`, `DUPLICATE_SKU_IDS`, `CHECKOUT_ATTEMPT_IN_PROGRESS`, `CART_DRIFT`) задокументированы в общей error-таблице (`SPEC §3`).
- [ ] Legacy-вызов (без `selectedSkuIds`) работает идентично текущей реализации (regression-тесты обязательны).
- [ ] При `selectionMode=partial` cart НЕ меняет глобальный статус (`active` сохраняется).
- [ ] `confirm` атомарно удаляет выбранные `cart_items` (одна транзакция с `INSERT INTO orders`).
- [ ] `cancel` / TTL-expire НЕ затрагивают cart.
- [ ] Уникальный constraint на активную попытку в БД (защита от race).
- [ ] Все кейсы из §6 покрыты integration-тестами.
- [ ] OpenLineage / observability: лог `cart.checkout.initiate` содержит `mode`, `selected_count`, `cart_total_count`.

## 10. Test plan

### 10.1 Unit
- Валидация `selectedSkuIds` (пустой, дубли, неизвестные UUID).
- Snapshot creation: правильный набор позиций, правильный total.

### 10.2 Integration
- E2E happy path: PDP → buy-now → checkout с partial → confirm → проверка, что в orders 1 строка, в cart остались остальные.
- E2E concurrent: два initiate подряд в разных вкладках → второй получает 409.
- E2E mutation during checkout: initiate → PATCH /cart/items на frozen SKU → 200 при варианте B; confirm с drift → 409.
- E2E TTL: initiate → подождать 16 минут → confirm → 410 → cart untouched.
- E2E cancel: initiate → cancel → cart полностью intact.

### 10.3 Property-based / fuzz
- Случайные `selectedSkuIds` из cart размера N=1..50; все confirm должны корректно отделять выбранное от остального.

## 11. Telemetry

Добавить в `cart.checkout.initiate` event:
```json
{
  "mode": "full|partial",
  "selected_count": 1,
  "cart_total_count": 5,
  "supplier_types": ["cross_border", "local"],
  "request_id": "..."
}
```
Метрики:
- `checkout_initiate_total{mode}` — counter.
- `checkout_partial_selected_ratio` — histogram (доля выбранных от cart).
- `checkout_drift_total{reason}` — counter (`PRICE_CHANGED`, `CART_DRIFT`).

## 12. Frontend integration contract

После релиза бэка фронт обновит:

1. `lib/store/api.js#initiateCheckout` — добавить поле в body:
   ```js
   body: { pickupPointId, selectedSkuIds: skuIds.length ? skuIds : null }
   ```
2. `lib/checkout/useCheckoutFlow.js#prepareCart` — **удалить логику `removeCartItem`** (это станет обязанностью бэка). Вместо этого `placeOrder` напрямую передаст `selectedSkuIds`.
3. Удалить ConfirmSheet "Оформить только этот? Остальные будут удалены" — теперь модалка может говорить безопасно: "Оформить только этот товар, остальные останутся в корзине."
4. UX для `CHECKOUT_ATTEMPT_IN_PROGRESS`: показать "У вас уже есть незавершённое оформление" + кнопки `[Продолжить]` (восстановить attempt) и `[Отменить и начать заново]` (cancel + re-initiate).

## 13. Открытые вопросы (требуют решения с продуктом)

- [ ] **Q1**: При `CART_DRIFT` (qty в корзине стало меньше snapshot) — разрешать ли `confirm` с фактическим qty или жёстко требовать reconciliation? Рекомендация: жёсткий 409, фронт делает re-quote.
- [ ] **Q2**: Лимит `selectedSkuIds` = 50 (равен лимиту корзины). Ок или нужно меньше?
- [ ] **Q3**: Нужен ли `cart_item_id` вместо `sku_id` в API (если у одного SKU могут быть несколько строк корзины из-за разных конфигураций)? **Анализ:** на сегодня cart индексируется по `sku_id` — одна позиция = один SKU. Если в будущем добавятся конфигурируемые продукты (gift-card с persona, custom engraving) — потребуется `cart_item_id`. Рекомендация: оставить `sku_id` сейчас, мигрировать на `cart_item_id` при появлении конфигурируемых SKU.
- [ ] **Q4**: Confirm на partial-checkout — нужно ли возвращать обновлённый `CartResponse` в ответе (чтобы фронт без extra round-trip обновил `/trash`)? Рекомендация: да, добавить `cart` в `CheckoutConfirmedResponse`.

## 14. Roadmap / rollout

| Шаг | Описание | Ответственный |
|---|---|---|
| 1 | Утверждение дизайна (вариант A vs B) | Backend lead + Product |
| 2 | DB миграция (Вариант B) | Backend |
| 3 | Реализация + unit-тесты | Backend |
| 4 | Обновление OpenAPI + публикация changelog | Backend |
| 5 | Интеграционные E2E на staging | QA |
| 6 | Frontend интеграция (см. §12) | Frontend |
| 7 | Включение buy-now на PDP за feature-flag (canary) | Frontend + DevOps |
| 8 | Полный релиз | — |

## 15. Связанные документы

- [SPEC — Frontend Integration Guide §7.4](../SPEC%20-%20Frontend%20Integration%20Guide.md) — текущий контракт checkout.
- [docs/tz.md](./tz.md) — общая ТЗ проекта.
- `lib/checkout/store.js` — frontend state machine (для понимания требуемого UX).
- `lib/checkout/useCheckoutFlow.js#prepareCart` — деструктивный workaround, который этот TZ устраняет.
