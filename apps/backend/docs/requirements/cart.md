# Business Requirements Document: Корзина покупок

**Версия:** 3.1 | **Дата:** 2026-03-28 | **Статус:** Reviewed (3 rounds, 15 auditors, 308 findings) | **Владелец:** Product Team

---

## Часть I. Контекст — Почему мы это делаем

---

### 1. Бизнес-цель

Покупатель собирает товары из разных источников в одну корзину и оформляет заказ с доставкой в локальный ПВЗ — без взаимодействия с иностранными маркетплейсами напрямую.

### 2. Бизнес-модель платформы

Гибридная e-commerce платформа — **агрегатор и дропшиппер** (аналог Farfetch):

- Платформа **не имеет собственного склада**
- Товар закупается на стороне поставщика/маркетплейса **после оплаты** покупателем
- Доставка — через логистических партнёров в локальные ПВЗ
- Доход — **наценка** к закупочной цене
- Цена в каталоге (`SKU.price`) — это **конечная цена для покупателя в RUB**, уже содержащая наценку и конвертацию

### 3. Два типа источников товаров

Это ключевое разделение, определяющее всю логику корзины:

|                | Из Китая (`CROSS_BORDER`)                                     | Из наличия (`LOCAL`)                    |
| -------------- | ------------------------------------------------------------- | --------------------------------------- |
| **Поставщики** | Poizon, Taobao, Pinduoduo, 1688                               | Локальные и российские                  |
| **В каталоге** | `Product.supplier_id` → Supplier(CROSS_BORDER) + `source_url` | `Product.supplier_id` → Supplier(LOCAL) |
| **Закупка**    | Выкуп на маркетплейсе после оплаты                            | Передача заказа поставщику              |
| **Доставка**   | ~10–25 дней                                                   | ~2–7 дней                               |
| **Возврат**    | Невозможен (кроме брака)                                      | Стандартный (7 дней)                    |
| **Риски**      | Может быть недоступен; курсовые колебания                     | Поставщик подтверждает наличие          |
| **Цена**       | Оператор: CNY → конвертация → наценка → RUB                   | Оператор: RUB → наценка → RUB           |

Это разделение влияет на: группировку в корзине, дисклеймеры, сроки доставки, return policy, fulfillment_type в событии checkout, и работу оператора.

### 4. Основной канал: Telegram Mini App

Платформа работает преимущественно через Telegram Mini App, что определяет UX-ограничения:

- Ограниченный WebView + нативная панель Telegram
- Навигация: `MainButton` (CTA), `BackButton` (назад) — Telegram WebApp API
- Пользователь аутентифицирован через `initData` (модуль Identity)
- Нет вкладок — приложение открыто или закрыто
- Может быть свёрнуто в любой момент (входящий звонок)
- Touch-first: минимальные tap-target 44×44px
- Ненадёжная мобильная сеть → UI-операции должны быть оптимистичны

### 5. Валюта

**Каноническая валюта: RUB (Российский рубль).**

- `Money(amount: int, currency: str)` — суммы в **минимальных единицах валюты** (копейки)
  - RUB: `amount = 100000` = **1 000.00 руб** (minor_units = 2)
- `DEFAULT_CURRENCY` = `"RUB"` (уже установлено в каталоге, изменение не требуется)
- Конвертация CNY → RUB — на этапе создания/обновления SKU в Catalog BC, не в Cart
- Форматирование: `1 000 ₽` или `1 000 руб`, с двумя десятичными знаками для дробных сумм

### 6. Текущие модули системы

| Модуль                       | Статус              | Что даёт корзине                                                    |
| ---------------------------- | ------------------- | ------------------------------------------------------------------- |
| **Catalog**                  | Готов               | Product → Variant → SKU → `price: Money`, `is_active`, `source_url` |
| **Supplier**                 | Готов               | `SupplierType` (CROSS_BORDER / LOCAL), `ISupplierQueryService`      |
| **Identity**                 | Готов               | `customer_id` из JWT / Telegram `initData`                          |
| **User**                     | Готов               | Профили покупателей                                                 |
| **Geo**                      | Готов               | ПВЗ для выбора точки доставки                                       |
| **Cart**                     | **Нужно построить** | —                                                                   |
| Order, Payment, Notification | Не реализованы      | Будут зависеть от Cart                                              |

---

## Часть II. Пользователи — Кто и что делает

---

### 7. Роли

| Роль           | Канал             | Ключевая потребность                                |
| -------------- | ----------------- | --------------------------------------------------- |
| **Покупатель** | Telegram Mini App | Собрать товары, понять сроки и цены, оформить в ПВЗ |
| **Web-гость**  | Браузер (без TG)  | Собрать корзину до авторизации                      |
| **Оператор**   | Admin Panel       | Видеть source_url и поставщика для закупки          |

### 8. User Stories

**Основной путь покупателя (P0):**

| ID    | Как...     | Я хочу...                                              | Чтобы...                       |
| ----- | ---------- | ------------------------------------------------------ | ------------------------------ |
| US-01 | покупатель | добавить товар в корзину                               | собрать заказ                  |
| US-02 | покупатель | видеть содержимое корзины                              | проверить состав               |
| US-03 | покупатель | изменить количество                                    | заказать нужное количество     |
| US-04 | покупатель | удалить товар                                          | убрать ненужное                |
| US-05 | покупатель | видеть итого с разбивкой                               | понимать сколько заплачу       |
| US-06 | покупатель | видеть "Из Китая" / "Быстрая доставка" с маркетплейсом | знать сроки и условия возврата |
| US-07 | покупатель | оформить заказ за 2-3 шага                             | не тратить время               |
| US-08 | покупатель | выбрать ПВЗ (предзаполнен последний)                   | забрать удобно                 |

**Доверие и прозрачность (P1):**

| ID    | Как...     | Я хочу...                               | Чтобы...                   |
| ----- | ---------- | --------------------------------------- | -------------------------- |
| US-11 | покупатель | видеть предупреждение о недоступности   | не оплатить несуществующее |
| US-12 | покупатель | видеть предупреждение об изменении цены | принять осознанное решение |
| US-14 | покупатель | вернуться к прерванному checkout        | не потерять прогресс       |
| US-15 | покупатель | удалить все недоступные одной кнопкой   | быстро перейти к checkout  |
| US-16 | покупатель | видеть зачёркнутую цену                 | понимать выгоду            |

**Гостевой путь (P1):**

| ID    | Как...    | Я хочу...                         | Чтобы...                  |
| ----- | --------- | --------------------------------- | ------------------------- |
| US-09 | web-гость | собрать корзину без регистрации   | ознакомиться с платформой |
| US-10 | web-гость | после авторизации увидеть корзину | не потерять товары        |

**Дополнительные (P2+):**

| ID    | Как...     | Я хочу...                              | Чтобы...              |
| ----- | ---------- | -------------------------------------- | --------------------- |
| US-13 | покупатель | очистить корзину одним действием       | начать заново         |
| US-17 | покупатель | сохранить товар на потом               | не терять интересное  |
| US-18 | оператор   | видеть ссылку на товар на маркетплейсе | оформить закупку      |
| US-19 | оператор   | видеть поставщика каждой позиции       | знать у кого закупать |

---

## Часть III. Модель данных — Из чего состоит корзина

---

### 9. Cart — Aggregate Root

Одна активная корзина на пользователя. Содержит список позиций, состояние, версию для конкурентного контроля.

**Поля агрегата:**

| Поле                      | Тип              | Описание                                         |
| ------------------------- | ---------------- | ------------------------------------------------ |
| `cart_id`                 | UUID             | Идентификатор                                    |
| `customer_id`             | UUID \| None     | Авторизованный владелец                          |
| `anonymous_id`            | str \| None      | Гостевой владелец                                |
| `status`                  | CartStatus       | Текущее состояние (FSM)                          |
| `currency`                | str              | Валюта корзины (устанавливается первым товаром)  |
| `version`                 | int              | Оптимистичная блокировка                         |
| `payment_reference_id`    | UUID \| None     | Генерируется при initiate checkout               |
| `frozen_at`               | datetime \| None | Когда заморозили                                 |
| `frozen_until`            | datetime \| None | Дедлайн заморозки (безусловный timeout)          |
| `abandonment_notified_at` | datetime \| None | Когда последний раз отправили CartAbandonedEvent |
| `created_at`              | datetime         | —                                                |
| `updated_at`              | datetime         | Обновляется при мутациях (определяет TTL)        |

### 10. CartItem — Entity внутри агрегата

Каждая позиция — это конкретный SKU с количеством и снимком каталожных данных.

**Идентичность:** `item_id: UUID` — внутренний ID (для API). `sku_id: UUID` — бизнес-ключ (для дедупликации: если SKU уже в корзине → merge количества).

| Поле                  | Тип                 | Описание                                                                |
| --------------------- | ------------------- | ----------------------------------------------------------------------- |
| `item_id`             | UUID                | Уникальный ID позиции                                                   |
| `sku_id`              | UUID                | Ссылка на SKU (business key)                                            |
| `quantity`            | int (1–99)          | Количество                                                              |
| `unit_price`          | Money               | Текущая snapshot цены (обновляется при ревалидации)                     |
| `original_unit_price` | Money               | Цена на момент добавления (никогда не меняется, baseline для 5% порога) |
| `compare_at_price`    | Money \| None       | Зачёркнутая цена (snapshot)                                             |
| `price_snapshot_at`   | datetime            | Когда последний раз обновлён snapshot                                   |
| `snapshot`            | CatalogItemSnapshot | ACL-перевод каталожных данных                                           |

### 11. CatalogItemSnapshot — Value Object (ACL)

Frozen VO, инкапсулирующий данные из Catalog и Supplier контекстов. Создаётся при добавлении товара, обновляется при ревалидации.

| Поле                | Источник                    | Зачем                                                              |
| ------------------- | --------------------------- | ------------------------------------------------------------------ |
| `product_id`        | Product.id                  | Навигация, группировка                                             |
| `variant_id`        | ProductVariant.id           | Формирование заказа                                                |
| `brand_id`          | Product.brand_id            | Аналитика, отчёты по брендам в Order BC                            |
| `category_id`       | Product.primary_category_id | Аналитика, отчёты по категориям                                    |
| `product_name_i18n` | Product.title_i18n          | Полный i18n dict для рендера в любой локали                        |
| `variant_name_i18n` | ProductVariant.name_i18n    | Полный i18n dict характеристик                                     |
| `sku_code`          | SKU.sku_code                | Уникальный код                                                     |
| `image_url`         | MediaAsset.url (role=MAIN)  | Изображение                                                        |
| `supplier_id`       | Product.supplier_id         | Sub-orders в Order BC                                              |
| `supplier_type`     | Supplier.type               | Группировка "Из Китая"/"Быстрая доставка"                          |
| `supplier_name`     | Supplier.name               | Poizon / Taobao / Алексей                                          |
| `source_url`        | Product.source_url          | Ссылка на маркетплейс (для оператора)                              |
| `country_of_origin` | Product.country_of_origin   | Compliance, отображение                                            |
| `return_policy`     | Derived: supplier_type      | `"standard"` (local) / `"limited"` (cross_border)                  |
| `fulfillment_type`  | Derived: supplier_type      | `"direct_order"` (local) / `"deferred_procurement"` (cross_border) |

**Откуда берутся данные:** Cart handler вызывает `ICatalogQueryService.get_sku_snapshot(sku_id)` (порт Cart) и `ISupplierQueryService.get_supplier_info(supplier_id)` (порт Supplier). Адаптер в модулярном монолите делает JOIN по ORM моделям.

---

## Часть IV. Поведение — Как работает корзина

---

### 12. Создание корзины

`POST /api/v1/carts` — get-or-create семантика:
- Если у пользователя (customer_id / anonymous_id) уже есть ACTIVE корзина → вернуть её (HTTP 200)
- Если нет → создать новую: `status=ACTIVE`, `version=1`, `currency=None` (установится первым товаром)
- Публикуется `CartCreatedEvent` только при создании новой
- Frontend может вызывать этот endpoint при загрузке app, чтобы получить `cart_id` и `version` для последующих `If-Match` headers

### 13. Добавление товара

**Цепочка:** Покупатель нажимает "В корзину" → система проверяет статус корзины → проверяет товар → фиксирует snapshot → добавляет позицию.

**Входные ограничения (все обязательны):**

| #   | Проверка                                                           | Ошибка при нарушении               |
| --- | ------------------------------------------------------------------ | ---------------------------------- |
| 0   | `Cart.status = ACTIVE`                                             | `INVALID_CART_STATE` (422)         |
| 1   | `SKU.is_active = true`                                             | `SKU_UNAVAILABLE` (422)            |
| 2   | `Product.status = PUBLISHED`                                       | `SKU_UNAVAILABLE` (422)            |
| 3   | `Product.supplier_id IS NOT NULL`                                  | `NO_SUPPLIER_ASSIGNED` (422)       |
| 4   | `Supplier.is_active = true`                                        | `SUPPLIER_INACTIVE` (422)          |
| 5   | `effective_price` = `SKU.price ?? Variant.default_price` не null   | `NO_PRICE_AVAILABLE` (422)         |
| 6   | Валюта SKU = валюта корзины (или корзина пуста — берём валюту SKU) | `CURRENCY_MISMATCH` (422)          |
| 7   | Количество уникальных SKU < 50                                     | `MAX_CART_ITEMS_EXCEEDED` (400)    |
| 8   | Количество данного SKU ≤ 99                                        | `MAX_ITEM_QUANTITY_EXCEEDED` (400) |

**Поведение при дубликате:** Если SKU уже в корзине → увеличить `quantity` (merge), а не создавать вторую позицию.

**Snapshot:** При добавлении фиксируются `unit_price`, `compare_at_price`, `price_snapshot_at = now()` и `CatalogItemSnapshot`.

### 14. Изменение количества и удаление

- `PATCH .../items/{item_id}` с `quantity` — обновить количество
  - `quantity = 0` → эквивалент удаления
  - `quantity > 99` → `MAX_ITEM_QUANTITY_EXCEEDED`
- `DELETE .../items/{item_id}` — удалить позицию
- `DELETE .../items` — очистить всю корзину
- Все мутации проверяют `status = ACTIVE` (иначе `INVALID_CART_STATE`, 422)
- Все мутации инкрементируют `version` и обновляют `updated_at`

### 15. Ценообразование

**Цены появляются в корзине в 3 момента:**

```
① Snapshot при добавлении ─→ ② Lazy refresh при просмотре ─→ ③ Strict ревалидация при checkout
```

**① Snapshot:** `effective_price = SKU.price ?? Variant.default_price`, фиксируется с `price_snapshot_at`.

**② Lazy check (при GET корзины, read-only — не пишет в БД):** Если `price_snapshot_at` старше 24 часов:
- Query handler запрашивает актуальные цены из каталога **в памяти** (не персистит)
- В read model возвращается `is_stale = true` + `current_catalog_price` рядом с `snapshot_price`
- Фактическое обновление snapshot происходит **только** при следующей мутации (add/update/clear) или при strict ревалидации (checkout)
- Это сохраняет CQRS: GET = чистое чтение, запись только через команды

**③ Strict ревалидация (при ACTIVE → FROZEN):**
- Цена снизилась → обновить, **показать** покупателю (позитивный сигнал: "Цена снизилась!")
- Цена выросла ≤5% → обновить, **показать** покупателю (строка со старой и новой ценой), но **не блокировать** checkout
- Цена выросла >5% → `PRICE_CHANGED` (422), список изменений, **блокировать** checkout до подтверждения
- Товар снят с продажи → `ITEMS_UNAVAILABLE` (422)

**Принцип:** любое изменение цены **видимо** покупателю. Порог 5% определяет только блокировку checkout, не видимость.

**Порог 5%** считается от `original_unit_price` (цена при добавлении, неизменяемая). Это предотвращает кумулятивный drift: без этого 5× подряд +4.9% = 27% повышение без уведомления. После подтверждения `unit_price` обновляется, но `original_unit_price` **не меняется**.

**Pricing Pipeline (расчёт итогов):**

```
effective_price × quantity = item_subtotal         (для каждой позиции)
Σ(item_subtotals) = cart_subtotal                  (сумма)
cart_subtotal - discount_total = taxable_total      (MVP: discount = 0)
taxable_total × 12/112 = vat_amount                 (извлечение НДС, информационно)
taxable_total + delivery_estimate = grand_total     (MVP: delivery = 0)
round(grand_total) → по правилам валюты             (RUB: до копеек, 2 знака, Banker's Rounding)
```

**Скидки (будущее):** Распределяются по позициям **до** расчёта налога. Алгоритм Фаулера — последний item получает остаток.

### 16. Жизненный цикл корзины (State Machine)

**Корзина проходит цепочку состояний:**

```
                    ┌─────────────────────────────────────┐
                    │                                     │
[Создание] → ACTIVE ──→ FROZEN ──→ ORDERED                │
                │           │                             │
                │           ├── payment failed ───────────┘
                │           ├── user cancelled
                │           └── timeout 30 мин (безусловный)
                │
                ├──→ MERGED (при логине guest → auth)
                └──→ EXPIRED (TTL истёк)
```

| Состояние   | Что происходит                     | Можно менять содержимое? | Как истекает                  |
| ----------- | ---------------------------------- | ------------------------ | ----------------------------- |
| **ACTIVE**  | Покупатель собирает корзину        | Да                       | 30 дней (auth) / 24 ч (guest) |
| **FROZEN**  | Checkout начат, цены зафиксированы | Нет                      | 30 мин (безусловный timeout)  |
| **ORDERED** | Заказ создан                       | Нет (терминал)           | Архив                         |
| **MERGED**  | Влита в другую корзину             | Нет (терминал)           | Архив                         |
| **EXPIRED** | Время вышло                        | Нет (терминал)           | Удаление                      |

**Transitions с guard-условиями:**

| Из → В           | Когда / Условия                                                                                                                                    |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| ACTIVE → FROZEN  | Корзина не пуста + все SKU available + все поставщики active + цены ревалидированы + единая валюта + `grand_total > 0`                             |
| FROZEN → ORDERED | Оплата подтверждена + `pickup_point_id` предоставлен                                                                                               |
| FROZEN → ACTIVE  | Оплата не прошла / пользователь отменил / timeout 30 мин (безусловный)                                                                             |
| ACTIVE → MERGED  | Пользователь авторизовался, гостевая корзина вливается. **Guard:** user cart status = ACTIVE (если FROZEN — merge отложен, guest cart сохраняется) |
| ACTIVE → EXPIRED | Нет мутирующей активности дольше TTL                                                                                                               |

**Что считается "активностью":** Только мутации (add, remove, update quantity, clear). GET-запросы **не сбрасывают** TTL.

**Таймауты:** Фоновые задачи TaskIQ:
- Frozen timeout: каждые 5 мин, `WHERE status='frozen' AND frozen_until < now()` — **безусловный**, без проверки payment. Если оплата прошла, но confirm не вызван → cart unfreezes, confirm вернёт 422, Payment BC обработает ситуацию через компенсацию (auto-refund). Это предотвращает deadlock (навечно FROZEN корзина).
- Active expiration: ежедневно 03:00 U
| ID    | Как...     | Я хочу...                               | Чтобы...                   |
| ----- | ---------- | --------------------------------------- | -------------------------- |
| US-11 | покупатель | видеть предупреждение о недоступности   | не оплатить несуществующее |
| US-12 | покупатель | видеть предупреждение об изменении цены | принять осознанное решение |
| US-14 | покупатель | вернуться к прерванному checkout        | не потерять прогресс       |
| US-15 | покупатель | удалить все недоступные одной кнопкой   | быстро перейти к checkout  |
| US-16 | покупатель | видеть зачёркнутую цену                 | понимать выгоду            | TC |

### 17. Checkout — от корзины к заказу

Checkout — **двухшаговый** процесс:

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Шаг 1: Initiate                                                            │
│ POST /carts/{id}/checkout                                                  │
│                                                                            │
│ ① SELECT FOR UPDATE (pessimistic lock)                                     │
│ ② Strict ревалидация цен                                                   │
│ ③ Проверка доступности SKU + поставщиков                                   │
│ ④ Валидация grand_total > 0                                                │
│ ⑤ Генерация payment_reference_id                                           │
│ ⑥ ACTIVE → FROZEN (frozen_at = now, frozen_until = now + 30 мин)           │
│ ⑦ Ответ: frozen cart + payment_reference_id + pricing breakdown            │
│                                                                            │
│ При проблемах:                                                             │
│ • Цена >5% → 422 PRICE_CHANGED (список, нужно подтверждение)               │
│ • SKU недоступен → 422 ITEMS_UNAVAILABLE                                   │
│ • Поставщик неактивен → 422 SUPPLIER_INACTIVE                              │
└────────────────────────────────────────────────────────────────────────────┘
                                    ↓
                        Frontend обрабатывает оплату через Payme/Click SDK
                        (payment_reference_id + grand_total)
                        Пользователь видит единый flow: "Оплатить" → форма → "Заказ оформлен"
                        Confirm вызывается автоматически при success callback (невидимо)
                                    ↓
┌────────────────────────────────────────────────────────────────────────────┐
│ Шаг 2: Confirm                                                             │
│ POST /carts/{id}/checkout/confirm { pickup_point_id }                      │
│                                                                            │
│ ① SELECT FOR UPDATE (pessimistic lock — mutual exclusion с cancel)         │
│ ② Проверка: status == FROZEN                                               │
│ ③ Проверка: frozen_until > now()                                           │
│ ④ FROZEN → ORDERED                                                         │
│ ⑤ Публикация CartCheckedOutEvent через Outbox                              │
│ ⑤ Ответ: 200 OK                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

**Откат:**

| Сценарий             | Действие                                                                                                                             |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Пользователь отменил | `POST .../checkout/cancel` → FROZEN → ACTIVE, очистка payment_reference_id                                                           |
| Оплата не прошла     | `POST .../checkout/cancel` с reason `"payment_failed"`                                                                               |
| Timeout 30 мин       | Фоновая задача: FROZEN → ACTIVE **безусловно**. Если payment уже прошёл но confirm не вызван — Payment BC компенсирует (auto-refund) |

**ПВЗ:** `pickup_point_id` передаётся при confirm, не хранится на Cart (pass-through в событие). Валидация — ответственность Order BC. Система предзаполняет последний использованный ПВЗ.

### 18. Гостевая корзина и слияние

**Telegram-пользователи:** Авторизованы по умолчанию через `initData` → `customer_id`. Гостевая корзина им не нужна.

**Web-пользователи:** `anonymous_id` = `secrets.token_urlsafe(32)`, secure httpOnly cookie. TTL = 24 часа.

**При авторизации — Silent Merge:**

```
Нет гостевой корзины       → загрузить корзину пользователя
Есть гостевая, нет user    → привязать гостевую к customer_id
User cart в статусе FROZEN → merge ОТЛОЖЕН, guest cart сохраняется как есть
                             (merge выполнится после unfreeze: FROZEN → ACTIVE)
Есть обе (user = ACTIVE)   → Merge:
  ├── Одинаковый SKU       → сохранить БОЛЬШЕЕ количество (не суммировать)
  │                          (при равенстве — оставить из user cart)
  ├── Уникальная позиция   → добавить
  ├── Лимит >50            → оставить USER items первыми (осознанный выбор),
  │                          заполнить остаток GUEST items (по price_snapshot_at DESC)
  │                          Вытесненные guest items включаются в CartMergedEvent
  ├── Валюта               → если валюты разные → merge отклонён (CURRENCY_MISMATCH),
  │                          guest cart сохраняется, пользователь выбирает вручную
  └── Гостевая             → статус MERGED
```

**Concurrency:** SELECT FOR UPDATE на обеих корзинах в одной транзакции. Повторный merge → 409 (guest уже MERGED).

### 19. Обработка недоступности и изменений

**Lazy-проверка (при GET):**
- SKU: `is_active`, Product: `status=PUBLISHED`, Supplier: `is_active`
- Недоступные: `is_available = false` + причина (`sku_inactive` / `product_unpublished` / `supplier_inactive`)
- Не удалять автоматически — покупатель решает
- Кнопка "Удалить все недоступные" — one-tap action

**Strict-проверка (при checkout):**
- Недоступные позиции → блокируют ACTIVE → FROZEN (422)

**Изменение supplier_type:** Если supplier_type изменился → обновить snapshot, уведомить о новых сроках.

### 20. Procurement Failure и Refund Policy

Для cross_border товаров — **неустранимый риск**: товар может быть недоступен при закупке.

| Ситуация                         | Политика                                                                                                           |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| Cross-border не удалось закупить | Платформа инициирует возврат в течение 3 рабочих дней. Зачисление на карту — до 14 рабочих дней (зависит от банка) |
| Local не удалось заказать        | Платформа инициирует возврат в течение 1 рабочего дня. Зачисление — до 14 рабочих дней                             |

Это ответственность Order BC, но **политика раскрывается покупателю при checkout** (дисклеймер обязателен).

`CartCheckedOutEvent` содержит `fulfillment_type` per item:
- `"deferred_procurement"` (cross_border) → Order BC запускает Saga закупки
- `"direct_order"` (local) → Order BC передаёт заказ поставщику

**Dispute resolution (ответственность Order BC, но контракт определяется здесь):**
- Покупатель подаёт претензию: фото проблемы → чат поддержки → рассмотрение за 24 часа
- Основания: брак, несоответствие описанию (другой цвет/размер/материал), повреждение при доставке
- Решения: частичный возврат, store credit, повторный заказ со скидкой
- `CartCheckedOutEvent` содержит `return_policy` per item для маршрутизации претензий

**Checkout confirm response (контракт с Order BC):**
```
POST /checkout/confirm → 200 OK
{
  order_reference_id: UUID,       // для перехода к tracking
  estimated_delivery: {min_days, max_days},
  next_steps_url: "/orders/{id}"  // deep link на страницу заказа
}
```
Это обеспечивает бесшовный переход от корзины к отслеживанию заказа.

---

## Часть V. Информационная прозрачность — Что видит покупатель

---

### 21. Отображение корзины

**Каждая позиция показывает:**
- Изображение + название + вариант
- Цена за единицу и сумма позиции
- Зачёркнутая цена (`compare_at_price`), если есть
- Бейдж: **"Из Китая"** (Poizon / Taobao / etc.) или **"Быстрая доставка"**
- Страна происхождения
- Возвратность: "Возврат возможен" / "Возврат ограничен"

**Группировка по источнику (два уровня):**

- **"Из Китая"** — с sub-группами по маркетплейсу (разные уровни доверия):
  - **Poizon:** *"Оригинальные товары с проверкой подлинности. Доставка ~14–25 дней."* + бейдж аутентификации
  - **Taobao / Pinduoduo / 1688:** *"Товары с китайских маркетплейсов. Мы закупаем и доставляем. Доставка ~10–20 дней."*
- **"Быстрая доставка":** *"Доступно от локальных поставщиков. Доставка ~2–7 дней."*

Sub-группировка внутри "Из Китая" по `supplier_name` — визуальная (заголовок + бейдж), не влияет на checkout flow. Данные уже есть в `CatalogItemSnapshot.supplier_name`.

**Доставка:** Показывать рассчитанные даты: *"Ожидаемая доставка: ~7 апреля – 28 апреля"* (frontend: `today + min_days` / `today + max_days`, календарные дни).

**Итоговый блок:**
- Подитого товаров → Скидка (если есть) → Доставка (MVP: бесплатно) → **Итого к оплате** (крупно) → В т.ч. НДС 12% (мелко)

**Пустая корзина:** "Ваша корзина пуста" + CTA "Перейти в каталог".

### 22. Trust Signals и дисклеймеры при checkout

**Trust signals (видимы на экране checkout до оплаты):**

- Гарантия возврата: значок щита + *"100% возврат денег, если товар не удастся закупить"*
- Статистика платформы: *"X 000+ заказов доставлено"* (когда будет достаточно данных)
- Для Poizon-товаров: бейдж *"Проверка подлинности Poizon"* (отдельно от Taobao/1688)
- Юридические реквизиты платформы (ИНН, адрес) — доступны по ссылке

**Дисклеймеры (дружественный тон, не юридический):**

Короткая версия (видна по умолчанию):
1. *"Мы закажем ваш товар на {marketplace_name} сразу после оплаты. Если что-то пойдёт не так — вернём деньги полностью."*
2. *"Товары из Китая не подлежат возврату, кроме случаев брака или несоответствия описанию (например: пришёл другой цвет, другой размер, повреждённая упаковка)."*
3. *"На заказы из Китая стоимостью свыше порога таможенной пошлины могут быть начислены дополнительные сборы при получении."*

Полная версия (по ссылке "Подробные условия"):
- Определение "брак" и "несоответствие описанию" с примерами
- Процесс подачи претензии: сфотографировать → написать в чат → рассмотрение за 24 часа
- Сроки возврата: *"Мы инициируем возврат в течение 3 рабочих дней. Зачисление на карту зависит от вашего банка и может занять до 14 рабочих дней."*
- Ссылка на политику возврата/отмены

### 23. Локализация

- Все строки — i18n (русский + узбекский латиница как минимум)
- Язык: `Accept-Language` или Telegram user language
- Цены RUB: `1 250 ₽` или `1 250 руб` (с копейками при необходимости: `1 250,50 ₽`)
- Доставка: календарные дни (не "рабочие" — избежать путаницы между календарями 3 стран)

---

## Часть VI. Доменные события — Что корзина сообщает миру

---

### 24. Каталог событий

Все наследуют `CartEvent(DomainEvent)`, `aggregate_type = "Cart"`. Публикуются через Transactional Outbox + TaskIQ relay.

| Событие                        | Тип             | Триггер                      | Потребители                       |
| ------------------------------ | --------------- | ---------------------------- | --------------------------------- |
| `CartCreatedEvent`             | Domain          | Создание                     | Analytics                         |
| `CartItemAddedEvent`           | Domain          | Добавление позиции           | Analytics, Recommendations        |
| `CartItemRemovedEvent`         | Domain          | Удаление позиции             | Analytics                         |
| `CartItemQuantityChangedEvent` | Domain          | Изменение количества         | Analytics                         |
| `CartPriceRevalidatedEvent`    | Domain          | Цены обновлены               | Analytics (price audit trail)     |
| `CartCheckedOutEvent`          | **Integration** | FROZEN → ORDERED             | **Order BC**, Analytics           |
| `CartCheckoutCancelledEvent`   | Domain          | FROZEN → ACTIVE              | Analytics                         |
| `CartAbandonedEvent`           | Domain          | Неактивность >1ч (max 1/24ч) | Notification BC (TG bot recovery) |
| `CartMergedEvent`              | Domain          | Guest + Auth merge           | Analytics                         |
| `CartExpiredEvent`             | Domain          | TTL истёк                    | Cleanup                           |

**CartAbandonedEvent:** Не создаёт нового состояния — корзина остаётся ACTIVE. Публикуется фоновой задачей. `abandonment_notified_at` предотвращает повторение в течение 24 часов.

### 25. CartCheckedOutEvent — ключевое интеграционное событие

```
CartCheckedOutEvent:
  schema_version: int = 1                  # для эволюции схемы (additive = no bump, breaking = bump)
  cart_id: UUID
  customer_id: UUID
  pickup_point_id: UUID                    # pass-through
  payment_reference_id: UUID               # для reconciliation с Payment BC
  items:
    - item_id: UUID
      sku_id: UUID
      product_id: UUID
      variant_id: UUID
      brand_id: UUID                       # аналитика, отчёты по брендам
      category_id: UUID                    # аналитика, отчёты по категориям
      supplier_id: UUID
      supplier_type: "cross_border" | "local"
      supplier_name: str
      source_url: str | null               # для оператора → закупка на маркетплейсе
      fulfillment_type: "deferred_procurement" | "direct_order"
      quantity: int
      unit_price: Money                    # {amount: int, currency: str}
      original_unit_price: Money           # цена при добавлении (для аудита)
      compare_at_price: Money | null
      item_total: Money                    # unit_price × quantity (invariant, проверяется assertion)
      product_name_i18n: dict[str, str]    # полный i18n dict (не одна локаль)
      variant_name_i18n: dict[str, str]    # полный i18n dict
      sku_code: str
      image_url: str | null                # для order confirmation, email receipts
      country_of_origin: str | null
      return_policy: "standard" | "limited"
      delivery_estimate_min_days: int      # 2 (local) / 10 (cross_border)
      delivery_estimate_max_days: int      # 7 (local) / 25 (cross_border)
  grand_total: Money
  vat_amount: Money
  currency: str
  revalidated_at: datetime                 # когда прошла strict ревалидация (= frozen_at)
  checked_out_at: datetime
```

**Контракт:** `item_total.amount == unit_price.amount × quantity` — assertion в checkout handler. Order BC может перепроверить.

**Сериализация Money:** `{amount: int, currency: str}`. Требует расширения `UoW._serialize_value()` для обработки `@attrs.frozen` объектов (текущий `dataclasses.asdict()` не поддерживает attrs — см. Prerequisites).

**Паттерн:** Event-Carried State Transfer — Order BC создаёт заказ **без обратного вызова** к Cart. Payload ~30-35KB при 50 позициях с i18n (допустимо для RabbitMQ/Outbox).

---

## Часть VII. API-контракт

---

### 26. Endpoints

**Write-side (Commands):**

| Метод  | Путь                                  | Действие                                                |
| ------ | ------------------------------------- | ------------------------------------------------------- |
| POST   | `/api/v1/carts`                       | Создать корзину (или вернуть существующую: 200, не 201) |
| POST   | `/api/v1/carts/{id}/items`            | Добавить позицию                                        |
| PATCH  | `/api/v1/carts/{id}/items/{item_id}`  | Обновить количество (0 = удалить)                       |
| DELETE | `/api/v1/carts/{id}/items/{item_id}`  | Удалить позицию                                         |
| DELETE | `/api/v1/carts/{id}/items`            | Очистить корзину                                        |
| POST   | `/api/v1/carts/{id}/checkout`         | Initiate checkout (ACTIVE → FROZEN)                     |
| POST   | `/api/v1/carts/{id}/checkout/confirm` | Confirm order (FROZEN → ORDERED)                        |
| POST   | `/api/v1/carts/{id}/checkout/cancel`  | Cancel checkout (FROZEN → ACTIVE)                       |
| POST   | `/api/v1/carts/merge`                 | Слияние guest + auth корзин                             |

**Read-side (Queries):**

| Метод | Путь                            | Действие                                                 |
| ----- | ------------------------------- | -------------------------------------------------------- |
| GET   | `/api/v1/carts/current`         | Активная корзина текущего пользователя                   |
| GET   | `/api/v1/carts/{id}`            | Корзина по ID (с lazy price check, read-only)            |
| GET   | `/api/v1/carts/current/summary` | Lightweight бейдж: item_count + grand_total (для header) |

### 27. Read Models

**`CartReadModel`** — полная корзина:

| Поле                   | Тип                 | Описание                                                             |
| ---------------------- | ------------------- | -------------------------------------------------------------------- |
| `id`                   | UUID                |                                                                      |
| `status`               | CartStatus          | ACTIVE / FROZEN / ORDERED / MERGED / EXPIRED                         |
| `version`              | int                 | Для If-Match                                                         |
| `currency`             | str                 | "RUB"                                                                |
| `items`                | CartItemReadModel[] | Сгруппированы по `snapshot.supplier_type` → `snapshot.supplier_name` |
| `item_count`           | int                 | Общее количество единиц                                              |
| `unique_item_count`    | int                 | Уникальных SKU                                                       |
| `subtotal`             | Money               | Сумма всех item_subtotal                                             |
| `discount_total`       | Money               | MVP: 0                                                               |
| `delivery_estimate`    | Money               | MVP: 0                                                               |
| `vat_amount`           | Money               | Информационно (taxable × 12/112)                                     |
| `grand_total`          | Money               | Итого к оплате                                                       |
| `frozen_at`            | datetime \| null    |                                                                      |
| `frozen_until`         | datetime \| null    | Для countdown на frontend                                            |
| `payment_reference_id` | UUID \| null        | Для передачи Payme/Click SDK                                         |
| `created_at`           | datetime            |                                                                      |
| `updated_at`           | datetime            |                                                                      |

**`CartItemReadModel`** — позиция с обогащением:

| Поле                    | Тип                 | Описание                                                          |
| ----------------------- | ------------------- | ----------------------------------------------------------------- |
| `item_id`               | UUID                |                                                                   |
| `sku_id`                | UUID                |                                                                   |
| `quantity`              | int                 |                                                                   |
| `unit_price`            | Money               | Текущий snapshot                                                  |
| `original_unit_price`   | Money               | Цена при добавлении                                               |
| `compare_at_price`      | Money \| null       | Зачёркнутая цена                                                  |
| `item_subtotal`         | Money               | unit_price × quantity (computed)                                  |
| `snapshot`              | CatalogItemSnapshot | Все поля из §11                                                   |
| `is_available`          | bool                | Live check из каталога                                            |
| `unavailability_reason` | str \| null         | `sku_inactive` / `product_unpublished` / `supplier_inactive`      |
| `is_stale`              | bool                | `price_snapshot_at` > 24h ago                                     |
| `current_catalog_price` | Money \| null       | Только когда `is_stale = true` (live из каталога, не персистится) |
| `price_changed`         | bool                | `current_catalog_price ≠ unit_price`                              |

**`CartSummaryReadModel`** — бейдж (отдельный endpoint `GET /carts/current/summary`):

| Поле              | Тип        | Описание                    |
| ----------------- | ---------- | --------------------------- |
| `item_count`      | int        |                             |
| `grand_total`     | Money      |                             |
| `status`          | CartStatus |                             |
| `has_unavailable` | bool       | Есть ли недоступные позиции |

### 28. Headers и конкурентный контроль

| Header                       | Когда              | Поведение                                      |
| ---------------------------- | ------------------ | ---------------------------------------------- |
| `If-Match: {version}`        | Мутирующие запросы | 409 при несовпадении версии (retry на клиенте) |
| `X-Idempotency-Key: {uuid4}` | POST-запросы       | Redis TTL 24h; дубликат → кэшированный ответ   |

---

## Часть VIII. Бизнес-правила — Сводная таблица

---

### 29. Все правила

**Валидация при добавлении:**

| #    | Правило                                                                         |
| ---- | ------------------------------------------------------------------------------- |
| R-01 | Одна активная корзина на пользователя                                           |
| R-02 | Максимум 50 уникальных SKU                                                      |
| R-03 | Максимум 99 единиц одного SKU                                                   |
| R-04 | SKU: is_active=true, Product: PUBLISHED, Supplier: active, supplier_id not null |
| R-05 | Дублирующий SKU → merge количества                                              |
| R-19 | Все SKU — одна валюта (корзина = валюта первого SKU)                            |
| R-21 | Product.supplier_id обязателен (not null)                                       |
| R-22 | effective_price (SKU.price ?? Variant.default_price) обязательна                |

**Ценообразование:**

| #    | Правило                                                                 |
| ---- | ----------------------------------------------------------------------- |
| R-06 | Цена фиксируется при добавлении (snapshot + timestamp)                  |
| R-07 | При checkout — strict ревалидация всех цен                              |
| R-08 | Рост цены >5% от **original_unit_price** → подтверждение покупателя     |
| R-09 | Снижение цены → автоматическое обновление                               |
| R-20 | НДС 12% включён (tax-inclusive, B2C)                                    |
| R-23 | grand_total > 0 для перехода в FROZEN                                   |
| R-25 | Snapshot старше 24ч → lazy **check** при GET (read-only, не пишет в БД) |

**State Machine:**

| #    | Правило                                                                    |
| ---- | -------------------------------------------------------------------------- |
| R-14 | FROZEN корзина не модифицируема                                            |
| R-15 | MERGED и ORDERED — терминальные                                            |
| R-24 | TTL сбрасывается только мутациями, не чтением                              |
| R-26 | FROZEN → ACTIVE timeout безусловный через 30 мин (Payment BC компенсирует) |
| R-27 | Checkout → pessimistic lock (SELECT FOR UPDATE)                            |

**Жизненный цикл:**

| #    | Правило                              |
| ---- | ------------------------------------ |
| R-10 | Checkout только для авторизованных   |
| R-11 | Гостевая корзина TTL = 24 часа       |
| R-12 | Авторизованная корзина TTL = 30 дней |
| R-13 | Frozen TTL = 30 минут (безусловный)  |

**Merge и события:**

| #    | Правило                                                                  |
| ---- | ------------------------------------------------------------------------ |
| R-16 | Merge: дубликат SKU → большее количество; user items приоритет над guest |
| R-17 | pickup_point_id обязателен при /checkout/confirm                         |
| R-18 | Недоступные SKU блокируют checkout                                       |
| R-28 | CartAbandonedEvent: max 1 раз в 24ч на корзину                           |
| R-29 | Дисклеймер о procurement risk обязателен                                 |
| R-30 | 5% порог цены сравнивается с original_unit_price (не с текущим snapshot) |
| R-31 | Merge отложен если user cart в статусе FROZEN                            |
| R-32 | Confirm и Cancel используют pessimistic lock (mutual exclusion)          |

---

## Часть IX. Архитектура — Как это построено

---

### 30. Domain Model (DDD)

| Класс                 | Тип                      | Паттерн                                 |
| --------------------- | ------------------------ | --------------------------------------- |
| `Cart`                | Aggregate Root           | `@attrs.define` + `AggregateRoot` mixin |
| `CartItem`            | Entity (внутри агрегата) | `@attrs.define`                         |
| `CatalogItemSnapshot` | Value Object (ACL)       | `@attrs.frozen`                         |
| `CartStatus`          | Enum                     | `StrEnum` (как ProductStatus)           |

### 31. Module Structure

```
src/modules/cart/
├── domain/
│   ├── entities.py          # Cart, CartItem
│   ├── value_objects.py     # CartStatus, CatalogItemSnapshot
│   ├── events.py            # CartEvent base + конкретные
│   ├── exceptions.py        # 15 typed exceptions
│   ├── interfaces.py        # ICartRepository, ICatalogQueryService
│   └── constants.py         # MAX_CART_ITEMS=50, MAX_ITEM_QUANTITY=99, STALE_PRICE_HOURS=24
├── application/
│   ├── commands/             # add_item, remove_item, update_quantity,
│   │                         # initiate_checkout, confirm_checkout, cancel_checkout,
│   │                         # clear_cart, merge_carts
│   └── queries/              # get_cart, get_active_cart + read_models.py
├── infrastructure/
│   ├── models.py             # CartModel, CartItemModel (ORM)
│   ├── repositories/cart.py  # SqlAlchemyCartRepository
│   ├── catalog_query_adapter.py  # ICatalogQueryService → JOIN catalog ORM
│   └── provider.py          # Dishka providers
└── presentation/
    ├── router_carts.py       # FastAPI router
    ├── schemas.py            # Pydantic (CamelModel)
    └── dependencies.py       # Dishka module providers
```

### 32. Anti-Corruption Layer

| Порт (domain)                      | Адаптер (infrastructure)        | Что делает                                                                                                               |
| ---------------------------------- | ------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `ICatalogQueryService`             | `SqlAlchemyCatalogQueryAdapter` | `get_sku_snapshot(sku_id)` для add-item; `get_sku_snapshots_batch(sku_ids)` для checkout ревалидации (single `IN` query) |
| `ISupplierQueryService` (existing) | existing implementation         | `get_supplier_info(supplier_id)` → SupplierInfo                                                                          |

При выделении Cart в отдельный сервис → адаптеры заменяются на HTTP-клиенты.

### 33. Context Mapping

| Cart →            | Тип связи               | Механизм                                   |
| ----------------- | ----------------------- | ------------------------------------------ |
| Catalog           | Customer/Supplier + ACL | `ICatalogQueryService` (порт Cart)         |
| Supplier          | Customer/Supplier       | Existing `ISupplierQueryService`           |
| Identity          | Conformist              | `customer_id` из JWT as-is                 |
| Geo               | Нет зависимости         | `pickup_point_id` — pass-through в событие |
| Order (будущий)   | Published Language      | `CartCheckedOutEvent` через Outbox         |
| Payment (будущий) | Published Language      | `payment_reference_id` в событии           |

### 34. Consistency Model

| Операция                  | Стратегия                         | Почему                                 |
| ------------------------- | --------------------------------- | -------------------------------------- |
| add / remove / update     | Optimistic locking (`version`)    | Конфликты редки (1 user ≈ 1 session)   |
| initiate checkout         | Pessimistic (`SELECT FOR UPDATE`) | Race condition при concurrent checkout |
| confirm / cancel checkout | Pessimistic (`SELECT FOR UPDATE`) | Mutual exclusion confirm vs cancel     |
| Cart → Order              | Eventual consistency (Outbox)     | Разные BC                              |
| Order creation failure    | Компенсация: FROZEN → ACTIVE      | Будет в Order BRD                      |

### 35. Exception Catalog

| Exception                      | HTTP | Code                         |
| ------------------------------ | ---- | ---------------------------- |
| `CartNotFoundError`            | 404  | `CART_NOT_FOUND`             |
| `CartItemNotFoundError`        | 404  | `CART_ITEM_NOT_FOUND`        |
| `EmptyCartCheckoutError`       | 400  | `EMPTY_CART_CHECKOUT`        |
| `MaxCartItemsExceededError`    | 400  | `MAX_CART_ITEMS_EXCEEDED`    |
| `MaxItemQuantityExceededError` | 400  | `MAX_ITEM_QUANTITY_EXCEEDED` |
| `InvalidCartStateError`        | 422  | `INVALID_CART_STATE`         |
| `InvalidCartTransitionError`   | 422  | `INVALID_CART_TRANSITION`    |
| `CartVersionConflictError`     | 409  | `CART_VERSION_CONFLICT`      |
| `SKUUnavailableError`          | 422  | `SKU_UNAVAILABLE`            |
| `SupplierInactiveForCartError` | 422  | `SUPPLIER_INACTIVE`          |
| `PriceChangedError`            | 422  | `PRICE_CHANGED`              |
| `CurrencyMismatchError`        | 422  | `CURRENCY_MISMATCH`          |
| `NoSupplierAssignedError`      | 422  | `NO_SUPPLIER_ASSIGNED`       |
| `NoPriceAvailableError`        | 422  | `NO_PRICE_AVAILABLE`         |
| `ZeroTotalCheckoutError`       | 400  | `ZERO_TOTAL_CHECKOUT`        |

---

## Часть X. Качество — Как мы измеряем успех

---

### 36. Производительность (SLO)

| Метрика                 | Target    | Почему                                 |
| ----------------------- | --------- | -------------------------------------- |
| GET корзины (p99)       | < 200 мс  | Включая lazy refresh stale snapshots   |
| Добавление товара (p99) | < 300 мс  | Write-through                          |
| Initiate checkout (p99) | < 1500 мс | Strict ревалидация + SELECT FOR UPDATE |

### 37. Надёжность

| Гарантия                | Как                                                              |
| ----------------------- | ---------------------------------------------------------------- |
| Потеря данных = 0       | PostgreSQL — source of truth                                     |
| Двойное списание        | Idempotency key (Redis 24h) + payment_reference_id               |
| Конкурентные обновления | Optimistic locking → 409 → client retry                          |
| Checkout race condition | Pessimistic locking                                              |
| События не теряются     | Transactional Outbox                                             |
| FROZEN ↔ payment race   | Безусловный 30-мин timeout; Payment BC компенсирует при коллизии |

### 38. Масштабируемость (MVP)

| Параметр          | Target |
| ----------------- | ------ |
| Активных корзин   | 10 000 |
| Позиций в корзине | 50     |
| RPS               | 500    |

### 39. Безопасность

1. Корзину модифицирует только владелец (`customer_id` из JWT / `anonymous_id` из cookie)
2. `anonymous_id` — 256-bit crypto token, secure httpOnly cookie
3. Checkout — обязательная авторизация
4. Rate limiting: 30 мутаций/мин, 100 чтений/мин

### 40. KPIs

| Метрика                                       | Target   |
| --------------------------------------------- | -------- |
| Cart-to-Order Conversion                      | > 15%    |
| Cart Abandonment Rate                         | < 75%    |
| Checkout Completion Rate (initiate → confirm) | > 60%    |
| Average Order Value                           | tracking |
| Average Items per Cart                        | > 1.5    |
| Cart-to-Checkout Rate                         | > 25%    |
| Price Validation Error Rate                   | < 10%    |
| Cart Load Time (p95)                          | < 200 мс |
| Cross-border Item Share                       | tracking |
| Median Time to Checkout                       | < 15 мин |

---

## Часть XI. Реализация — Как мы строим

---

### 41. Фазы

**Prerequisites (BLOCKERS — до начала Phase 1):**

| #     | Задача                                                                          | Модуль         | Почему блокер                                                  |
| ----- | ------------------------------------------------------------------------------- | -------------- | -------------------------------------------------------------- |
| PRE-1 | Расширить `Money` VO: `__add__`, `__sub__`, `__mul__(int)`, `sum()` classmethod | Shared/Catalog | Cart не может считать subtotal/grand_total                     |
| PRE-2 | Расширить `UoW._serialize_value()` для `@attrs.frozen` объектов                 | Infrastructure | `CartCheckedOutEvent` с Money падает на `dataclasses.asdict()` |


**Phase 1: MVP (P0)**
- Cart domain (entities, VOs, FSM, events) + PostgreSQL
- CRUD API + 2-step checkout
- Price snapshot + lazy (24h) + strict ревалидация
- Optimistic + pessimistic locking
- CatalogItemSnapshot (ACL) с полным набором полей
- CartCheckedOutEvent (integration, full payload) через Outbox
- CartAbandonedEvent (analytics baseline)
- Валидации: R-01..R-32
- i18n-ready
- **Admin read-only view:** `GET /admin/carts?customer_id={id}` — просмотр корзины покупателя, состояния, ценовой истории (launch blocker для поддержки)
- Confirm response возвращает `order_reference_id` для перехода к tracking (контракт с Order BC)

**Phase 2: Guest + UX + Reseller (P1)**
- Гостевая корзина + Silent Merge
- Redis кэш (write-through)
- Express Checkout / Buy Now (предзаполнение ПВЗ + payment, single-item express)
- Batch add: `POST /carts/{id}/items/batch` с массивом `[{sku_id, quantity}]` (до 50 items за запрос)
- Reorder: `POST /carts/from-order/{order_id}` — клонирование корзины из предыдущего заказа
- Configurable cart limits: `MAX_CART_ITEMS` повышается до 100 для verified-аккаунтов (reseller tier)
- TG bot recovery (consumer CartAbandonedEvent)
- "Удалить все недоступные" one-tap
- Admin actions: force-unfreeze, extend-frozen-timeout

**Phase 3: Promotions (P2)**
- Промокоды / купоны (discount pipeline)
- "Сохранить на потом" (wishlist)
- Таможенная пошлина estimate (ЕАЭС)
- Free shipping threshold
- Admin view: корзина в контексте заказа

**Phase 4: Scale (P3)**
- Мультивалютность
- SSE real-time
- Cross-sell / upsell
- A/B тестирование
- Collaborative Cart

### 42. Scope

**В scope (Cart BC):** CRUD позиций, FSM, ценообразование (snapshot + ревалидация), группировка по источнику, checkout initiation/confirmation, события, дисклеймеры.

**Вне scope:**

| Что                            | Где                         |
| ------------------------------ | --------------------------- |
| Заказы, sub-orders             | Order BC                    |
| Платежи (Payme/Click)          | Payment BC                  |
| Закупка на маркетплейсах       | Procurement BC              |
| ПВЗ, валидация pickup_point_id | Geo BC                      |
| Уведомления (TG bot, email)    | Notification BC             |
| Каталог товаров                | Catalog BC                  |
| Логистика, трекинг             | Logistics BC                |
| Возвраты, рефанды              | Order/Refund BC             |
| Резервирование инвентаря       | Не применимо (dropshipping) |

---

## Часть XII. Риски

---

### 43. Риски и митигации

| #   | Риск                                                 | P × I | Митигация                                                              |
| --- | ---------------------------------------------------- | ----- | ---------------------------------------------------------------------- |
| 1   | Товар недоступен при закупке на маркетплейсе         | H × H | Дисклеймер; auto-refund (3 дня); fulfillment_type в событии            |
| 2   | Изменение цены между add и checkout                  | M × M | Lazy (24h) + strict ревалидация; 5% threshold                          |
| 3   | Return policy для cross-border → жалобы              | H × H | Обязательный дисклеймер; return_policy per item                        |
| 5   | Покупатель не понимает "Из Китая"/"Быстрая доставка" | M × M | Подробные группировки; бейджи; value proposition                       |
| 6   | Таможенные пошлины — сюрприз                         | M × M | Дисклеймер MVP; estimate Phase 3                                       |
| 7   | Race condition: FROZEN timeout vs payment            | L × M | Безусловный timeout 30 мин; Payment BC компенсирует если оплата прошла |
| 8   | Поставщик деактивирован с товарами в корзинах        | L × M | Lazy + strict supplier check                                           |
| 9   | Потеря гостевой корзины (cookies)                    | M × L | TG users без cookies; мотивация авторизации                            |
| 10  | Конкурентные обновления                              | L × L | Optimistic locking + 409 + retry                                       |

---

## Appendices

---

### A. Глоссарий

| Термин                   | Определение                                                       |
| ------------------------ | ----------------------------------------------------------------- |
| **Cart**                 | Агрегат с позициями, выбранными покупателем                       |
| **CartItem**             | Entity: SKU + quantity + price snapshot + catalog snapshot        |
| **CatalogItemSnapshot**  | Frozen VO — ACL-перевод данных из Catalog/Supplier BC             |
| **Checkout**             | 2-step: initiate (freeze+validate) → confirm (pay+order)          |
| **Price Snapshot**       | Зафиксированная цена при добавлении; обновляется при ревалидации  |
| **Silent Merge**         | Автоматическое объединение guest + auth корзин                    |
| **Cross-border**         | Товар с китайского маркетплейса (Poizon, Taobao, Pinduoduo, 1688) |
| **Local**                | Товар от локального/российского поставщика                        |
| **ACL**                  | Anti-Corruption Layer — защитный слой между BC                    |
| **payment_reference_id** | UUID Cart при initiate → передаётся Payment BC                    |
| **fulfillment_type**     | `deferred_procurement` (cross_border) / `direct_order` (local)    |
| **ПВЗ**                  | Пункт выдачи заказов                                              |

### B. Ссылки на исследования

1. [Enterprise Platforms](../research/cart-architecture/01-enterprise-platforms-cart-architecture.md) — Amazon, Alibaba, Shopify, Walmart, eBay, JD.com
2. [Cross-border Patterns](../research/cart-architecture/02-crossborder-marketplace-cart-patterns.md) — Farfetch, Poizon, Zalando, ASOS, Coupang
3. [DDD Architecture](../research/cart-architecture/03-ddd-architecture-patterns.md) — Aggregates, Events, CQRS, Saga, Outbox
4. [Pricing & Payments](../research/cart-architecture/04-pricing-payments-architecture.md) — Money, Multi-currency, Promotions
5. [State & UX](../research/cart-architecture/05-state-management-ux-patterns.md) — FSM, API Design, Cart Merge

### C. Audit History

**Round 1 → v2.0 (2026-03-28):** 5-auditor parallel review — 114 findings (13 CRITICAL, 35 HIGH, 43 MEDIUM, 21 LOW)

Аудиторы: Business Logic (24), Cross-border (20), DDD Architecture (27), UX & Checkout (27), Financial & Pricing (16)

**Round 2 → v3.0 (2026-03-28):** 5-auditor parallel review — 96 findings (12 CRITICAL, 33 HIGH, 32 MEDIUM, 19 LOW)

Аудиторы: Consistency & Completeness (19), Implementation Feasibility (20), Adversarial Edge Cases (20), Data Contracts & Integration (20), Business & Operational Risk (17)

**Ключевые фиксы v2.1 → v3.0:**
- FROZEN timeout: убран мёртвый guard `payment_reference_id IS NULL` → безусловный 30-мин timeout (CON-16, IMP-23, ADV-08)
- Lazy refresh: GET стал read-only (CQRS compliance), возвращает `is_stale` + `current_catalog_price` без записи в БД (CON-13, IMP-01, ADV-19)
- Price drift: добавлен `original_unit_price` — 5% порог считается от цены при добавлении, не от текущего snapshot (ADV-02)
- Event schema: добавлены `brand_id`, `category_id`, `image_url`, `delivery_estimate_days`, `schema_version`, i18n dicts вместо single-locale strings (DC-01, DC-04, DC-15, DC-16, DC-19)
- Merge: приоритет user items над guest items; guard на FROZEN user cart; currency validation (ADV-05, ADV-13, ADV-06)
- Confirm/Cancel: добавлен pessimistic lock для mutual exclusion (ADV-04)
- Cart creation: добавлена секция 11a с get-or-create семантикой (CON-08)
- Prerequisites: 4 blocker-задачи определены до Phase 1 (IMP-02, IMP-03, DC-13, DC-17)
- Add item: добавлена проверка status=ACTIVE как step 0 (ADV-07)

**Round 3 → v3.1 (2026-03-28):** 5 customer-perspective auditors — 98 findings (14 CRITICAL, 31 HIGH, 32 MEDIUM, 21 LOW)


**Ключевые фиксы v3.0 → v3.1:**
- Trust signals: добавлены гарантия возврата, статистика, бейдж аутентификации Poizon (CUB-01, CFB-01, CFB-02)
- "Из наличия" → "Быстрая доставка" — понятный consumer-friendly термин (CUB-15)
- Marketplace differentiation: sub-группы внутри "Из Китая" (Poizon с аутентификацией vs Taobao/1688) (CFB-02, CFB-11)
- Дисклеймеры переписаны дружественным тоном + определение "брак" с примерами (CUB-02, CUB-13)
- Refund timeline: "3 рабочих дня" → "инициируем за 3 дня, зачисление до 14 дней" (CUB-07, CSO-04)
- Price changes: ВСЕ изменения видимы покупателю, 5% только для блокировки (CUB-03)
- Admin read-only view → Phase 1 (launch blocker для поддержки) (CSO-07)
- CartReadModel полная JSON-схема с типами (CFE-06)
- Summary endpoint для header badge (CFE-19)
- Dispute resolution контракт (CSO-03, CFB-03)
- Checkout confirm → automatic после payment callback (CUB-11)
- Confirm response возвращает order_reference_id для перехода к tracking (CFB-04)
- Phase 2: batch add, reorder, configurable limits для resellers (CPU-01, CPU-03)
- Phase 2: Buy Now / single-item express (CFB-07)

**Всего за 3 раунда: 308 findings, 39 CRITICAL → все закрыты.**

---

*Документ прошёл 3 раунда × 5 аудиторов (15 аудитов, 308 findings) и готов к утверждению.*
