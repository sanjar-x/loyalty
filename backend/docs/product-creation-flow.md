# Product Creation Flow

Полный жизненный цикл товара — от создания карточки до публикации на витрине.

---

## Обзор

```
                    ┌─────────────────────────────────────────────┐
                    │            Жизненный цикл товара            │
                    │                                             │
  1. Создать        │   DRAFT ──► ENRICHING ──► READY_FOR_REVIEW  │
     карточку       │     ▲          │                  │         │
                    │     │          ▼                  ▼         │
  2. Добавить       │   ARCHIVED ◄── ─ ─ ─ ─ ─    PUBLISHED       │
     SKU, медиа,    │                                             │
     атрибуты       └─────────────────────────────────────────────┘

  3. Сменить статус
```

**Минимальный путь до витрины:**

```
POST /products                          → DRAFT
POST /products/{id}/skus                → добавить варианты (цена за каждый)
POST /products/{id}/media               → загрузить фото по вариантам
POST /products/{id}/attributes          → назначить product-level атрибуты
PATCH /products/{id}/status → enriching → ENRICHING
PATCH /products/{id}/status → ready     → READY_FOR_REVIEW
PATCH /products/{id}/status → published → PUBLISHED (на витрине)
```

---

## Шаг 1. Создание карточки товара

### Запрос

```
POST /api/v1/catalog/products
Authorization: Bearer <token>
Permission: catalog:manage
```

```json
{
  "titleI18n": {
    "ru": "Кроссовки Air Max 90",
    "en": "Air Max 90 Sneakers"
  },
  "slug": "air-max-90",
  "brandId": "a1000000-0000-0000-0000-000000000001",
  "primaryCategoryId": "019cdbf4-e987-75b9-aca8-8b2dd2c35314",
  "descriptionI18n": {
    "ru": "Легендарные кроссовки Nike с технологией Air",
    "en": "Iconic Nike sneakers with Air technology"
  },
  "supplierId": "<supplier-uuid>",
  "countryOfOrigin": "VN",
  "tags": ["nike", "air-max", "sneakers", "running"]
}
```

### Валидация

| Поле                | Правила                                    |
| ------------------- | ------------------------------------------ |
| `titleI18n`         | Обязательно, минимум 1 язык                |
| `slug`              | `^[a-z0-9-]+$`, 1–255 символов, уникальный |
| `brandId`           | UUID, FK → brands (RESTRICT)               |
| `primaryCategoryId` | UUID, FK → categories (RESTRICT)           |
| `descriptionI18n`   | Опционально, `{}`                          |
| `supplierId`        | UUID, FK → suppliers (RESTRICT)            |
| `countryOfOrigin`   | ISO 3166-1 alpha-2, 2 символа или null     |
| `tags`              | Массив строк, `[]`                         |

### Внутренний flow

```
Router                     Handler                      Domain                    Repository
  │                          │                            │                          │
  ├─ parse request ─────────►│                            │                          │
  │                          ├─ async with uow ──────────►│                          │
  │                          │                            │                          │
  │                          ├─ check_slug_exists() ────────────────────────────────►│
  │                          │◄─ false ──────────────────────────────────────────────│
  │                          │                            │                          │
  │                          ├─ Product.create() ────────►│                          │
  │                          │                            ├─ validate title_i18n     │
  │                          │                            ├─ generate UUID v7        │
  │                          │                            ├─ status = DRAFT          │
  │                          │                            ├─ version = 1             │
  │                          │◄─ product ─────────────────│                          │
  │                          │                            │                          │
  │                          ├─ repo.add(product) ──────────────────────────────────►│
  │                          │                            │        _to_orm()         │
  │                          │                            │      session.add()       │
  │                          │                            │                          │
  │                          ├─ uow.commit() ────────────►│                          │
  │                          │                        INSERT INTO products           │
  │                          │                            │                          │
  │◄─ 201 { id, message } ───│                            │                          │
```

### Ответ

```
HTTP/1.1 201 Created
```

```json
{
  "id": "019ce123-abcd-7000-8000-000000000001",
  "message": "Product created"
}
```

### Ошибки

| Код | Ошибка                   | Когда                                      |
| --- | ------------------------ | ------------------------------------------ |
| 401 | Unauthorized             | Нет токена или токен невалидный            |
| 403 | InsufficientPermissions  | Нет права `catalog:manage`                 |
| 409 | ProductSlugConflictError | Товар с таким slug уже существует          |
| 422 | ValidationError          | `titleI18n` пустой, slug невалидный и т.д. |

---

## Шаг 2. Добавление SKU (вариантов)

Товар без SKU не может быть опубликован. Каждый SKU — конкретная комбинация атрибутов (цвет, размер) **со своей ценой**.

### Запрос

```
POST /api/v1/catalog/products/{product_id}/skus
Authorization: Bearer <token>
Permission: catalog:manage
```

```json
{
  "skuCode": "AIR-MAX-90-BLK-42",
  "priceAmount": 1299000,
  "priceCurrency": "UZS",
  "compareAtPriceAmount": 1599000,
  "isActive": true,
  "variantAttributes": [
    {
      "attributeId": "<color-attr-id>",
      "attributeValueId": "<black-value-id>"
    },
    {
      "attributeId": "<size-attr-id>",
      "attributeValueId": "<size-42-value-id>"
    }
  ]
}
```

### Валидация

| Поле                   | Правила                                              |
| ---------------------- | ---------------------------------------------------- |
| `skuCode`              | 1–100 символов, уникальный (soft-delete aware)       |
| `priceAmount`          | `>= 0`, в минимальных единицах валюты (тийины, коп.) |
| `priceCurrency`        | ISO 4217, 3 символа (`UZS`, `RUB`, `USD`)            |
| `compareAtPriceAmount` | `>= 0` или null, должна быть > price                 |
| `isActive`             | bool, default `true`                                 |
| `variantAttributes`    | Массив пар `(attributeId, attributeValueId)`         |

### Внутренний flow

```
1. Загрузить товар с существующими SKU
2. Создать Money VO: Money(amount=1299000, currency="UZS")
3. Валидация: compareAtPrice > price (если указана)
4. Вычислить variant_hash:
     SHA-256( sorted([attr_id:val_id, ...]).join("|") )
5. Проверить уникальность hash среди не-удалённых SKU
6. Создать SKU, добавить в product.skus
7. Сохранить → Commit
```

### Variant Hash

Гарантирует что не будет двух SKU с одинаковой комбинацией атрибутов:

```
Атрибуты: [color=black, size=42]

Сортировка по attribute_id:
  "uuid-color:uuid-black|uuid-size:uuid-42"

SHA-256 → "a3f2b8..."
```

### Ответ

```json
{
  "id": "019ce456-...",
  "message": "SKU added"
}
```

### Ошибки

| Код | Ошибка                           | Когда                               |
| --- | -------------------------------- | ----------------------------------- |
| 404 | ProductNotFoundError             | Товар не найден                     |
| 409 | DuplicateVariantCombinationError | Такая комбинация атрибутов уже есть |
| 422 | ValueError                       | compareAtPrice <= price             |

---

## Шаг 3. Загрузка медиа (фото вариантов)

Каждый вариант товара (цвет) имеет **свою коллекцию фото**. Когда клиент на витрине нажимает на другой цвет — меняются фото и цена.

### Как связаны фото и варианты

```
Product "Air Max 90"
│
├── MediaAsset: photo1.jpg
│   ├── attribute_value_id = <black-value-id>  ← привязан к ЧЁРНОМУ
│   └── role = MAIN
│
├── MediaAsset: photo2.jpg
│   ├── attribute_value_id = <black-value-id>  ← привязан к ЧЁРНОМУ
│   └── role = GALLERY
│
├── MediaAsset: photo3.jpg
│   ├── attribute_value_id = <white-value-id>  ← привязан к БЕЛОМУ
│   └── role = MAIN
│
├── MediaAsset: size_guide.jpg
│   ├── attribute_value_id = NULL              ← общее для ВСЕХ вариантов
│   └── role = SIZE_GUIDE
│
├── SKU "BLK-42": color=black, size=42, price=1 299 000 сум
├── SKU "BLK-43": color=black, size=43, price=1 299 000 сум
├── SKU "WHT-42": color=white, size=42, price=1 399 000 сум
└── SKU "WHT-43": color=white, size=43, price=1 399 000 сум
```

**Связь через `attribute_value_id`:**

- MediaAsset и SKU ссылаются на один и тот же `attribute_value_id` (например `<black-value-id>`)
- Если `attribute_value_id = NULL` → фото показывается для **всех** вариантов
- Constraint: **один MAIN** на (product_id, attribute_value_id)

### Что видит клиент

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│   ┌───────────────────────┐                         │
│   │                       │                         │
│   │    [фото чёрных]      │  ← MAIN фото варианта   │
│   │                       │                         │
│   └───────────────────────┘                         │
│   [ img1 ][ img2 ][ img3 ]  ← GALLERY фото варианта │
│                                                     │
│   Цвет:  ● чёрный  ○ белый   ← нажал "белый" →      │
│                                  фото меняются      │
│                                  цена меняется      │
│                                                     │
│   Размер: [42] [43] [44]     ← меняется только цена │
│                                                     │
│   Цена: 1 299 000 сум       ← цена конкретного SKU  │
│   ̶Ц̶е̶н̶а̶:̶ ̶1̶ ̶5̶9̶9̶ ̶0̶0̶0̶           ← compareAtPrice        │
│                                                     │
│   [  Добавить в корзину  ]                          │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Логика на фронтенде:**

```
1. Клиент выбирает цвет → фильтруем MediaAssets по attribute_value_id
2. Клиент выбирает размер → находим SKU по (color + size) → получаем цену
3. Фото с attribute_value_id = NULL показываются всегда (размерная сетка и т.д.)
```

### Запрос

```
POST /api/v1/catalog/products/{product_id}/media
Authorization: Bearer <token>
Permission: catalog:manage
```

```json
{
  "attributeValueId": "<black-value-id>",
  "role": "main",
  "mediaType": "image",
  "storageObjectId": "<storage-object-uuid>",
  "sortOrder": 0
}
```

Для общего фото (все варианты):

```json
{
  "attributeValueId": null,
  "role": "size_guide",
  "mediaType": "image",
  "storageObjectId": "<storage-object-uuid>",
  "sortOrder": 0
}
```

Для внешнего видео (YouTube и т.д.):

```json
{
  "attributeValueId": "<black-value-id>",
  "role": "hero_video",
  "mediaType": "video",
  "isExternal": true,
  "externalUrl": "https://youtube.com/watch?v=...",
  "sortOrder": 0
}
```

### Валидация

| Поле               | Правила                                                                         |
| ------------------ | ------------------------------------------------------------------------------- |
| `attributeValueId` | UUID или null. Если UUID — FK exists в attribute_values                         |
| `role`             | Обязателен: `main`, `hover`, `gallery`, `hero_video`, `size_guide`, `packaging` |
| `mediaType`        | Обязателен: `image`, `video`, `model_3d`, `document`                            |
| `storageObjectId`  | UUID, soft-link → storage_objects (если не external)                            |
| `isExternal`       | bool, default false                                                             |
| `externalUrl`      | Обязателен если `isExternal=true`, валидный URL                                 |
| `sortOrder`        | int, default 0                                                                  |

### Роли медиа

| Role         | Описание                    | Сколько на вариант |
| ------------ | --------------------------- | ------------------ |
| `main`       | Главное фото                | ровно 1            |
| `hover`      | Фото при наведении          | 0–1                |
| `gallery`    | Галерея дополнительных фото | 0–N                |
| `hero_video` | Видео (YouTube, файл)       | 0–1                |
| `size_guide` | Размерная сетка             | 0–1 (обычно общее) |
| `packaging`  | Фото упаковки               | 0–N                |

### Constraint

Один MAIN на (product, variant):

```sql
UNIQUE (product_id, attribute_value_id)
WHERE role = 'MAIN'
```

### Ошибки

| Код | Ошибка                      | Когда                                    |
| --- | --------------------------- | ---------------------------------------- |
| 404 | ProductNotFoundError        | Товар не найден                          |
| 404 | AttributeValueNotFoundError | attribute_value_id не найден             |
| 409 | DuplicateMainMediaError     | MAIN фото уже есть для этого варианта    |
| 422 | ExternalUrlRequiredError    | isExternal=true но externalUrl не указан |

---

## Шаг 4. Назначение атрибутов товару

Product-level атрибуты (не вариантные) — например, материал, страна, коллекция.

### Запрос

```
POST /api/v1/catalog/products/{product_id}/attributes
Authorization: Bearer <token>
Permission: catalog:manage
```

```json
{
  "attributeId": "...",
  "attributeValueId": "..."
}
```

### Внутренний flow

```
1. Проверить что товар существует
2. Проверить что атрибут ещё не назначен этому товару
3. Создать ProductAttributeValue
4. Сохранить → Commit
```

### Constraint

Один атрибут = одно значение на товар:

```sql
UNIQUE (product_id, attribute_id)
```

### Ошибки

| Код | Ошибка                         | Когда                             |
| --- | ------------------------------ | --------------------------------- |
| 404 | ProductNotFoundError           | Товар не найден                   |
| 409 | DuplicateProductAttributeError | Атрибут уже назначен этому товару |

---

## Шаг 5. Смена статуса (FSM)

### Запрос

```
PATCH /api/v1/catalog/products/{product_id}/status
Authorization: Bearer <token>
Permission: catalog:manage
```

```json
{
  "status": "enriching"
}
```

### Таблица переходов

```
Текущий            → Допустимые
─────────────────────────────────────────
DRAFT              → ENRICHING
ENRICHING          → DRAFT, READY_FOR_REVIEW
READY_FOR_REVIEW   → ENRICHING, PUBLISHED
PUBLISHED          → ARCHIVED
ARCHIVED           → DRAFT
```

### Диаграмма

```
  ┌───────┐         ┌───────────┐        ┌──────────────────┐        ┌───────────┐
  │ DRAFT │────────►│ ENRICHING │───────►│ READY_FOR_REVIEW │───────►│ PUBLISHED │
  └───────┘         └───────────┘        └──────────────────┘        └───────────┘
      ▲                 │   ▲                     │                       │
      │                 ▼   │                     │                       ▼
      │             ┌───────┘                     │                  ┌──────────┐
      └─────────────┤                             │                  │ ARCHIVED │
                    └─────────────────────────────┘                  └────┬─────┘
                                                                         │
                              ┌──────────────────────────────────────────┘
                              ▼
                          ┌───────┐
                          │ DRAFT │  (повторная публикация)
                          └───────┘
```

### Бизнес-правила

| Переход              | Что происходит                                                |
| -------------------- | ------------------------------------------------------------- |
| → `ENRICHING`        | Менеджер начал наполнять карточку                             |
| → `READY_FOR_REVIEW` | Карточка готова к проверке                                    |
| → `PUBLISHED`        | Устанавливается `published_at` (только при первой публикации) |
| → `ARCHIVED`         | Товар скрыт с витрины, SKU остаются                           |
| → `DRAFT`            | Возврат на доработку (из ENRICHING или ARCHIVED)              |

### Ошибки

| Код | Ошибка                       | Когда                            |
| --- | ---------------------------- | -------------------------------- |
| 404 | ProductNotFoundError         | Товар не найден                  |
| 422 | InvalidStatusTransitionError | Переход не разрешён FSM-таблицей |

---

## Конкурентность

### Optimistic Locking

Каждый товар и SKU имеет `version` — целочисленный счётчик:

```sql
UPDATE products
SET    title_i18n = ..., version = 2, updated_at = now()
WHERE  id = '...' AND version = 1;
-- 0 rows affected → StaleDataError
```

При конкурентном обновлении SQLAlchemy выбросит ошибку — клиент должен перечитать и повторить.

### Soft Delete

Товары и SKU не удаляются физически:

```sql
UPDATE products SET deleted_at = now() WHERE id = '...';
```

Уникальные индексы (`slug`, `sku_code`, `variant_hash`) фильтруются:

```sql
CREATE UNIQUE INDEX uix_products_slug ON products (slug)
WHERE deleted_at IS NULL;
```

---

## Полная схема данных

```
products
├── id                    UUID PK (v7)
├── slug                  VARCHAR(255) UNIQUE (soft-delete aware)
├── title_i18n            JSONB {"ru": "...", "en": "..."}
├── description_i18n      JSONB
├── status                ENUM (draft|enriching|ready_for_review|published|archived)
├── brand_id              UUID FK → brands (RESTRICT)
├── primary_category_id   UUID FK → categories (RESTRICT)
├── supplier_id           UUID FK → suppliers (RESTRICT)
├── source_url            VARCHAR(1024), nullable
├── country_of_origin     VARCHAR(2), nullable
├── tags                  VARCHAR[] (GIN index)
├── popularity_score      INTEGER default 0
├── is_visible            BOOLEAN default true
├── version               INTEGER default 1 (optimistic lock)
├── created_at            TIMESTAMPTZ
├── updated_at            TIMESTAMPTZ
├── published_at          TIMESTAMPTZ, nullable
└── deleted_at            TIMESTAMPTZ, nullable

    skus (1:N cascade)
    ├── id                UUID PK (v7)
    ├── product_id        UUID FK → products (CASCADE)
    ├── sku_code          VARCHAR(100) UNIQUE (soft-delete aware)
    ├── variant_hash      VARCHAR(64) UNIQUE (soft-delete aware)
    ├── main_image_url    VARCHAR(1024), nullable (cached from MediaAsset MAIN)
    ├── price             INTEGER (мин. единицы валюты)
    ├── currency          VARCHAR(3) FK → currencies (RESTRICT)
    ├── compare_at_price  INTEGER, nullable
    ├── attributes_cache  JSONB (денормализованные variant атрибуты)
    ├── is_active         BOOLEAN default true
    ├── version           INTEGER default 1
    ├── created_at        TIMESTAMPTZ
    ├── updated_at        TIMESTAMPTZ
    └── deleted_at        TIMESTAMPTZ, nullable

        sku_attribute_values (M:N)
        ├── sku_id             UUID FK → skus (CASCADE)
        ├── attribute_id       UUID FK → attributes (CASCADE)
        └── attribute_value_id UUID FK → attribute_values (RESTRICT)
            UNIQUE (sku_id, attribute_id)

    product_attribute_values (M:N)
    ├── product_id         UUID FK → products (CASCADE)
    ├── attribute_id       UUID FK → attributes (CASCADE)
    └── attribute_value_id UUID FK → attribute_values (RESTRICT)
        UNIQUE (product_id, attribute_id)

    media_assets (1:N cascade)                ← ФОТО ВАРИАНТОВ
    ├── id                 UUID PK (v7)
    ├── product_id         UUID FK → products (CASCADE)
    ├── attribute_value_id UUID FK → attribute_values (CASCADE), nullable
    │                      ├── NULL = общее фото (все варианты)
    │                      └── UUID = фото конкретного варианта (цвета)
    ├── media_type         ENUM (IMAGE|VIDEO|MODEL_3D|DOCUMENT)
    ├── role               ENUM (MAIN|HOVER|GALLERY|HERO_VIDEO|SIZE_GUIDE|PACKAGING)
    ├── sort_order         INTEGER default 0
    ├── storage_object_id  UUID (soft-link → storage_objects), nullable
    ├── is_external        BOOLEAN default false
    └── external_url       VARCHAR(1024), nullable (YouTube и т.д.)
        UNIQUE (product_id, attribute_value_id) WHERE role = 'MAIN'
```

---

## GIN-индексы для поиска

```sql
-- Полнотекстовый поиск по названию
CREATE INDEX ix_products_title_gin ON products USING gin (title_i18n);

-- Поиск по тегам
CREATE INDEX ix_products_tags_gin ON products USING gin (tags);

-- Листинг каталога (бренд + категория + статус + популярность)
CREATE INDEX ix_products_catalog_listing ON products
  (brand_id, primary_category_id, status, popularity_score)
  WHERE deleted_at IS NULL AND is_visible = true;
```

---

## Пример: полный сценарий создания товара

```bash
# 1. Создать карточку
curl -X POST /api/v1/catalog/products \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "titleI18n":{"ru":"Air Max 90"},
    "slug":"air-max-90",
    "brandId":"...",
    "primaryCategoryId":"...",
    "supplierId":"<poizon-uuid>",
    "sourceUrl":"https://dw4.co/t/A-abc123"
  }'
# → 201 {"id":"PRODUCT_ID","message":"Product created"}

# 2. Добавить SKU (чёрный, 42 размер)
curl -X POST /api/v1/catalog/products/$PRODUCT_ID/skus \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "skuCode":"AM90-BLK-42",
    "priceAmount":1299000,
    "priceCurrency":"UZS",
    "compareAtPriceAmount":1599000,
    "variantAttributes":[
      {"attributeId":"<color-id>","attributeValueId":"<black-id>"},
      {"attributeId":"<size-id>","attributeValueId":"<size-42-id>"}
    ]
  }'
# → 201 {"id":"SKU_ID","message":"SKU added"}

# 3. Загрузить MAIN фото для чёрного варианта
curl -X POST /api/v1/catalog/products/$PRODUCT_ID/media \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "attributeValueId":"<black-id>",
    "role":"main",
    "mediaType":"image",
    "storageObjectId":"<uploaded-photo-uuid>"
  }'
# → 201 {"id":"MEDIA_ID","message":"Media attached"}

# 4. Загрузить GALLERY фото для чёрного варианта
curl -X POST /api/v1/catalog/products/$PRODUCT_ID/media \
  -d '{"attributeValueId":"<black-id>","role":"gallery","mediaType":"image","storageObjectId":"..."}'

# 5. Загрузить общую размерную сетку (для всех цветов)
curl -X POST /api/v1/catalog/products/$PRODUCT_ID/media \
  -d '{"attributeValueId":null,"role":"size_guide","mediaType":"image","storageObjectId":"..."}'

# 6. Назначить product-level атрибут (материал = кожа)
curl -X POST /api/v1/catalog/products/$PRODUCT_ID/attributes \
  -d '{"attributeId":"<material-id>","attributeValueId":"<leather-id>"}'
# → 201 {"id":"PAV_ID","message":"Attribute assigned"}

# 7. FSM: DRAFT → ENRICHING → READY_FOR_REVIEW → PUBLISHED
curl -X PATCH /api/v1/catalog/products/$PRODUCT_ID/status -d '{"status":"enriching"}'
curl -X PATCH /api/v1/catalog/products/$PRODUCT_ID/status -d '{"status":"ready_for_review"}'
curl -X PATCH /api/v1/catalog/products/$PRODUCT_ID/status -d '{"status":"published"}'
# → 200 {product с published_at}
```
