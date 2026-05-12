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
GET  /storefront/categories/{id}/form-attributes  → схема формы (какие атрибуты показать)
POST /products                                    → DRAFT (+ default variant)
POST /products/{id}/variants/{vid}/skus           → добавить SKU (цена + variant attrs)
POST /products/{id}/attributes                    → назначить product-level атрибуты
POST /products/{id}/media                        → привязать media asset (storageObjectId из ImageBackend)
PATCH /products/{id}/status → enriching           → ENRICHING
PATCH /products/{id}/status → ready_for_review    → READY_FOR_REVIEW
PATCH /products/{id}/status → published           → PUBLISHED (на витрине, требует media + SKU с ценой)
```

> **Важно**: Все i18n-поля передаются со строчной `n` в конце: `nameI18n`, `titleI18n`, `descriptionI18n`, `valueI18n`
> Pydantic `to_camel("name_i18n")` = `nameI18n` (`.capitalize()` делает первую букву заглавной, остальные — строчными, поэтому `i18n` → `I18n`, а не `I18N`)

---

## Предварительные условия

Перед созданием товара должны существовать:

```
Brand ──────────────────────────────────┐
                                        ▼
Attribute ── AttributeValue          Product (DRAFT)
    │                                   │
    ▼                                   ├── ProductAttributeValue
AttributeTemplate                       ├── ProductVariant (auto)
    │                                   │       └── SKU
    ▼                                   │            └── MediaAsset
TemplateAttributeBinding                │
    │                                   └── Status FSM
    ▼
Category (templateId → effectiveTemplateId)
```

| Сущность            | Endpoint                                            | Что хранит                                      |
| ------------------- | --------------------------------------------------- | ----------------------------------------------- |
| Brand               | `POST /catalog/brands`                              | Название, slug, логотип                         |
| Category            | `POST /catalog/categories`                          | Иерархия, slug, шаблон атрибутов                |
| Attribute           | `POST /catalog/attributes`                          | Определение характеристики (тип, UI виджет)     |
| AttributeValue      | `POST /catalog/attributes/{id}/values/bulk`         | Конкретные значения (Red, XL, Cotton)           |
| AttributeTemplate   | `POST /catalog/attribute-templates`                 | Шаблон: какие атрибуты применимы к категории    |
| TemplateBinding     | `POST /catalog/attribute-templates/{id}/attributes` | Привязка атрибута к шаблону + requirement level |
| Category ← Template | `PATCH /catalog/categories/{id}` + `{templateId}`   | CTE-пропагация к children                       |

---

## Шаг 0. Получить схему формы (Storefront)

Перед рендером формы фронтенд загружает **какие поля показать** для выбранной категории.

### Запрос

```
GET /api/v1/catalog/storefront/categories/{category_id}/form-attributes?lang=ru
Authorization: Bearer <token>
Permission: catalog:manage
```

### Ответ

```json
{
  "categoryId": "019cdbf4-e987-...",
  "groups": [
    {
      "groupId": "uuid",
      "groupCode": "physical",
      "groupNameI18n": { "ru": "Физические характеристики" },
      "groupSortOrder": 1,
      "attributes": [
        {
          "attributeId": "uuid-shoe-size",
          "code": "shoe_size",
          "slug": "shoe-size",
          "nameI18n": { "ru": "Размер обуви", "en": "Shoe Size" },
          "name": "Размер обуви",
          "descriptionI18n": { "ru": "EU размер" },
          "dataType": "float",
          "uiType": "text_button",
          "isDictionary": true,
          "level": "variant",
          "requirementLevel": "required",
          "isFilterable": true,
          "isVisibleOnCard": true,
          "isComparable": false,
          "validationRules": null,
          "values": [
            { "id": "uuid", "code": "eu42", "slug": "eu42", "valueI18n": {"ru":"EU 42"}, "metaData": {}, "sortOrder": 0 },
            { "id": "uuid", "code": "eu43", "slug": "eu43", "valueI18n": {"ru":"EU 43"}, "metaData": {}, "sortOrder": 1 }
          ],
          "sortOrder": 1
        }
      ]
    }
  ]
}
```

### Как фронтенд использует это

| Поле                              | Использование                                                                            |
| --------------------------------- | ---------------------------------------------------------------------------------------- |
| `level: "product"`                | Показать в секции product-level атрибутов                                                |
| `level: "variant"`                | Показать в SKU-матрице / variant-атрибутах                                               |
| `requirementLevel: "required"`    | Пометить поле обязательным, блокировать сохранение                                       |
| `requirementLevel: "recommended"` | Показать предупреждение если пусто                                                       |
| `uiType`                          | Выбрать UI-виджет: `text_button`, `color_swatch`, `dropdown`, `checkbox`, `range_slider` |
| `isDictionary: true`              | Рендерить как выбор из `values[]`                                                        |
| `values[]`                        | Заполнить dropdown/swatch опции                                                          |
| `validationRules`                 | Клиентская валидация (min/max length, pattern)                                           |
| `metaData.hex`                    | Hex-цвет для color swatch                                                                |

### Другие storefront-эндпоинты

| Endpoint                                                | Назначение                                   |
| ------------------------------------------------------- | -------------------------------------------- |
| `GET /storefront/categories/{id}/filters`               | Фильтры каталога + значения                  |
| `GET /storefront/categories/{id}/card-attributes`       | Атрибуты на карточке товара (группированные) |
| `GET /storefront/categories/{id}/comparison-attributes` | Атрибуты для таблицы сравнения               |

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
  "brandId": "brand-uuid",
  "primaryCategoryId": "sneakers-category-uuid",
  "descriptionI18n": {
    "ru": "Легендарные кроссовки Nike с технологией Air",
    "en": "Iconic Nike sneakers with Air technology"
  },
  "tags": ["nike", "air-max", "sneakers", "running"]
}
```

### Валидация

| Поле                | Правила                                                                                                           |
| ------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `titleI18n`         | Обязательно, ключи `ru` + `en` обязательны                                                                        |
| `slug`              | `^[a-z0-9-]+$`, 1-255 символов, уникальный                                                                        |
| `brandId`           | UUID, FK → brands (RESTRICT)                                                                                      |
| `primaryCategoryId` | UUID, FK → categories (RESTRICT)                                                                                  |
| `descriptionI18n`   | Опционально — **поле можно не передавать**. Если передаёшь, оба ключа `ru` + `en` обязательны (как у `titleI18n`) |
| `supplierId`        | UUID или null, FK → suppliers                                                                                     |
| `sourceUrl`         | `^https?://`, max 1024, или null. **Только при создании** — недоступно в PATCH                                    |
| `tags`              | Массив строк, max 50 элементов, каждый max 200 символов                                                           |

### Внутренний flow

```
Router                     Handler                      Domain                    Repository
  │                          │                            │                          │
  ├─ parse request ─────────►│                            │                          │
  │                          ├─ async with uow ──────────►│                          │
  │                          │                            │                          │
  │                          ├─ brand_repo.get() ───────────────────────────────────►│
  │                          │◄─ brand exists ───────────────────────────────────────│
  │                          │                            │                          │
  │                          ├─ category_repo.get() ────────────────────────────────►│
  │                          │◄─ category exists ────────────────────────────────────│
  │                          │                            │                          │
  │                          ├─ check_slug_exists() ────────────────────────────────►│
  │                          │◄─ false ──────────────────────────────────────────────│
  │                          │                            │                          │
  │                          ├─ Product.create() ────────►│                          │
  │                          │                            ├─ validate titleI18n      │
  │                          │                            ├─ generate UUID v7        │
  │                          │                            ├─ status = DRAFT          │
  │                          │                            ├─ version = 1             │
  │                          │                            ├─ create default Variant  │
  │                          │                            ├─ emit ProductCreatedEvent│
  │                          │◄─ product ─────────────────│                          │
  │                          │                            │                          │
  │                          ├─ repo.add(product) ──────────────────────────────────►│
  │                          │                            │        _to_orm()         │
  │                          │                            │      session.flush()     │
  │                          │                            │                          │
  │                          ├─ uow.commit() ────────────►│                          │
  │                          │                        INSERT products + product_variants
  │                          │                            │                          │
  │◄─ 201 Created ───────────│                            │                          │
```

### Ответ

```json
{
  "id": "019ce123-abcd-7000-8080-000000000001",
  "defaultVariantId": "019ce123-abcd-7000-8080-000000000002",
  "message": "Product created"
}
```

Товар создан в статусе `DRAFT` с 1 дефолтным вариантом.

### Ошибки

| Код | Ошибка                   | Когда                                          |
| --- | ------------------------ | ---------------------------------------------- |
| 401 | Unauthorized             | Нет токена или токен невалидный                |
| 403 | ForbiddenError           | Нет права `catalog:manage`                     |
| 404 | BrandNotFoundError       | Brand с указанным ID не найден                 |
| 404 | CategoryNotFoundError    | Category с указанным ID не найдена             |
| 409 | ProductSlugConflictError | Товар с таким slug уже существует              |
| 422 | RequestValidationError   | `titleI18n` пустой, slug невалидный (Pydantic) |

---

## Шаг 2. Загрузка медиа (ImageBackend)

Каждый вариант товара имеет **свою коллекцию фото**. Физические файлы хранятся в отдельном сервисе ImageBackend.

### Архитектура

```
┌───────────┐     ┌───────────┐     ┌───────────────┐     ┌───────────┐
│ Frontend  │     │  Backend  │     │ ImageBackend  │     │  Bucket   │
│ (Next.js) │     │ (бизнес-  │     │ (обработка +  │     │   (S3)    │
│           │     │  логика)  │     │  хранение)    │     │           │
└───────────┘     └───────────┘     └───────────────┘     └───────────┘
```

### Flow загрузки

```
  Frontend              Backend              ImageBackend              Bucket
     │                     │                      │                      │
 ┌───┴─────────────────────┴──────────────────────┴──────────────────────┴───┐
 │                STEP 1 — Получить presigned URL                            │
 └───┬─────────────────────┬──────────────────────┬──────────────────────┬───┘
     │                     │                      │                      │
     │  POST /api/v1/media/upload                 │                      │
     │  { contentType: "image/jpeg",              │                      │
     │    filename: "photo.jpg" }                 │                      │
     │  ─────────────────────────────────────────►│                      │
     │                     │                      │  generate key        │
     │                     │                      │  ──────────────────► │
     │                     │                      │  ◄── presigned URL ─ │
     │  ◄── 201 ──────────────────────────────────│                      │
     │  { presignedUrl, storageObjectId,          │                      │
     │    expiresIn: 300 }                        │                      │
     │                     │                      │                      │
 ┌───┴─────────────────────┴──────────────────────┴──────────────────────┴───┐
 │           STEP 2 — Загрузить файл напрямую в Bucket                       │
 └───┬─────────────────────┬──────────────────────┬──────────────────────┬───┘
     │                     │                      │                      │
     │  PUT presignedUrl (binary body) ────────────────────────────────► │
     │  ◄── 200 OK ────────────────────────────────────────────────────  │
     │                     │                      │                      │
 ┌───┴─────────────────────┴──────────────────────┴──────────────────────┴───┐
 │         STEP 3 — Подтвердить и запустить обработку                        │
 └───┬─────────────────────┬──────────────────────┬──────────────────────┬───┘
     │                     │                      │                      │
     │  POST /api/v1/media/{storageObjectId}/confirm                     │
     │  ─────────────────────────────────────────►│                      │
     │                     │                      │  verify file exists  │
     │                     │                      │  status → processing │
     │                     │                      │  dispatch worker     │
     │  ◄── 202 Accepted ─────────────────────────│                      │
     │                     │                      │                      │
 ┌───┴─────────────────────┴──────────────────────┴──────────────────────┴───┐
 │       STEP 4 — Worker обрабатывает (thumbnail, medium, large)             │
 └───┬─────────────────────┬──────────────────────┬──────────────────────┬───┘
     │                     │                      │  ◄── read original ─ │
     │                     │                      │  process:            │
     │                     │                      │   thumbnail 150x150  │
     │                     │                      │   medium 600x600     │
     │                     │                      │   large 1200x1200    │
     │                     │                      │  ── PUT variants ──► │
     │                     │                      │  status → completed  │
     │                     │                      │                      │
 ┌───┴─────────────────────┴──────────────────────┴──────────────────────┴───┐
 │              STEP 5 — Polling статуса                                     │
 └───┬─────────────────────┬──────────────────────┬──────────────────────┬───┘
     │  GET /api/v1/media/{storageObjectId}       │                      │
     │  ─────────────────────────────────────────►│                      │
     │  ◄── 200 { status: "COMPLETED",            │                      │
     │           url: "https://cdn.../id.webp",   │                      │
     │           variants: [...] }                │                      │
     │                     │                      │                      │
 ┌───┴─────────────────────┴──────────────────────┴──────────────────────┴───┐
 │      STEP 6 — Привязать к продукту                                       │
 └───┬─────────────────────┬──────────────────────┬──────────────────────┬───┘
     │  POST /api/v1/catalog/products/{id}/media  │                      │
     │  { storageObjectId: "uuid-...",            │                      │
     │    variantId: "variant-uuid" | null,       │                      │
     │    role: "main",                           │                      │
     │    mediaType: "image",                     │                      │
     │    sortOrder: 0 }                          │                      │
     │  ──────────────────►│  создаёт             │                      │
     │  ◄── 201 ───────────│  media_asset         │                      │
```

### Роли медиа

| Role         | Описание              | Сколько на вариант |
| ------------ | --------------------- | ------------------ |
| `main`       | Главное фото          | ровно 1            |
| `hover`      | Фото при наведении    | 0-1                |
| `gallery`    | Дополнительные фото   | 0-N                |
| `hero_video` | Видео (YouTube, файл) | 0-1                |
| `size_guide` | Размерная сетка       | 0-1 (обычно общее) |
| `packaging`  | Фото упаковки         | 0-N                |

### Media API Endpoints

Привязка медиа к продукту через catalog API:

#### Добавить медиа

```
POST /api/v1/catalog/products/{product_id}/media
Authorization: Bearer <token>
Permission: catalog:manage
```

```json
{
  "storageObjectId": "uuid-from-imagebackend",
  "variantId": "variant-uuid-or-null",
  "mediaType": "image",
  "role": "main",
  "sortOrder": 0,
  "isExternal": false
}
```

**Валидация:**

| Поле              | Правила                                                                                 |
| ----------------- | --------------------------------------------------------------------------------------- |
| `storageObjectId` | UUID, обязательно для internal (`isExternal: false`)                                    |
| `variantId`       | UUID или null, FK → product_variants (проверяется принадлежность)                       |
| `mediaType`       | `image`, `video`, `model_3d`, `document`. Default: `image`                              |
| `role`            | `main`, `hover`, `gallery`, `hero_video`, `size_guide`, `packaging`. Default: `gallery` |
| `sortOrder`       | `>= 0`, default `0`                                                                     |
| `isExternal`      | bool, default `false`                                                                   |
| `url`             | `^https?://`, max 1024. Обязательно если `isExternal: true`                             |

**Ответ:** `201 { "id": "media-asset-uuid", "message": "Media asset created" }`

**Ошибки:**

| Код | Ошибка                  | Когда                                           |
| --- | ----------------------- | ----------------------------------------------- |
| 404 | ProductNotFoundError    | Товар не найден                                 |
| 404 | VariantNotFoundError    | Вариант не найден / не принадлежит товару       |
| 409 | DuplicateMainMediaError | MAIN уже существует для данного product+variant |
| 422 | ValidationError         | External без URL, internal без storageObjectId  |

#### Список медиа

```
GET /api/v1/catalog/products/{product_id}/media?offset=0&limit=50
Permission: catalog:read
```

**Ответ:** `PaginatedResponse<MediaAssetResponse>`

```json
{
  "items": [
    {
      "id": "uuid",
      "productId": "uuid",
      "variantId": "uuid-or-null",
      "mediaType": "image",
      "role": "main",
      "sortOrder": 0,
      "storageObjectId": "uuid",
      "url": "https://cdn.../image.webp",
      "isExternal": false,
      "imageVariants": [
        { "size": "thumbnail", "width": 150, "height": 150, "url": "https://cdn.../thumb.webp" },
        { "size": "medium", "width": 600, "height": 600, "url": "https://cdn.../med.webp" }
      ],
      "createdAt": "2026-03-27T10:00:00Z",
      "updatedAt": "2026-03-27T10:00:00Z"
    }
  ],
  "total": 1, "offset": 0, "limit": 50, "hasNext": false
}
```

#### Обновить медиа

```
PATCH /api/v1/catalog/products/{product_id}/media/{media_id}
Permission: catalog:manage
```

```json
{ "role": "gallery", "sortOrder": 2 }
```

PATCH-семантика: передаются только изменяемые поля (`role`, `variantId`, `sortOrder`).

#### Удалить медиа

```
DELETE /api/v1/catalog/products/{product_id}/media/{media_id}
Permission: catalog:manage
→ 204 No Content
```

Best-effort cleanup: после удаления записи из БД вызывается `ImageBackend.delete(storageObjectId)`.

#### Переупорядочить медиа

```
POST /api/v1/catalog/products/{product_id}/media/reorder
Permission: catalog:manage
```

```json
{
  "items": [
    { "mediaId": "uuid-1", "sortOrder": 0 },
    { "mediaId": "uuid-2", "sortOrder": 1 },
    { "mediaId": "uuid-3", "sortOrder": 2 }
  ]
}
```

Max 100 items. `→ 204 No Content`

---

## Шаг 3. Добавление SKU (вариантов)

Товар без SKU не может быть опубликован. Каждый SKU — конкретная комбинация variant-атрибутов (цвет + размер) **со своей ценой**.

### Запрос

```
POST /api/v1/catalog/products/{product_id}/variants/{variant_id}/skus
Authorization: Bearer <token>
Permission: catalog:manage
```

```json
{
  "skuCode": "AIR-MAX-90-BLK-42",
  "priceAmount": 12990,
  "priceCurrency": "RUB",
  "compareAtPriceAmount": 15990,
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

Используйте `defaultVariantId` из ответа создания продукта (Шаг 1).

### Валидация

| Поле                   | Правила                                                                          |
| ---------------------- | -------------------------------------------------------------------------------- |
| `skuCode`              | 1-100 символов, уникальный (soft-delete aware)                                   |
| `priceAmount`          | `>= 0` или null, в минимальных единицах валюты (копейки)                         |
| `priceCurrency`        | ISO 4217, 3 символа (`RUB`, `USD`, `UZS`), default `RUB`                         |
| `compareAtPriceAmount` | `>= 0` или null, должна быть > price; нельзя указывать если `priceAmount` = null |
| `isActive`             | bool, default `true`                                                             |
| `variantAttributes`    | Массив пар `(attributeId, attributeValueId)`, max 50                             |

### Variant Hash

Гарантирует уникальность комбинации атрибутов:

```
Атрибуты: [color=black, size=42]

SHA-256( variant_id + ":" + sorted("uuid-color:uuid-black|uuid-size:uuid-42") )
→ "a3f2b8..."
```

### Ответ

```json
{
  "id": "019ce456-...",
  "message": "SKU created"
}
```

### Ошибки

| Код | Ошибка                           | Когда                               |
| --- | -------------------------------- | ----------------------------------- |
| 404 | ProductNotFoundError             | Товар не найден                     |
| 404 | VariantNotFoundError             | Вариант не найден                   |
| 409 | SKUCodeConflictError             | SKU с таким кодом уже существует    |
| 409 | DuplicateVariantCombinationError | Такая комбинация атрибутов уже есть |
| 422 | ValueError                       | compareAtPrice <= price             |

---

## Шаг 4. Назначение атрибутов товару

Product-level атрибуты (не вариантные) — например, материал, пол, сезон.

### Запрос (единичный)

```
POST /api/v1/catalog/products/{product_id}/attributes
Authorization: Bearer <token>
Permission: catalog:manage
```

```json
{
  "attributeId": "<material-attr-id>",
  "attributeValueId": "<leather-value-id>"
}
```

### Запрос (массовый)

```
POST /api/v1/catalog/products/{product_id}/attributes/bulk
```

```json
{
  "items": [
    { "attributeId": "<gender-id>", "attributeValueId": "<male-id>" },
    { "attributeId": "<season-id>", "attributeValueId": "<all-season-id>" }
  ]
}
```

### Внутренний flow

```
1. Проверить что товар существует
2. Загрузить effectiveTemplateId категории товара
3. Проверить что атрибут входит в шаблон (если шаблон назначен)
4. Проверить что атрибут level = "product" и isDictionary = true
5. Проверить что значение принадлежит атрибуту
6. Проверить что атрибут ещё не назначен этому товару
7. Создать ProductAttributeValue → Commit
```

### Constraint

Один атрибут = одно значение на товар:

```sql
UNIQUE (product_id, attribute_id)
```

### Ошибки

| Код | Ошибка                         | Когда                                |
| --- | ------------------------------ | ------------------------------------ |
| 404 | ProductNotFoundError           | Товар не найден                      |
| 404 | AttributeNotFoundError         | Атрибут не найден                    |
| 404 | AttributeValueNotFoundError    | Значение не найдено                  |
| 409 | DuplicateProductAttributeError | Атрибут уже назначен этому товару    |
| 422 | AttributeLevelMismatchError    | Атрибут level != "product"           |
| 422 | AttributeNotDictionaryError    | isDictionary = false                 |
| 422 | AttributeNotInTemplateError    | Атрибут не входит в шаблон категории |

---

## Шаг 5. Создание дополнительных вариантов (опционально)

По умолчанию при создании товара создается 1 вариант. Дополнительные варианты нужны для разных вкладок/версий товара.

```
POST /api/v1/catalog/products/{product_id}/variants
```

```json
{
  "nameI18n": { "ru": "Красный", "en": "Red" },
  "descriptionI18n": { "ru": "Красная расцветка", "en": "Red colorway" },
  "sortOrder": 1,
  "defaultPriceAmount": 12990,
  "defaultPriceCurrency": "RUB"
}
```

`descriptionI18n` опционально — можно не передавать. Если передаёшь, требуются ключи `ru` + `en`.

Затем добавьте SKU к новому варианту (Шаг 3).

---

## Шаг 6. Смена статуса (FSM)

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
    ▲   ▲                  │   ▲                     │                 │
    │   └──────────────────┘   └─────────────────────┘                 ▼
    │                                                         ┌──────────┐
    └─────────────────────────────────────────────────────────│ ARCHIVED │
                                                              └──────────┘
```

### Гарды переходов

| Переход              | Условие                                                  | Бизнес-смысл                               |
| -------------------- | -------------------------------------------------------- | ------------------------------------------ |
| → `ENRICHING`        | —                                                        | Менеджер начал наполнять карточку          |
| → `READY_FOR_REVIEW` | Минимум 1 active SKU                                     | Карточка готова к проверке                 |
| → `PUBLISHED`        | Минимум 1 active SKU **с ценой** + минимум 1 media asset | Устанавливается `publishedAt` (первый раз) |
| → `ARCHIVED`         | —                                                        | Товар скрыт с витрины, SKU остаются        |
| → `DRAFT`            | —                                                        | Возврат на доработку                       |
| `DELETE` product     | status != `PUBLISHED`                                    | Сначала нужно архивировать                 |

### Ошибки

| Код | Ошибка                       | Когда                                                              |
| --- | ---------------------------- | ------------------------------------------------------------------ |
| 404 | ProductNotFoundError         | Товар не найден                                                    |
| 422 | InvalidStatusTransitionError | Переход не разрешен FSM-таблицей                                   |
| 422 | ProductNotReadyError         | Нет active SKU / нет SKU с ценой / нет media asset (для PUBLISHED) |

---

## Шаг 7. Проверка полноты (опционально)

```
GET /api/v1/catalog/products/{product_id}/completeness
```

```json
{
  "isComplete": false,
  "totalRequired": 2,
  "filledRequired": 1,
  "totalRecommended": 1,
  "filledRecommended": 0,
  "missingRequired": [
    { "attributeId": "uuid", "code": "color", "nameI18n": {"ru":"Цвет","en":"Color"} }
  ],
  "missingRecommended": [
    { "attributeId": "uuid", "code": "material", "nameI18n": {"ru":"Материал","en":"Material"} }
  ]
}
```

Soft-check — не блокирует переходы, но показывает фронтенду что не заполнено.

---

## Конкурентность

### Optimistic Locking

Каждый товар и SKU имеет `version` — целочисленный счетчик:

```sql
UPDATE products
SET    title_i18n = ..., version = 2, updated_at = now()
WHERE  id = '...' AND version = 1;
-- 0 rows affected → ConcurrencyError (409)
```

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
├── supplier_id           UUID FK → suppliers (RESTRICT), nullable
├── source_url            VARCHAR(1024), nullable
├── country_of_origin     VARCHAR(2), nullable
├── tags                  VARCHAR[] (GIN index)
├── attributes            JSONB (denormalized attribute cache)
├── popularity_score      INTEGER default 0
├── is_visible            BOOLEAN default true
├── version               INTEGER default 1 (optimistic lock)
├── created_at            TIMESTAMPTZ
├── updated_at            TIMESTAMPTZ
├── published_at          TIMESTAMPTZ, nullable
└── deleted_at            TIMESTAMPTZ, nullable

    product_variants (1:N cascade)
    ├── id                UUID PK (v7)
    ├── product_id        UUID FK → products (CASCADE)
    ├── name_i18n         JSONB
    ├── description_i18n  JSONB, nullable
    ├── sort_order         INTEGER default 0
    ├── default_price      INTEGER, nullable (min currency units)
    ├── default_currency   VARCHAR(3) FK → currencies (RESTRICT)
    ├── deleted_at         TIMESTAMPTZ, nullable
    ├── created_at         TIMESTAMPTZ
    └── updated_at         TIMESTAMPTZ

        skus (1:N cascade from variant)
        ├── id                UUID PK (v7)
        ├── product_id        UUID FK → products (CASCADE)
        ├── variant_id        UUID FK → product_variants (CASCADE)
        ├── sku_code          VARCHAR(100) UNIQUE (soft-delete aware)
        ├── variant_hash      VARCHAR(64) UNIQUE (soft-delete aware)
        ├── main_image_url    VARCHAR(1024), nullable (denormalized)
        ├── attributes_cache  JSONB (denormalized variant attributes)
        ├── price             INTEGER, nullable (inherits from variant)
        ├── currency          VARCHAR(3) FK → currencies (RESTRICT)
        ├── compare_at_price  INTEGER, nullable
        ├── is_active         BOOLEAN default true
        ├── version           INTEGER default 1
        ├── created_at        TIMESTAMPTZ
        ├── updated_at        TIMESTAMPTZ
        └── deleted_at        TIMESTAMPTZ, nullable

            sku_attribute_values (M:N)
            ├── id                 UUID PK (v7)
            ├── sku_id             UUID FK → skus (CASCADE)
            ├── attribute_id       UUID FK → attributes (CASCADE)
            └── attribute_value_id UUID FK → attribute_values (RESTRICT)
                UNIQUE (sku_id, attribute_id)

    product_attribute_values (M:N)
    ├── id                 UUID PK (v7)
    ├── product_id         UUID FK → products (CASCADE)
    ├── attribute_id       UUID FK → attributes (CASCADE)
    └── attribute_value_id UUID FK → attribute_values (RESTRICT)
        UNIQUE (product_id, attribute_id)

    media_assets (1:N cascade)
    ├── id                 UUID PK (v7)
    ├── product_id         UUID FK → products (CASCADE)
    ├── variant_id         UUID FK → product_variants (CASCADE), nullable
    ├── media_type         ENUM (image|video|model_3d|document)
    ├── role               ENUM (main|hover|gallery|hero_video|size_guide|packaging)
    ├── sort_order         INTEGER default 0
    ├── storage_object_id  UUID (soft-link → ImageBackend), nullable
    ├── is_external        BOOLEAN default false
    ├── url                VARCHAR(1024), nullable
    ├── image_variants     JSONB [{size, width, height, url}, ...]
    ├── created_at         TIMESTAMPTZ
    └── updated_at         TIMESTAMPTZ
        UNIQUE (product_id, variant_id) WHERE role = 'MAIN'
```

---

## Полный curl-сценарий

```bash
# 0. Получить схему формы для категории
curl -s /api/v1/catalog/storefront/categories/$CATEGORY_ID/form-attributes?lang=ru \
  -H "Authorization: Bearer $TOKEN"
# → 200 { groups: [{ attributes: [...] }] }

# 1. Создать карточку
curl -X POST /api/v1/catalog/products \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "titleI18n":{"ru":"Air Max 90","en":"Air Max 90"},
    "slug":"air-max-90",
    "brandId":"...",
    "primaryCategoryId":"..."
  }'
# → 201 {"id":"PRODUCT_ID","defaultVariantId":"VARIANT_ID","message":"Product created"}

# 2. Загрузить фото через ImageBackend
curl -X POST /api/v1/media/upload \
  -H "Content-Type: application/json" \
  -d '{"contentType":"image/jpeg","filename":"photo.jpg"}'
# → 201 {"presignedUrl":"https://s3.../...","storageObjectId":"STORAGE_ID"}
curl -X PUT "$PRESIGNED_URL" --data-binary @photo.jpg -H "Content-Type: image/jpeg"
# → 200 OK
curl -X POST /api/v1/media/$STORAGE_ID/confirm
# → 202 {"status":"processing"}

# 2b. Привязать фото к продукту (после status=COMPLETED)
curl -X POST /api/v1/catalog/products/$PRODUCT_ID/media \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "storageObjectId":"'$STORAGE_ID'",
    "variantId":"'$VARIANT_ID'",
    "role":"main",
    "mediaType":"image",
    "sortOrder":0
  }'
# → 201 {"id":"MEDIA_ID","message":"Media asset created"}

# 3. Добавить SKU (черный, 42 размер)
curl -X POST /api/v1/catalog/products/$PRODUCT_ID/variants/$VARIANT_ID/skus \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "skuCode":"AM90-BLK-42",
    "priceAmount":12990,
    "priceCurrency":"RUB",
    "variantAttributes":[
      {"attributeId":"<color-id>","attributeValueId":"<black-id>"},
      {"attributeId":"<size-id>","attributeValueId":"<42-id>"}
    ]
  }'
# → 201 {"id":"SKU_ID","message":"SKU created"}

# 4. Назначить product-level атрибут (материал = кожа)
curl -X POST /api/v1/catalog/products/$PRODUCT_ID/attributes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"attributeId":"<material-id>","attributeValueId":"<leather-id>"}'
# → 201 {"id":"PAV_ID","message":"Attribute assigned to product"}

# 5. FSM: DRAFT → ENRICHING → READY_FOR_REVIEW → PUBLISHED
# ⚠ Переход в PUBLISHED требует: 1 active SKU с ценой + 1 media asset
curl -X PATCH /api/v1/catalog/products/$PRODUCT_ID/status \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"enriching"}'
curl -X PATCH /api/v1/catalog/products/$PRODUCT_ID/status \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"ready_for_review"}'
curl -X PATCH /api/v1/catalog/products/$PRODUCT_ID/status \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status":"published"}'
# → 200 { product с publishedAt }
```
