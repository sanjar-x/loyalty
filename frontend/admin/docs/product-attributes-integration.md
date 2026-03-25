# Product Creation — Attribute Assignment Integration Guide

## Context

Фронтенд уже реализовал:

- [x] Category tree (`GET /catalog/categories/tree`)
- [x] Brand selection (`GET /catalog/brands`)
- [ ] **Attribute assignment** ← этот документ

> **Architecture update (2026-03-25):** Бэкенд перешёл на систему `AttributeFamily` вместо прямой привязки атрибутов к категориям. Категория теперь ссылается на `AttributeFamily` через поле `familyId`. Семьи (families) образуют иерархию с наследованием атрибутов: дочерняя семья наследует атрибуты родительской, может переопределять настройки и исключать унаследованные атрибуты. **Для фронтенда storefront API не изменился** — те же endpoints, те же response formats. Изменения касаются только admin panel (новые endpoints для управления семьями).

После того как пользователь выбрал **категорию** и **бренд**, следующий шаг — запросить атрибуты этой категории и дать пользователю заполнить их.

---

## Общий Flow создания продукта

```
Step 1: Выбрать категорию          GET /catalog/categories/tree
Step 2: Загрузить атрибуты формы   GET .../storefront/categories/{categoryId}/form-attributes
          ↓ показать форму с атрибутами сразу
Step 3: Выбрать бренд              GET /catalog/brands
Step 4: Заполнить ВСЮ форму       (основные поля + product attrs + variant selections)
Step 5: Создать продукт            POST /catalog/products  → productId
Step 6: Bulk-присвоить attrs       POST /products/{id}/attributes/bulk
        (product-level, одним запросом)
Step 7: Создать variant + SKU      POST .../variants + POST .../skus/generate
        (variant-level, бэкенд генерирует комбинации)
Step 8: Загрузить медиа            POST .../media/upload → S3 → confirm
Step 9: Сменить статус             PATCH .../products/{id}/status
```

> **Ключевые принципы:**
>
> - Атрибуты формы загружаются **сразу после выбора категории** (Step 2), не после создания продукта
> - `level: "product"` → bulk assign одним запросом `POST /products/{id}/attributes/bulk`
> - `level: "variant"` → `POST .../skus/generate` (бэкенд генерирует SKU комбинации)
> - Бэкенд **валидирует** что присваиваемые атрибуты входят в Family категории

---

## Step 5: Получить атрибуты для формы

### Endpoint

```
GET /api/v1/catalog/storefront/categories/{categoryId}/form-attributes
Authorization: Bearer <accessToken>
```

**Permission:** `catalog:manage`

### Response

```jsonc
{
  "categoryId": "uuid",
  "groups": [
    {
      "groupId": "uuid | null", // null = атрибуты без группы
      "groupCode": "physical | null",
      "groupNameI18n": { "en": "Physical", "ru": "Физические" },
      "groupSortOrder": 0,
      "attributes": [
        {
          "attributeId": "uuid",
          "code": "color", // уникальный код атрибута
          "slug": "color",
          "nameI18n": { "en": "Color", "ru": "Цвет" },
          "descriptionI18n": { "en": "Product color" },
          "dataType": "string", // string | integer | float | boolean
          "uiType": "color_swatch", // КАК рендерить (см. таблицу ниже)
          "isDictionary": true, // true = выбор из values[], false = free input
          "level": "variant", // product | variant
          "requirementLevel": "required", // required | recommended | optional
          "validationRules": null, // или { "min_length": 1, "max_length": 100 }
          "values": [
            // только если isDictionary = true
            {
              "id": "uuid", // ← это attributeValueId для assign
              "code": "red",
              "slug": "red",
              "valueI18n": { "en": "Red", "ru": "Красный" },
              "metaData": { "hex": "#FF0000" }, // для color_swatch
              "valueGroup": "Warm tones", // опционально, для группировки в UI
              "sortOrder": 0,
            },
            {
              "id": "uuid",
              "code": "blue",
              "slug": "blue",
              "valueI18n": { "en": "Blue", "ru": "Синий" },
              "metaData": { "hex": "#0000FF" },
              "valueGroup": "Cool tones",
              "sortOrder": 1,
            },
          ],
          "sortOrder": 0,
        },
      ],
    },
  ],
}
```

---

## Step 6: Присвоить атрибут продукту

### Endpoint

```
POST /api/v1/catalog/products/{productId}/attributes
Authorization: Bearer <accessToken>
Content-Type: application/json
```

**Permission:** `catalog:manage`

### Request

```json
{
  "attributeId": "uuid", // из form-attributes response → attributeId
  "attributeValueId": "uuid" // из form-attributes response → values[].id
}
```

### Response (201)

```json
{
  "id": "uuid",
  "message": "Attribute assigned to product"
}
```

### Constraints

- Один атрибут = одно значение на продукт. Повторное присвоение того же `attributeId` → **409 Conflict** (`DUPLICATE_PRODUCT_ATTRIBUTE`)
- Только dictionary-атрибуты (`isDictionary: true`) могут быть присвоены. Non-dictionary → **400** (`ATTRIBUTE_NOT_DICTIONARY`)
- `attributeValueId` должен принадлежать указанному `attributeId`, иначе → **404**

### Errors

| Status | Code                          | Meaning                                        |
| ------ | ----------------------------- | ---------------------------------------------- |
| 404    | `PRODUCT_NOT_FOUND`           | Продукт не найден                              |
| 404    | `ATTRIBUTE_NOT_FOUND`         | Атрибут не найден                              |
| 404    | `ATTRIBUTE_VALUE_NOT_FOUND`   | Значение не найдёт или не принадлежит атрибуту |
| 400    | `ATTRIBUTE_NOT_DICTIONARY`    | Атрибут не словарный, нельзя присвоить value   |
| 409    | `DUPLICATE_PRODUCT_ATTRIBUTE` | Этот атрибут уже присвоен продукту             |

---

## Удаление атрибута с продукта

```
DELETE /api/v1/catalog/products/{productId}/attributes/{attributeId}
Authorization: Bearer <accessToken>
```

**Response:** 204 No Content

---

## Просмотр присвоенных атрибутов

```
GET /api/v1/catalog/products/{productId}/attributes?limit=50&offset=0
Authorization: Bearer <accessToken>
```

**Permission:** `catalog:read`

### Response

```json
{
  "items": [
    {
      "id": "uuid", // ID записи привязки
      "productId": "uuid",
      "attributeId": "uuid",
      "attributeValueId": "uuid",
      "attributeCode": "color",
      "attributeNameI18n": { "en": "Color", "ru": "Цвет" }
    }
  ],
  "total": 5,
  "offset": 0,
  "limit": 50
}
```

---

## Как рендерить UI по `uiType`

| `uiType`       | Компонент                                     | `metaData` use             |
| -------------- | --------------------------------------------- | -------------------------- |
| `text_button`  | Кнопки с текстом (как size selector: S, M, L) | —                          |
| `color_swatch` | Цветные кружки/квадраты                       | `metaData.hex` → цвет фона |
| `dropdown`     | Select/Dropdown (одиночный выбор)             | —                          |
| `checkbox`     | Чекбоксы (множественный выбор)\*              | —                          |
| `range_slider` | Слайдер диапазона (для числовых)              | —                          |

> \*Примечание: Текущий бэкенд поддерживает только одно значение на атрибут. Для `checkbox` реализуйте как single-select пока.

---

## Как рендерить по `dataType`

| `dataType` | Если `isDictionary: true` | Если `isDictionary: false` |
| ---------- | ------------------------- | -------------------------- |
| `string`   | Выбор из `values[]`       | Text input                 |
| `integer`  | Выбор из `values[]`       | Number input (целое)       |
| `float`    | Выбор из `values[]`       | Number input (дробное)     |
| `boolean`  | Выбор из `values[]`       | Toggle/switch              |

---

## Validation Rules (для non-dictionary атрибутов)

Когда `isDictionary: false`, поле `validationRules` содержит правила для input:

**String:**

```json
{ "min_length": 1, "max_length": 255, "pattern": "^[a-zA-Z0-9]+$" }
```

**Integer / Float:**

```json
{ "min_value": 0, "max_value": 10000 }
```

**Boolean:** нет правил

---

## `level`: product vs variant — КРИТИЧЕСКИ ВАЖНО

Атрибуты привязываются к **разным сущностям** в зависимости от `level`:

| Level     | Сущность                | Endpoint                                  | Когда                            |
| --------- | ----------------------- | ----------------------------------------- | -------------------------------- |
| `product` | `ProductAttributeValue` | `POST /products/{id}/attributes`          | Step 6 (после создания продукта) |
| `variant` | `SKU.variantAttributes` | `POST /products/{id}/variants/{vid}/skus` | Step 7 (при создании SKU)        |

**Пример — Nike Air Force 1:**

```
Product "Nike Air Force 1"
├── material = "leather"        ← product-level (POST /products/{id}/attributes)
├── style = "casual"            ← product-level (POST /products/{id}/attributes)
│
├── Variant "Standard"
│   ├── SKU "AF1-WHT-42"       ← variant-level: variantAttributes: [{size: 42}, {color: white}]
│   ├── SKU "AF1-WHT-43"       ← variant-level: variantAttributes: [{size: 43}, {color: white}]
│   └── SKU "AF1-BLK-42"       ← variant-level: variantAttributes: [{size: 42}, {color: black}]
```

### Как фронтенд должен разделить атрибуты

```typescript
const { groups } = await api.get(`.../form-attributes`);

// Собрать ВСЕ атрибуты из всех групп в плоский список
const allAttrs = groups.flatMap((g) => g.attributes);

// Разделить по level
const productAttrs = allAttrs.filter((a) => a.level === 'product');
const variantAttrs = allAttrs.filter((a) => a.level === 'variant');

// Step 6: product-level → POST /products/{id}/attributes
for (const attr of productAttrs) {
  if (userSelected[attr.attributeId]) {
    await api.post(`/products/${productId}/attributes`, {
      attributeId: attr.attributeId,
      attributeValueId: userSelected[attr.attributeId],
    });
  }
}

// Step 7: variant-level → bulk-генерация SKU на бэкенде
// Фронт отправляет ВЫБРАННЫЕ значения, бэкенд сам генерирует все комбинации
await api.post(`/products/${productId}/variants/${variantId}/skus/generate`, {
  attributeSelections: [
    { attributeId: sizeAttrId, valueIds: [sizeS, sizeM, sizeL] },
    { attributeId: colorAttrId, valueIds: [whiteId, blackId] },
  ],
  priceAmount: 15000,
  priceCurrency: 'RUB',
});
// → Backend создаёт 6 SKU (3×2) в одной транзакции, auto-generates skuCode
```

---

## `requirementLevel`: что показывать пользователю

| Level         | UI                                         | Validation               |
| ------------- | ------------------------------------------ | ------------------------ |
| `required`    | Красная звёздочка \*, блокирует сохранение | Обязательное поле        |
| `recommended` | Жёлтый индикатор, предупреждение           | Warning, но не блокирует |
| `optional`    | Обычное поле                               | Без валидации            |

---

## Пример реализации (pseudocode)

```typescript
// ═══ Step 1-2: Выбрать категорию → сразу загрузить атрибуты ═══

const { groups } = await api.get(
  `/catalog/storefront/categories/${categoryId}/form-attributes`,
);

const allAttrs = groups.flatMap((g) => g.attributes);
const productAttrs = allAttrs.filter((a) => a.level === 'product');
const variantAttrs = allAttrs.filter((a) => a.level === 'variant');

// ═══ Step 3-4: Показать полную форму ═══
// Секция A: основные поля (title, slug, brand...)
// Секция B: product-level атрибуты (material, style) — single select per attr
// Секция C: variant-level атрибуты (size, color) — multi-select (какие размеры/цвета)

// ═══ Step 5: Создать продукт ═══

const { id: productId } = await api.post('/catalog/products', {
  titleI18n: { ru: 'Nike Air Force 1' },
  slug: 'nike-air-force-1',
  brandId: nikeBrandId,
  primaryCategoryId: categoryId,
});

// ═══ Step 6: Bulk-присвоить product-level атрибуты (один запрос) ═══

await api.post(`/catalog/products/${productId}/attributes/bulk`, {
  items: productAttrs
    .filter((attr) => selectedProductAttrs[attr.attributeId])
    .map((attr) => ({
      attributeId: attr.attributeId,
      attributeValueId: selectedProductAttrs[attr.attributeId],
    })),
});
// → { assignedCount: 3, pavIds: [...], message: "Assigned 3 attributes" }
// Бэкенд валидирует что все атрибуты входят в Family категории!

// ═══ Step 7: Создать variant + bulk SKU (два запроса) ═══

const { id: variantId } = await api.post(
  `/catalog/products/${productId}/variants`,
  { nameI18n: { ru: 'Стандарт', en: 'Standard' } },
);

const skuResult = await api.post(
  `/catalog/products/${productId}/variants/${variantId}/skus/generate`,
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
```

> **Все bulk-операции атомарны:** Если один атрибут невалиден — откатывается вся транзакция. Бэкенд валидирует принадлежность атрибутов к Family категории.

---

## Полный TypeScript Interface

```typescript
// Response from GET /catalog/storefront/categories/{id}/form-attributes
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
  validationRules: ValidationRules | null;
  values: AttributeValue[];
  sortOrder: number;
}

interface AttributeValue {
  id: string; // ← используй как attributeValueId при assign
  code: string;
  slug: string;
  valueI18n: Record<string, string>;
  metaData: Record<string, unknown>; // e.g. { hex: "#FF0000" } for color_swatch
  valueGroup: string | null;
  sortOrder: number;
}

interface ValidationRules {
  min_length?: number; // string only
  max_length?: number; // string only
  pattern?: string; // string only (regex)
  min_value?: number; // integer/float only
  max_value?: number; // integer/float only
}

// Request to POST /catalog/products/{id}/attributes
interface AssignAttributeRequest {
  attributeId: string;
  attributeValueId: string;
}

// Response from POST
interface AssignAttributeResponse {
  id: string;
  message: string;
}

// Items from GET /catalog/products/{id}/attributes
interface ProductAttribute {
  id: string;
  productId: string;
  attributeId: string;
  attributeValueId: string;
  attributeCode: string;
  attributeNameI18n: Record<string, string>;
}
```

---

## Admin Panel: AttributeFamily Management (NEW)

Для admin panel доступны новые endpoints для управления семьями атрибутов.

### Family CRUD

```
POST   /api/v1/catalog/attribute-families          — создать семью
GET    /api/v1/catalog/attribute-families          — список (paginated)
GET    /api/v1/catalog/attribute-families/tree     — дерево семей
GET    /api/v1/catalog/attribute-families/{id}     — получить семью
PATCH  /api/v1/catalog/attribute-families/{id}     — обновить
DELETE /api/v1/catalog/attribute-families/{id}     — удалить
```

### Family Attribute Bindings

```
POST   /api/v1/catalog/attribute-families/{id}/attributes           — привязать атрибут
GET    /api/v1/catalog/attribute-families/{id}/attributes           — свои привязки
GET    /api/v1/catalog/attribute-families/{id}/attributes/effective — resolved с наследованием
PATCH  /api/v1/catalog/attribute-families/{id}/attributes/{bid}    — обновить привязку
DELETE /api/v1/catalog/attribute-families/{id}/attributes/{bid}    — удалить привязку
POST   /api/v1/catalog/attribute-families/{id}/attributes/reorder  — переупорядочить
```

### Family Attribute Exclusions

```
POST   /api/v1/catalog/attribute-families/{id}/exclusions              — исключить атрибут
GET    /api/v1/catalog/attribute-families/{id}/exclusions              — список исключений
DELETE /api/v1/catalog/attribute-families/{id}/exclusions/{eid}       — отменить исключение
```

### Category → Family Assignment

При создании/обновлении категории передаётся `familyId`:

```json
// PATCH /api/v1/catalog/categories/{id}
{ "familyId": "uuid-of-family" }
```

### Пример: создать иерархию семей

```typescript
// 1. Создать корневую семью "Одежда"
const clothing = await api.post('/catalog/attribute-families', {
  code: 'clothing',
  nameI18n: { ru: 'Одежда', en: 'Clothing' },
});

// 2. Привязать атрибуты к "Одежда"
await api.post(`/catalog/attribute-families/${clothing.id}/attributes`, {
  attributeId: sizeAttrId,
  requirementLevel: 'optional',
});
await api.post(`/catalog/attribute-families/${clothing.id}/attributes`, {
  attributeId: colorAttrId,
  requirementLevel: 'required',
});

// 3. Создать дочернюю семью "Футболки" (наследует size, color)
const tshirts = await api.post('/catalog/attribute-families', {
  code: 't_shirts',
  parentId: clothing.id,
  nameI18n: { ru: 'Футболки', en: 'T-shirts' },
});

// 4. Добавить собственный атрибут "Материал"
await api.post(`/catalog/attribute-families/${tshirts.id}/attributes`, {
  attributeId: materialAttrId,
  requirementLevel: 'recommended',
});

// 5. Переопределить size на required (было optional у родителя)
await api.post(`/catalog/attribute-families/${tshirts.id}/attributes`, {
  attributeId: sizeAttrId,
  requirementLevel: 'required',
});

// 6. Получить effective атрибуты (size:required, color:required, material:recommended)
const effective = await api.get(
  `/catalog/attribute-families/${tshirts.id}/attributes/effective`,
);

// 7. Назначить семью категории
await api.patch(`/catalog/categories/${tshirtCategoryId}`, {
  familyId: tshirts.id,
});
```
