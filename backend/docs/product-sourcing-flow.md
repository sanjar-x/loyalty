# Product Sourcing Flow

Бизнес-требования к созданию товара с учётом источника поставки.

---

## Бизнес-модель

Платформа — агрегатор без собственного склада. Товары поступают из двух источников:

```
┌──────────────────────────────────────────────────────────────────┐
│                        Платформа                                 │
│                                                                  │
│   ┌──────────────────────┐     ┌─────────────────────────────┐   │
│   │    ИЗ КИТАЯ          │     │    ИЗ НАЛИЧИЯ               │   │
│   │    (Cross-border)    │     │    (Local)                  │   │
│   │                      │     │                             │   │
│   │  Poizon              │     │  Локальные поставщики       │   │
│   │  Taobao              │     │  Региональные поставщики    │   │
│   │  Pinduoduo           │     │  Поставщики из России       │   │
│   │  1688                │     │                             │   │
│   │                      │     │                             │   │
│   │  Оригинал / Реплика  │     │  Быстрая доставка           │   │
│   │  Долгая доставка     │     │  Прямая передача в ПВЗ      │   │
│   │  Выкуп → Логистика   │     │                             │   │
│   └──────────────────────┘     └─────────────────────────────┘   │
│                                                                  │
│                    ┌──────────────┐                              │
│                    │     ПВЗ      │ ← клиент забирает            │
│                    └──────────────┘                              │
└──────────────────────────────────────────────────────────────────┘
```

---

## Ключевое решение: маркетплейсы = поставщики

Вместо полиморфных nullable полей (`marketplace` null при одном типе, `supplier_id` null при другом) — **унифицированная модель**: Poizon, Taobao, 1688 — это поставщики с `type=CROSS_BORDER`.

```
products
├── supplier_id    NOT NULL  ← всегда
├── source_url     nullable  ← для cross_border
└── ...без лишних полей

suppliers
├── type=CROSS_BORDER → Poizon, Taobao, 1688...
└── type=LOCAL        → Местные поставщики
```

---

## Что уже есть в коде

| Компонент                   | Состояние                          | Где                                                 |
| --------------------------- | ---------------------------------- | --------------------------------------------------- |
| `SupplierType` enum         | `CROSS_BORDER`, `LOCAL`            | `catalog/infrastructure/models.py`                  |
| `Supplier` ORM              | `id`, `name`, `type`, `region`     | `catalog/infrastructure/models.py`                  |
| `Product.supplier_id`       | FK → suppliers, **NOT NULL в ORM** | ORM: NOT NULL, Domain/Schema: nullable (рассинхрон) |
| `Product.source_url`        | VARCHAR(1024), nullable            | Только ORM (нет в Domain, Schema, API)              |
| `Product.country_of_origin` | ISO 3166-1 alpha-2                 | Domain + ORM                                        |

---

## Что нужно изменить

### 1. Расширение Supplier модели

```
suppliers
├── id              UUID PK (v7)
├── name            VARCHAR(255)        "Poizon" | "Ташкентский оптовик"
├── type            supplier_type_enum  CROSS_BORDER | LOCAL
├── region          VARCHAR(255)        nullable
├── is_active       BOOLEAN             default true
├── created_at      TIMESTAMPTZ
└── updated_at      TIMESTAMPTZ
```

Маркетплейсы — pre-seeded поставщики (создаются миграцией):

| id          | name      | type           | region |
| ----------- | --------- | -------------- | ------ |
| `c0...0001` | Poizon    | `cross_border` | China  |
| `c0...0002` | Taobao    | `cross_border` | China  |
| `c0...0003` | Pinduoduo | `cross_border` | China  |
| `c0...0004` | 1688      | `cross_border` | China  |

### 2. Синхронизация Product модели

`supplier_id` уже NOT NULL в ORM, но nullable в Domain entity и Schema — нужно исправить рассинхрон:

```
Product domain entity (entities.py):
  supplier_id: uuid.UUID | None = None   →   supplier_id: uuid.UUID  (обязателен)

ProductCreateRequest (schemas.py):
  supplier_id: uuid.UUID | None = None   →   supplier_id: uuid.UUID  (обязателен)

CreateProductCommand (create_product.py):
  supplier_id: uuid.UUID | None = None   →   supplier_id: uuid.UUID  (обязателен)
```

### 3. Добавить `source_url` во все слои

Поле `source_url` существует только в ORM. Нужно добавить в:

- `Product` domain entity — `source_url: str | None = None`
- `CreateProductCommand` — `source_url: str | None = None`
- `ProductCreateRequest` schema — `source_url: str | None = None`
- `ProductUpdateRequest` schema — `source_url: str | None | object = _SENTINEL`
- `ProductResponse` schema — `source_url: str | None = None`

**Правило валидации** (в `CreateProductHandler`, не DB constraint):

| `supplier.type` | `source_url`   | Когда                          |
| --------------- | -------------- | ------------------------------ |
| `CROSS_BORDER`  | **обязателен** | Ссылка на товар в маркетплейсе |
| `LOCAL`         | опционален     | Ссылка на каталог поставщика   |

---

## Flow создания товара

### Общий flow

```
                              Менеджер
                                 │
                                 │
                         Заполнить общие поля:
                         title, slug, brand,
                         category, description,
                         tags, price (SKU)
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
             ИЗ КИТАЯ                   ИЗ НАЛИЧИЯ
         Выбрать поставщика         Выбрать поставщика
          (Poizon, Taobao,           (или создать нового:
           Pinduoduo, 1688)           город + название)
                    │                         │
              Вставить ссылку                 │
              на товар                        │
                    │                         │
                    └────────────┬────────────┘
                                 │
                                 ▼
                         Product создан
                          (status=DRAFT)
                                 │
                                 ▼
                         Стандартный flow:
                         SKU → Атрибуты →
                         ENRICHING →
                         READY_FOR_REVIEW →
                         PUBLISHED
```

### Шаг 0. Управление поставщиками (предусловие)

Маркетплейсы (Poizon, Taobao...) создаются миграцией как системные поставщики.
Локальные поставщики создаются менеджером через API.

#### Создание локального поставщика

```
POST /api/v1/catalog/suppliers
Authorization: Bearer <token>
Permission: catalog:manage
```

```json
{
  "name": "Ташкентский оптовик",
  "type": "local",
  "region": "Ташкентская область"
}
```

#### Список поставщиков

```
GET /api/v1/catalog/suppliers?type=local
GET /api/v1/catalog/suppliers?type=cross_border
```

```json
{
  "items": [
    {
      "id": "...",
      "name": "Poizon",
      "type": "cross_border",
      "isActive": true
    },
    {
      "id": "...",
      "name": "Ташкентский оптовик",
      "type": "local",
      "region": "Ташкентская область",
      "isActive": true
    }
  ],
  "total": 2
}
```

---

### Шаг 1a. Создание товара — Из Китая

Менеджер выбирает маркетплейс-поставщика и вставляет ссылку на товар.

```
POST /api/v1/catalog/products
Authorization: Bearer <token>
Permission: catalog:manage
```

```json
{
  "supplierId": "<poizon-supplier-uuid>",
  "sourceUrl": "https://dw4.co/t/A-abc123456",

  "titleI18n": {
    "ru": "Nike Air Max 90 — оригинал Poizon",
    "uz": "Nike Air Max 90 — Poizon original"
  },
  "slug": "nike-air-max-90-poizon",
  "brandId": "a1000000-0000-0000-0000-000000000001",
  "primaryCategoryId": "019cdbf4-e987-75b9-aca8-8b2dd2c35314",
  "descriptionI18n": {
    "ru": "Оригинальные кроссовки Nike с проверкой подлинности Poizon"
  },
  "countryOfOrigin": "CN",
  "tags": ["nike", "air-max", "poizon", "original"]
}
```

#### Валидация

| Поле         | Правило                                                    |
| ------------ | ---------------------------------------------------------- |
| `supplierId` | Обязателен, FK exists                                      |
| `sourceUrl`  | Обязателен если `supplier.type=CROSS_BORDER`, валидный URL |

---

### Шаг 1b. Создание товара — Из наличия

Менеджер выбирает локального поставщика.

```
POST /api/v1/catalog/products
Authorization: Bearer <token>
Permission: catalog:manage
```

```json
{
  "supplierId": "<local-supplier-uuid>",

  "titleI18n": {
    "ru": "Худи оверсайз базовая",
    "uz": "Oversize bazaviy hudi"
  },
  "slug": "oversize-basic-hoodie",
  "brandId": "a1000000-0000-0000-0000-000000000002",
  "primaryCategoryId": "019cdbf2-f48b-7482-852a-3607d2955e57",
  "descriptionI18n": {
    "ru": "Базовая худи от местного поставщика, доставка 1-3 дня"
  },
  "tags": ["hoodie", "oversize", "basic"]
}
```

#### Валидация

| Поле         | Правило                                   |
| ------------ | ----------------------------------------- |
| `supplierId` | Обязателен, FK exists                     |
| `sourceUrl`  | Опционален (ссылка на каталог, если есть) |

---

### Шаги 2–4. Без изменений

После создания карточки flow идентичен для обоих типов:

```
Шаг 2. POST /products/{id}/skus            → добавить варианты с ценой
Шаг 3. POST /products/{id}/attributes      → назначить атрибуты
Шаг 4. PATCH /products/{id}/status          → FSM: DRAFT → ... → PUBLISHED
```

Подробности — см. [product-creation-flow.md](product-creation-flow.md).

---

## Таблица ошибок

| Код | Ошибка                   | Когда                                              |
| --- | ------------------------ | -------------------------------------------------- |
| 404 | SupplierNotFoundError    | `supplierId` не найден в БД                        |
| 422 | SupplierInactiveError    | Поставщик деактивирован                            |
| 422 | SourceUrlRequiredError   | `supplier.type=CROSS_BORDER` но `sourceUrl` пустой |
| 409 | ProductSlugConflictError | Slug уже занят                                     |
| 422 | ValidationError          | `titleI18n` пустой, slug невалидный и т.д.         |

---

## Схема данных (изменения)

### Таблица products

```sql
-- supplier_id уже NOT NULL в ORM — изменений в БД не требуется
-- source_url уже есть (VARCHAR 1024, nullable) — изменений в БД не требуется
-- Изменения только на уровне Domain/Schema/Command (см. выше)
```

### Изменения в таблице suppliers

```sql
ALTER TABLE suppliers
  ADD COLUMN is_active    BOOLEAN      NOT NULL DEFAULT true,
  ADD COLUMN created_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
  ADD COLUMN updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now();

CREATE INDEX ix_suppliers_type ON suppliers (type);
CREATE INDEX ix_suppliers_active ON suppliers (is_active) WHERE is_active = true;
```

### Seed маркетплейсов (в миграции)

```sql
INSERT INTO suppliers (id, name, type, region) VALUES
  ('c0000000-0000-0000-0000-000000000001', 'Poizon',    'cross_border', 'China'),
  ('c0000000-0000-0000-0000-000000000002', 'Taobao',    'cross_border', 'China'),
  ('c0000000-0000-0000-0000-000000000003', 'Pinduoduo', 'cross_border', 'China'),
  ('c0000000-0000-0000-0000-000000000004', '1688',      'cross_border', 'China');
```

---

## API поставщиков (новые эндпоинты)

| Method   | Endpoint                  | Auth             | Description           |
| -------- | ------------------------- | ---------------- | --------------------- |
| `POST`   | `/catalog/suppliers`      | `catalog:manage` | Создать поставщика    |
| `GET`    | `/catalog/suppliers`      | `catalog:manage` | Список поставщиков    |
| `GET`    | `/catalog/suppliers/{id}` | `catalog:manage` | Детали поставщика     |
| `PATCH`  | `/catalog/suppliers/{id}` | `catalog:manage` | Обновить поставщика   |
| `DELETE` | `/catalog/suppliers/{id}` | `catalog:manage` | Деактивировать (soft) |

Фильтры для списка: `?type=local|cross_border`, `?is_active=true`.

---

## Витрина (как клиент видит товар)

Клиент **не видит** внутреннюю механику поставок. Тип доставки выводится из `supplier.type`:

```json
{
  "id": "...",
  "title": "Nike Air Max 90",
  "price": { "amount": 1299000, "currency": "UZS" },

  "deliveryInfo": {
    "source": "china",
    "estimatedDays": "10–18",
    "label": "Доставка из Китая"
  }
}
```

Для товаров от локальных поставщиков:

```json
{
  "deliveryInfo": {
    "source": "local",
    "estimatedDays": "1–3",
    "label": "В наличии"
  }
}
```

**Бейджи на карточке:**

| `supplier.type` | Бейдж               | Цвет    |
| --------------- | ------------------- | ------- |
| `cross_border`  | "Доставка из Китая" | синий   |
| `local`         | "В наличии"         | зелёный |

---

## Процесс заказа (контекст)

```
Клиент оформляет заказ → Платформа определяет supplier.type

  ┌── supplier.type = CROSS_BORDER ───────────────────────┐
  │                                                       │
  │  1. Менеджер открывает source_url                     │
  │  2. Выкупает товар на маркетплейсе (вне системы)      │
  │  3. Передаёт трекинг логистической компании           │
  │  4. Логистика доставляет в ПВЗ                        │
  │  5. Клиент забирает                                   │
  │                                                       │
  │  Сроки: 10–18 дней                                    │
  └───────────────────────────────────────────────────────┘

  ┌── supplier.type = LOCAL ──────────────────────────────┐
  │                                                       │
  │  1. Менеджер связывается с поставщиком                │
  │  2. Поставщик отправляет товар в ПВЗ                  │
  │  3. Клиент забирает                                   │
  │                                                       │
  │  Сроки: 1–3 дня                                       │
  └───────────────────────────────────────────────────────┘
```

---

## Файлы для изменений

| Файл                                                     | Что менять                                                          |
| -------------------------------------------------------- | ------------------------------------------------------------------- |
| `catalog/domain/entities.py`                             | `supplier_id` → NOT NULL, + `source_url`; создать Supplier entity   |
| `catalog/infrastructure/models.py`                       | Supplier ORM: + `is_active`, `created_at`, `updated_at`             |
| `catalog/presentation/schemas.py`                        | `supplierId` обязателен, + `sourceUrl`; новые supplier schemas      |
| `catalog/application/commands/create_product.py`         | `supplier_id` обязателен; валидация `source_url` по `supplier.type` |
| `catalog/presentation/router_products.py`                | Передать `source_url` в command                                     |
| Новый: `catalog/presentation/router_suppliers.py`        | CRUD поставщиков                                                    |
| Новый: `catalog/application/commands/create_supplier.py` | Создание поставщика                                                 |
| Новый: `catalog/application/queries/list_suppliers.py`   | Список поставщиков                                                  |
| Новый: `catalog/infrastructure/repositories/supplier.py` | Supplier repository                                                 |
| `alembic/versions/...`                                   | Миграция: расширить suppliers, seed маркетплейсов                   |
