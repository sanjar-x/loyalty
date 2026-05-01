# Product Creation — Full Integration Guide

## Architecture

Атрибуты управляются через **AttributeFamily**. Category ссылается на Family через `familyId`. Family определяет какие атрибуты нужны продуктам.

Атрибуты делятся на два уровня:

- `level: "product"` — одинаковы для всех SKU (материал, стиль) → привязываются к **Product**
- `level: "variant"` — разные для каждого SKU (размер, цвет) → привязываются к **SKU**

---

## Flow создания продукта

```
Step 1: Выбрать категорию              GET /catalog/categories/tree
Step 2: Загрузить атрибуты формы       GET .../storefront/categories/{categoryId}/form-attributes
Step 3: Выбрать бренд                  GET /catalog/brands
Step 4: Заполнить ВСЮ форму           (основные поля + product attrs + variant selections)
Step 5: Создать продукт                POST /catalog/products → { id, defaultVariantId }
Step 6: Bulk-присвоить product attrs   POST /products/{id}/attributes/bulk
Step 7: Генерация SKU                  POST .../variants/{defaultVariantId}/skus/generate
Step 8: Загрузить медиа                POST .../media/upload → S3 → confirm
Step 9: Сменить статус                 PATCH .../products/{id}/status
```

> **Важно:**
>
> - Step 2 выполняется **сразу после выбора категории**, не после создания продукта
> - Step 5 возвращает `defaultVariantId` — **не создавайте variant вручную**, он уже есть
> - Step 6 использует `/bulk` endpoint — один запрос, одна транзакция
> - Step 7 использует `/generate` — бэкенд сам строит cartesian product
> - Бэкенд **валидирует** что атрибуты входят в Family категории и что `level` корректен

---

## Step 2: Загрузить атрибуты формы

```
GET /api/v1/catalog/storefront/categories/{categoryId}/form-attributes
Authorization: Bearer <accessToken>
```

**Permission:** `catalog:manage`

Бэкенд: `category → familyId → resolve effective attributes`. Если `familyId = null` → пустой `groups: []`.

### Response

```jsonc
{
  "categoryId": "uuid",
  "groups": [
    {
      "groupId": "uuid | null",
      "groupCode": "physical | null",
      "groupNameI18n": { "en": "Physical", "ru": "Физические характеристики" },
      "groupSortOrder": 0,
      "attributes": [
        {
          "attributeId": "uuid",
          "code": "clothing_size",
          "slug": "clothing-size",
          "nameI18n": { "en": "Clothing Size", "ru": "Размер одежды" },
          "descriptionI18n": { "en": "Letter-based clothing size" },
          "dataType": "string", // string | integer | float | boolean
          "uiType": "text_button", // text_button | color_swatch | dropdown | checkbox | range_slider
          "isDictionary": true, // true = выбор из values[], false = free input
          "level": "variant", // product | variant ← КРИТИЧЕСКИ ВАЖНО
          "requirementLevel": "required", // required | recommended | optional
          "validationRules": null, // { "min_length": 1 } — keys в snake_case!
          "values": [
            {
              "id": "uuid",
              "code": "m",
              "slug": "m",
              "valueI18n": { "en": "M", "ru": "M" },
              "metaData": {},
              "valueGroup": null,
              "sortOrder": 4,
            },
          ],
          "sortOrder": 1,
        },
      ],
    },
  ],
}
```

> **Примечание:** Ключи внутри `validationRules` — `snake_case` (`min_length`, `max_length`, `min_value`, `max_value`, `pattern`), потому что хранятся как raw JSONB, а не через CamelModel.

---

## Step 5: Создать продукт

```
POST /api/v1/catalog/products
Authorization: Bearer <accessToken>
```

**Permission:** `catalog:manage`

### Request

```json
{
  "titleI18n": { "ru": "Название", "en": "Title" },
  "slug": "product-slug",
  "brandId": "uuid",
  "primaryCategoryId": "uuid",
  "descriptionI18n": { "ru": "Описание" },
  "supplierId": "uuid | null",
  "sourceUrl": "https://... | null",
  "countryOfOrigin": "RU | null",
  "tags": ["tag1", "tag2"]
}
```

**Обязательные:** `titleI18n` (мин. 1 язык), `slug` (^[a-z0-9-]+$), `brandId`, `primaryCategoryId`
**Опциональные:** `descriptionI18n`, `supplierId`, `sourceUrl` (обязателен если supplier type = CROSS_BORDER; **immutable** — задаётся только при создании, в PATCH игнорируется), `countryOfOrigin` (ISO 3166-1 alpha-2), `tags`

### Response (201)

```jsonc
{
  "id": "uuid",
  "defaultVariantId": "uuid", // ← бэкенд автоматически создаёт variant
  "message": "Product created",
}
```

> **НЕ создавайте variant вручную** через `POST .../variants`! `Product.create()` автоматически создаёт default variant. Используйте `defaultVariantId` из response для Step 7.

---

## Step 6: Bulk-присвоить product-level атрибуты

### Bulk endpoint (рекомендуемый)

```
POST /api/v1/catalog/products/{productId}/attributes/bulk
Authorization: Bearer <accessToken>
```

### Request

```json
{
  "items": [
    { "attributeId": "uuid", "attributeValueId": "uuid" },
    { "attributeId": "uuid", "attributeValueId": "uuid" }
  ]
}
```

**Constraints:** `items` — от 1 до 50 элементов. Только `level: "product"` атрибуты.

### Response (201)

```json
{
  "assignedCount": 2,
  "pavIds": ["uuid", "uuid"],
  "message": "Assigned 2 attributes"
}
```

### Single endpoint (для редактирования одного атрибута)

```
POST /api/v1/catalog/products/{productId}/attributes
{ "attributeId": "uuid", "attributeValueId": "uuid" }
→ 201 { "id": "uuid", "message": "Attribute assigned to product" }

DELETE /api/v1/catalog/products/{productId}/attributes/{attributeId}
→ 204
```

> **Примечание:** `{attributeId}` — это UUID атрибута (не ID записи привязки). Удаляет привязку данного атрибута к продукту.

```
GET /api/v1/catalog/products/{productId}/attributes?limit=50&offset=0
→ 200 { items: [ProductAttribute], total, offset, limit }
```

### Errors

| Status | Code                          | Meaning                                                         |
| ------ | ----------------------------- | --------------------------------------------------------------- |
| 404    | `PRODUCT_NOT_FOUND`           | Продукт не найден                                               |
| 404    | `ATTRIBUTE_NOT_FOUND`         | Атрибут не найден                                               |
| 404    | `ATTRIBUTE_VALUE_NOT_FOUND`   | Значение не найдено или не принадлежит атрибуту                 |
| 422    | `ATTRIBUTE_NOT_DICTIONARY`    | Атрибут не словарный, нельзя присвоить value                    |
| 422    | `ATTRIBUTE_NOT_IN_FAMILY`     | Атрибут не входит в Family категории продукта                   |
| 422    | `ATTRIBUTE_LEVEL_MISMATCH`    | Уровень атрибута не соответствует endpoint (ожидался `product`) |
| 409    | `DUPLICATE_PRODUCT_ATTRIBUTE` | Этот атрибут уже присвоен продукту                              |

> При ошибке в bulk запросе вся транзакция откатывается. Ответ содержит `attribute_id` проблемного атрибута в `details`.

---

## Step 7: Генерация SKU

Используйте `defaultVariantId` из Step 5.

```
POST /api/v1/catalog/products/{productId}/variants/{defaultVariantId}/skus/generate
Authorization: Bearer <accessToken>
```

### Request

```json
{
  "attributeSelections": [
    { "attributeId": "size-uuid", "valueIds": ["s-uuid", "m-uuid", "l-uuid"] },
    { "attributeId": "color-uuid", "valueIds": ["white-uuid", "black-uuid"] }
  ],
  "priceAmount": 5000,
  "priceCurrency": "RUB",
  "isActive": true
}
```

Только `level: "variant"` атрибуты. Бэкенд строит cartesian product (3×2 = 6 SKU).
`priceCurrency` — опциональное, default: `"RUB"`.

> **`priceAmount` обязателен для публикации.** Если `null` → SKU создаются без цены → продукт нельзя перевести в PUBLISHED.

### Response (201)

```json
{
  "createdCount": 6,
  "skippedCount": 0,
  "skuIds": ["uuid", "uuid", "uuid", "uuid", "uuid", "uuid"],
  "message": "Generated 6 SKUs, skipped 0 existing"
}
```

SKU code генерируется автоматически (`{slug}-001`, `{slug}-002`...). Дубликаты пропускаются (`skippedCount`).

---

## Step 8: Загрузка медиа

### 8a. Зарезервировать upload slot

```
POST /api/v1/catalog/products/{productId}/media/upload
{ "mediaType": "image", "role": "main", "contentType": "image/jpeg", "sortOrder": 0, "variantId": null }
→ 201 { "id": "media-uuid", "presignedUploadUrl": "https://s3...", "objectKey": "..." }
```

### 8b. Загрузить файл на S3

```
PUT {presignedUploadUrl}
Content-Type: image/jpeg
Body: <raw file bytes>
```

### 8c. Подтвердить загрузку

```
POST /api/v1/catalog/products/{productId}/media/{mediaId}/confirm
→ 202 Accepted { "message": "Upload confirmed, processing started" }
```

**Типы медиа (`mediaType`):** `image` | `video` | `model_3d` | `document`
**Роли медиа (`role`):** `main` | `hover` | `gallery` | `hero_video` | `size_guide` | `packaging`
**`variantId`** — опциональный, привязывает медиа к конкретному варианту (null = к продукту целиком).
**`objectKey`** — S3 ключ, нужен только для отладки, фронтенд может игнорировать.

> Минимум одно медиа с ролью `main` требуется для публикации продукта.

---

## Step 9: Смена статуса (FSM)

```
PATCH /api/v1/catalog/products/{productId}/status
{ "status": "enriching" }
```

### Допустимые переходы

```
DRAFT → ENRICHING → READY_FOR_REVIEW → PUBLISHED → ARCHIVED
                                                         ↓
ARCHIVED → DRAFT (вернуть в работу)
ENRICHING → DRAFT (откатить)
READY_FOR_REVIEW → ENRICHING (вернуть на доработку)
```

### Предусловия

**Для READY_FOR_REVIEW:**

- Минимум 1 активный SKU

**Для PUBLISHED:**

- Минимум 1 активный SKU с ценой (`priceAmount > 0`)
- Минимум 1 медиа-ассет

### Errors

| Status | Code                        | Meaning                                                                                 |
| ------ | --------------------------- | --------------------------------------------------------------------------------------- |
| 422    | `INVALID_STATUS_TRANSITION` | Недопустимый переход (e.g., DRAFT → PUBLISHED)                                          |
| 422    | `PRODUCT_NOT_READY`         | Нет активных SKU (для READY_FOR_REVIEW) или нет SKU с ценой / нет медиа (для PUBLISHED) |

> **Response:** PATCH status возвращает полный `ProductResponse` с variants, SKUs, attributes.

---

## Как рендерить UI

### По `uiType`

| `uiType`       | Компонент                      | `metaData`                 |
| -------------- | ------------------------------ | -------------------------- |
| `text_button`  | Кнопки с текстом (S, M, L, XL) | —                          |
| `color_swatch` | Цветные кружки                 | `metaData.hex` → цвет фона |
| `dropdown`     | Select/Dropdown                | —                          |
| `checkbox`     | Чекбоксы (single-select пока)  | —                          |
| `range_slider` | Слайдер (для числовых)         | —                          |

### По `level` — КРИТИЧЕСКИ ВАЖНО

| Level     | UX в форме                                                       | API endpoint                          |
| --------- | ---------------------------------------------------------------- | ------------------------------------- |
| `product` | **Single select** — одно значение на атрибут                     | `POST /products/{id}/attributes/bulk` |
| `variant` | **Multi select** — несколько значений (все нужные размеры/цвета) | `POST .../skus/generate`              |

### По `requirementLevel`

| Level         | UI                   | Validation            |
| ------------- | -------------------- | --------------------- |
| `required`    | Красная звёздочка \* | Блокирует сохранение  |
| `recommended` | Жёлтый индикатор     | Warning, не блокирует |
| `optional`    | Обычное поле         | Без валидации         |

---

## SKU Price Resolution

SKU может не иметь собственной цены — тогда используется `defaultPrice` варианта.

```
Effective price = sku.price ?? variant.defaultPrice ?? null
```

В response SKU есть поле `resolvedPrice` — это вычисленная итоговая цена.

---

## Optimistic Locking

Product и SKU имеют поле `version` (integer, начинается с 1).

**В PATCH запросах `version` — опциональное поле:**

- `PATCH /products/{id}` — `{ ..., "version": 3 }` (опционально)
- `PATCH .../skus/{id}` — `{ ..., "version": 2 }` (опционально)

**Поведение:**

- Если `version` передан → бэкенд проверяет что version в БД совпадает
- Если не совпадает → `409 CONCURRENCY_ERROR`
- Если `version` не передан → обновление без проверки конкурентности
- Frontend должен перезагрузить данные и повторить при 409

---

## Полный пример реализации

```typescript
// ═══ Step 1-2: Категория → атрибуты ═══

const { groups } = await api.get(
  `/catalog/storefront/categories/${categoryId}/form-attributes`,
);

const allAttrs = groups.flatMap((g) => g.attributes);
const productAttrs = allAttrs.filter((a) => a.level === 'product');
const variantAttrs = allAttrs.filter((a) => a.level === 'variant');

// Если groups пуст — у категории нет family, атрибутов нет

// ═══ Step 3-4: Форма ═══
// Секция A: основные поля (title, slug, brand...)
// Секция B: product-level (single select per attr)
// Секция C: variant-level (multi-select — какие размеры? какие цвета?)

// ═══ Step 5: Создать продукт ═══

const { id: productId, defaultVariantId } = await api.post(
  '/catalog/products',
  {
    titleI18n: { ru: 'Nike Air Force 1', en: 'Nike Air Force 1' },
    slug: 'nike-air-force-1',
    brandId: nikeBrandId,
    primaryCategoryId: categoryId,
  },
);
// defaultVariantId — использовать в Step 7, НЕ создавать variant вручную!

// ═══ Step 6: Bulk assign product attrs ═══

await api.post(`/catalog/products/${productId}/attributes/bulk`, {
  items: productAttrs
    .filter((attr) => selectedProductAttrs[attr.attributeId])
    .map((attr) => ({
      attributeId: attr.attributeId,
      attributeValueId: selectedProductAttrs[attr.attributeId],
    })),
});

// ═══ Step 7: Generate SKU matrix ═══

const skuResult = await api.post(
  `/catalog/products/${productId}/variants/${defaultVariantId}/skus/generate`,
  {
    attributeSelections: variantAttrs.map((attr) => ({
      attributeId: attr.attributeId,
      valueIds: selectedVariantValues[attr.attributeId],
    })),
    priceAmount: 5000,
    priceCurrency: 'RUB',
  },
);
// → { createdCount: 6, skippedCount: 0, skuIds: [...] }

// ═══ Step 8: Upload media ═══

const { presignedUploadUrl, id: mediaId } = await api.post(
  `/catalog/products/${productId}/media/upload`,
  { mediaType: 'image', role: 'main', contentType: 'image/jpeg', sortOrder: 0 },
);
await fetch(presignedUploadUrl, { method: 'PUT', body: imageFile });
await api.post(`/catalog/products/${productId}/media/${mediaId}/confirm`);

// ═══ Step 9: Publish ═══

await api.patch(`/catalog/products/${productId}/status`, {
  status: 'enriching',
});
// ... после review ...
await api.patch(`/catalog/products/${productId}/status`, {
  status: 'published',
});
```

---

## TypeScript Interfaces

```typescript
// GET /catalog/storefront/categories/{id}/form-attributes
interface FormAttributesResponse {
  categoryId: string;
  groups: FormGroup[];
}

interface FormGroup {
  groupId: string | null;
  groupCode: string | null;
  groupNameI18n: Record<string, string>;
  groupSortOrder: number;
  attributes: FormAttribute[];
}

interface FormAttribute {
  attributeId: string;
  code: string;
  slug: string;
  nameI18n: Record<string, string>;
  descriptionI18n: Record<string, string>;
  dataType: 'string' | 'integer' | 'float' | 'boolean';
  uiType:
    | 'text_button'
    | 'color_swatch'
    | 'dropdown'
    | 'checkbox'
    | 'range_slider';
  isDictionary: boolean;
  level: 'product' | 'variant';
  requirementLevel: 'required' | 'recommended' | 'optional';
  validationRules: ValidationRules | null; // keys are snake_case!
  values: AttributeValue[];
  sortOrder: number;
}

interface AttributeValue {
  id: string;
  code: string;
  slug: string;
  valueI18n: Record<string, string>;
  metaData: Record<string, unknown>;
  valueGroup: string | null;
  sortOrder: number;
}

// Note: keys inside validationRules are snake_case (raw JSONB, not CamelModel)
interface ValidationRules {
  min_length?: number;
  max_length?: number;
  pattern?: string;
  min_value?: number;
  max_value?: number;
}

// POST /catalog/products
interface CreateProductResponse {
  id: string;
  defaultVariantId: string;
  message: string;
}

// POST /catalog/products/{id}/attributes/bulk
interface BulkAssignRequest {
  items: Array<{ attributeId: string; attributeValueId: string }>;
}

interface BulkAssignResponse {
  assignedCount: number;
  pavIds: string[];
  message: string;
}

// POST /catalog/products/{id}/attributes (single)
interface AssignAttributeRequest {
  attributeId: string;
  attributeValueId: string;
}

// POST .../skus/generate
interface SKUMatrixGenerateRequest {
  attributeSelections: Array<{
    attributeId: string;
    valueIds: string[];
  }>;
  priceAmount: number | null;
  priceCurrency: string;
  compareAtPriceAmount?: number | null;
  isActive?: boolean;
}

interface SKUMatrixGenerateResponse {
  createdCount: number;
  skippedCount: number;
  skuIds: string[];
  message: string;
}

// GET /catalog/products/{id}/attributes
interface ProductAttribute {
  id: string;
  productId: string;
  attributeId: string;
  attributeValueId: string;
  attributeCode: string;
  attributeNameI18n: Record<string, string>;
  attributeValueCode: string;
  attributeValueNameI18n: Record<string, string>; // e.g. { ru: "Хлопок", en: "Cotton" }
}

// SKU in product response
interface SKUResponse {
  id: string;
  productId: string;
  variantId: string;
  skuCode: string;
  price: MoneySchema | null;
  resolvedPrice: MoneySchema | null; // effective price (sku.price ?? variant.defaultPrice)
  compareAtPrice: MoneySchema | null;
  isActive: boolean;
  version: number;
  variantAttributes: Array<{ attributeId: string; attributeValueId: string }>;
  createdAt: string; // ISO 8601 datetime
  updatedAt: string; // ISO 8601 datetime
}

interface MoneySchema {
  amount: number; // в мин. единицах валюты (копейки)
  currency: string; // ISO 4217 (RUB, USD...)
}
```

---

## Error Reference

Все ошибки возвращаются как:

```json
{
  "detail": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {}
  }
}
```

### HTTP Status → Exception mapping

| Status | Base class                 | Meaning                                     |
| ------ | -------------------------- | ------------------------------------------- |
| 404    | `NotFoundError`            | Ресурс не найден                            |
| 409    | `ConflictError`            | Конфликт (дубликат, concurrency)            |
| 422    | `UnprocessableEntityError` | Невалидные данные / бизнес-правило нарушено |

### Product attribute errors

| Code                          | Status | Когда                                                 |
| ----------------------------- | ------ | ----------------------------------------------------- |
| `PRODUCT_NOT_FOUND`           | 404    | Продукт не найден                                     |
| `ATTRIBUTE_NOT_FOUND`         | 404    | Атрибут не найден                                     |
| `ATTRIBUTE_VALUE_NOT_FOUND`   | 404    | Значение не найдено                                   |
| `ATTRIBUTE_NOT_DICTIONARY`    | 422    | Не словарный атрибут                                  |
| `ATTRIBUTE_NOT_IN_FAMILY`     | 422    | Атрибут не входит в Family категории                  |
| `ATTRIBUTE_LEVEL_MISMATCH`    | 422    | Уровень атрибута не `product` (передан variant-level) |
| `DUPLICATE_PRODUCT_ATTRIBUTE` | 409    | Уже присвоен                                          |

### Product status errors

| Code                        | Status | Когда                         |
| --------------------------- | ------ | ----------------------------- |
| `INVALID_STATUS_TRANSITION` | 422    | Недопустимый переход статуса  |
| `PRODUCT_NOT_READY`         | 422    | Нет SKU с ценой или нет медиа |

### SKU errors

| Code                            | Status | Когда                                                 |
| ------------------------------- | ------ | ----------------------------------------------------- |
| `DUPLICATE_VARIANT_COMBINATION` | 409    | SKU с такой комбинацией атрибутов уже есть            |
| `SKU_CODE_CONFLICT`             | 409    | SKU code уже занят                                    |
| `VARIANT_NOT_FOUND`             | 404    | Вариант не найден                                     |
| `ATTRIBUTE_NOT_FOUND`           | 404    | Атрибут в `attributeSelections` не найден             |
| `ATTRIBUTE_VALUE_NOT_FOUND`     | 404    | Значение в `valueIds` не найдено                      |
| `ATTRIBUTE_NOT_IN_FAMILY`       | 422    | Атрибут не входит в Family категории                  |
| `ATTRIBUTE_LEVEL_MISMATCH`      | 422    | Уровень атрибута не `variant` (передан product-level) |
| `SKU_NOT_FOUND`                 | 404    | SKU не найден (для update/delete)                     |

### General

| Code                | Status | Когда                                          |
| ------------------- | ------ | ---------------------------------------------- |
| `CONCURRENCY_ERROR` | 409    | Optimistic locking conflict (version mismatch) |

---

## Admin Panel: AttributeFamily

### Концепция

```
AttributeFamily → определяет КАКИЕ атрибуты нужны (бизнес-правило)
AttributeGroup  → определяет ГДЕ показать в UI (визуальная секция)
Category.familyId → связывает категорию с Family
```

### Endpoints

**Family CRUD:**

```
POST   /api/v1/catalog/attribute-families
GET    /api/v1/catalog/attribute-families
GET    /api/v1/catalog/attribute-families/tree
GET    /api/v1/catalog/attribute-families/{id}
PATCH  /api/v1/catalog/attribute-families/{id}
DELETE /api/v1/catalog/attribute-families/{id}
```

**Family Bindings:**

```
POST   .../attribute-families/{id}/attributes
GET    .../attribute-families/{id}/attributes
GET    .../attribute-families/{id}/attributes/effective
PATCH  .../attribute-families/{id}/attributes/{bid}
DELETE .../attribute-families/{id}/attributes/{bid}
POST   .../attribute-families/{id}/attributes/reorder
```

**Family Exclusions:**

```
POST   .../attribute-families/{id}/exclusions
GET    .../attribute-families/{id}/exclusions
DELETE .../attribute-families/{id}/exclusions/{eid}
```

**Category → Family:**

```json
PATCH /api/v1/catalog/categories/{id}
{ "familyId": "uuid" }   // null — убрать привязку
```

---

## Full Catalog API Reference

Помимо creation flow, бэкенд предоставляет полный CRUD для всех сущностей.

### Products

```
POST   /api/v1/catalog/products                          — создать (Step 5)
GET    /api/v1/catalog/products                          — список (paginated, фильтры: status, brandId)
GET    /api/v1/catalog/products/{id}                     — получить с variants/SKUs/attributes
PATCH  /api/v1/catalog/products/{id}                     — обновить (version для optimistic locking)
DELETE /api/v1/catalog/products/{id}                     — soft-delete (204)
PATCH  /api/v1/catalog/products/{id}/status              — сменить статус (Step 9)
```

### Product Attributes

```
POST   /api/v1/catalog/products/{id}/attributes          — присвоить один (level: product only)
POST   /api/v1/catalog/products/{id}/attributes/bulk     — bulk assign (Step 6)
GET    /api/v1/catalog/products/{id}/attributes          — список присвоенных
DELETE /api/v1/catalog/products/{id}/attributes/{attrId} — удалить привязку
```

### Variants

```
POST   /api/v1/catalog/products/{id}/variants            — создать (обычно не нужно — default auto-created)
GET    /api/v1/catalog/products/{id}/variants            — список
PATCH  /api/v1/catalog/products/{id}/variants/{vid}      — обновить
DELETE /api/v1/catalog/products/{id}/variants/{vid}      — soft-delete
```

### SKUs

```
POST   .../variants/{vid}/skus                           — создать один SKU
POST   .../variants/{vid}/skus/generate                  — bulk generate (Step 7)
GET    .../variants/{vid}/skus                           — список
PATCH  .../variants/{vid}/skus/{sid}                     — обновить (price, is_active, sku_code)
DELETE .../variants/{vid}/skus/{sid}                     — soft-delete
```

### Media

```
POST   /api/v1/catalog/products/{id}/media/upload        — reserve slot (Step 8a)
POST   /api/v1/catalog/products/{id}/media/{mid}/confirm — confirm (Step 8c)
POST   /api/v1/catalog/products/{id}/media/external      — add external URL (YouTube, etc.)
GET    /api/v1/catalog/products/{id}/media               — список
DELETE /api/v1/catalog/products/{id}/media/{mid}         — удалить
```

### Storefront (read-only, mixed auth)

```
GET    /api/v1/catalog/storefront/categories/{id}/form-attributes       — [catalog:manage] form для создания
GET    /api/v1/catalog/storefront/categories/{id}/filters               — [public] фильтры для каталога
GET    /api/v1/catalog/storefront/categories/{id}/card-attributes       — [public] атрибуты для карточки товара
GET    /api/v1/catalog/storefront/categories/{id}/comparison-attributes — [public] атрибуты для сравнения
```

### CORS

```
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
Allowed headers: Authorization, Content-Type, X-Request-ID
```
