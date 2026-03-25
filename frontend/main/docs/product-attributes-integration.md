# Product Creation — Attribute & AttributeFamily Integration Guide

## Architecture

Атрибуты продуктов управляются через систему **AttributeFamily** (семья атрибутов).

```
AttributeFamily "Одежда"
├── clothing_size (optional)    ← наследуется всеми дочерними
│
└── AttributeFamily "Футболки" (extends "Одежда")
    ├── clothing_size (→ required)   ← переопределён
    └── material (recommended)       ← добавлен
```

**Как это работает:**
- `AttributeFamily` определяет набор атрибутов для группы продуктов
- Семьи образуют иерархию: дочерняя наследует атрибуты родительской
- Дочерняя может: добавить свои, переопределить настройки, исключить ненужные
- `Category` ссылается на `AttributeFamily` через поле `familyId`
- Один storefront endpoint возвращает **effective** (resolved) атрибуты для категории

---

## Flow создания продукта

```
Step 1: Выбрать категорию          GET /catalog/categories/tree
Step 2: Выбрать бренд              GET /catalog/brands
Step 3: Заполнить основные поля    (title, slug, description...)
Step 4: Создать продукт            POST /catalog/products
          ↓ получаем productId
Step 5: Загрузить атрибуты формы   GET /catalog/storefront/categories/{categoryId}/form-attributes
          ↓ бэкенд: category → familyId → resolve effective attrs
Step 6: Присвоить атрибуты         POST /catalog/products/{productId}/attributes  (per attribute)
Step 7: Создать варианты/SKU       POST .../variants, .../skus
Step 8: Загрузить медиа            POST .../media/upload → S3 → confirm
Step 9: Сменить статус             PATCH /catalog/products/{productId}/status
```

> **Важно:** Если у категории нет `familyId` — Step 5 вернёт пустой список атрибутов. Продукт можно создать без атрибутов.

---

## Step 5: Получить атрибуты для формы

### Endpoint

```
GET /api/v1/catalog/storefront/categories/{categoryId}/form-attributes
Authorization: Bearer <accessToken>
```

**Permission:** `catalog:manage`

**Что происходит на бэкенде:**
1. Загружается категория → берётся `familyId`
2. Если `familyId = null` → возвращается пустой `groups: []`
3. По `familyId` строится цепочка предков (root → ... → parent → self)
4. Для каждой семьи в цепочке: сначала exclusions, потом bindings (overrides)
5. Результат — **effective** набор атрибутов с полной метадатой

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
          "dataType": "string",            // string | integer | float | boolean
          "uiType": "text_button",         // КАК рендерить (см. таблицу ниже)
          "isDictionary": true,            // true = выбор из values[], false = free input
          "level": "variant",              // product | variant
          "requirementLevel": "required",  // required | recommended | optional
          "validationRules": null,
          "values": [
            {
              "id": "uuid",
              "code": "s",
              "slug": "s",
              "valueI18n": { "en": "S", "ru": "S" },
              "metaData": {},
              "valueGroup": null,
              "sortOrder": 3
            },
            {
              "id": "uuid",
              "code": "m",
              "slug": "m",
              "valueI18n": { "en": "M", "ru": "M" },
              "metaData": {},
              "valueGroup": null,
              "sortOrder": 4
            }
          ],
          "sortOrder": 1
        }
      ]
    }
  ]
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
  "attributeId": "uuid",        // из form-attributes response → attributeId
  "attributeValueId": "uuid"    // из form-attributes response → values[].id
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

- Один атрибут = одно значение на продукт. Повторное присвоение → **409** (`DUPLICATE_PRODUCT_ATTRIBUTE`)
- Только dictionary-атрибуты (`isDictionary: true`). Non-dictionary → **400** (`ATTRIBUTE_NOT_DICTIONARY`)
- `attributeValueId` должен принадлежать `attributeId`, иначе → **404**

### Errors

| Status | Code | Meaning |
|--------|------|---------|
| 404 | `PRODUCT_NOT_FOUND` | Продукт не найден |
| 404 | `ATTRIBUTE_NOT_FOUND` | Атрибут не найден |
| 404 | `ATTRIBUTE_VALUE_NOT_FOUND` | Значение не найдено или не принадлежит атрибуту |
| 400 | `ATTRIBUTE_NOT_DICTIONARY` | Атрибут не словарный |
| 409 | `DUPLICATE_PRODUCT_ATTRIBUTE` | Атрибут уже присвоен |

---

## Удаление / Просмотр атрибутов продукта

```
DELETE /api/v1/catalog/products/{productId}/attributes/{attributeId}
→ 204 No Content

GET /api/v1/catalog/products/{productId}/attributes?limit=50&offset=0
→ 200 { items: [...], total, offset, limit }
```

---

## Как рендерить UI

### По `uiType`

| `uiType` | Компонент | `metaData` |
|-----------|-----------|------------|
| `text_button` | Кнопки с текстом (S, M, L, XL) | — |
| `color_swatch` | Цветные кружки | `metaData.hex` → цвет фона |
| `dropdown` | Select/Dropdown | — |
| `checkbox` | Чекбоксы (single-select пока) | — |
| `range_slider` | Слайдер (для числовых) | — |

### По `dataType`

| `dataType` | `isDictionary: true` | `isDictionary: false` |
|------------|----------------------|----------------------|
| `string` | Выбор из `values[]` | Text input |
| `integer` | Выбор из `values[]` | Number input (целое) |
| `float` | Выбор из `values[]` | Number input (дробное) |
| `boolean` | Выбор из `values[]` | Toggle/switch |

### По `level`

| Level | Meaning | Frontend |
|-------|---------|----------|
| `product` | Одинаков для всех SKU | Показать на шаге атрибутов |
| `variant` | Разный для каждого SKU | Показать при создании SKU |

### По `requirementLevel`

| Level | UI | Validation |
|-------|-----|------------|
| `required` | Красная звёздочка * | Блокирует сохранение |
| `recommended` | Жёлтый индикатор | Warning, не блокирует |
| `optional` | Обычное поле | Без валидации |

---

## Validation Rules (non-dictionary атрибуты)

```typescript
interface ValidationRules {
  min_length?: number;     // string
  max_length?: number;     // string
  pattern?: string;        // string (regex)
  min_value?: number;      // integer/float
  max_value?: number;      // integer/float
}
```

---

## Пример реализации

```typescript
// 1. Загрузить атрибуты после выбора категории
const { groups } = await api.get(
  `/catalog/storefront/categories/${categoryId}/form-attributes`
);

// 2. Если groups пуст — у категории нет familyId, атрибутов нет
if (groups.length === 0) {
  // Пропустить шаг атрибутов
}

// 3. Отрендерить форму по группам
groups.forEach(group => {
  // Заголовок секции: group.groupNameI18n[locale]
  group.attributes.forEach(attr => {
    // Рендерить по attr.uiType + attr.isDictionary
    // Label: attr.nameI18n[locale]
    // Если isDictionary — показать attr.values как варианты
    // requirementLevel → обязательность
  });
});

// 4. При сабмите — отправить параллельно
const results = await Promise.allSettled(
  selectedAttributes.map(([attributeId, attributeValueId]) =>
    api.post(`/catalog/products/${productId}/attributes`, {
      attributeId,
      attributeValueId,
    })
  )
);

// 5. Показать ошибки по конкретным атрибутам
results.forEach((result, i) => {
  if (result.status === 'rejected') {
    showError(selectedAttributes[i][0], result.reason);
  }
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
  dataType: "string" | "integer" | "float" | "boolean";
  uiType: "text_button" | "color_swatch" | "dropdown" | "checkbox" | "range_slider";
  isDictionary: boolean;
  level: "product" | "variant";
  requirementLevel: "required" | "recommended" | "optional";
  validationRules: ValidationRules | null;
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

interface ValidationRules {
  min_length?: number;
  max_length?: number;
  pattern?: string;
  min_value?: number;
  max_value?: number;
}

// POST /catalog/products/{id}/attributes
interface AssignAttributeRequest {
  attributeId: string;
  attributeValueId: string;
}

interface AssignAttributeResponse {
  id: string;
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
}
```

---

## Admin Panel: AttributeFamily Management

### Концепция

```
AttributeFamily — определяет КАКИЕ атрибуты нужны продуктам.
AttributeGroup  — определяет ГДЕ показывать атрибуты в UI (визуальная группировка).
Category        — ссылается на Family через familyId.
```

### Family CRUD

```
POST   /api/v1/catalog/attribute-families          — создать
GET    /api/v1/catalog/attribute-families          — список
GET    /api/v1/catalog/attribute-families/tree     — дерево
GET    /api/v1/catalog/attribute-families/{id}     — получить
PATCH  /api/v1/catalog/attribute-families/{id}     — обновить
DELETE /api/v1/catalog/attribute-families/{id}     — удалить
```

### Create Family

```typescript
// Корневая семья
const clothing = await api.post('/catalog/attribute-families', {
  code: 'clothing',              // unique, immutable, ^[a-z0-9_]+$
  nameI18n: { ru: 'Одежда', en: 'Clothing' },
  descriptionI18n: { ru: '...' },
  sortOrder: 0,
});
// → { id: "uuid", message: "Attribute family created" }

// Дочерняя семья (наследует атрибуты родителя)
const tshirts = await api.post('/catalog/attribute-families', {
  code: 't_shirts',
  parentId: clothing.id,           // ← parent family
  nameI18n: { ru: 'Футболки', en: 'T-shirts' },
});
```

### Family Attribute Bindings

```
POST   .../attribute-families/{id}/attributes              — привязать
GET    .../attribute-families/{id}/attributes              — свои привязки
GET    .../attribute-families/{id}/attributes/effective    — resolved (с наследованием)
PATCH  .../attribute-families/{id}/attributes/{bid}       — обновить
DELETE .../attribute-families/{id}/attributes/{bid}       — удалить
POST   .../attribute-families/{id}/attributes/reorder     — переупорядочить
```

```typescript
// Привязать атрибут
await api.post(`/catalog/attribute-families/${clothing.id}/attributes`, {
  attributeId: sizeAttrId,
  sortOrder: 1,
  requirementLevel: 'optional',    // required | recommended | optional
  flagOverrides: null,             // { isFilterable: true } — переопределить флаги
  filterSettings: null,
});

// Получить effective атрибуты (с наследованием)
const effective = await api.get(
  `/catalog/attribute-families/${tshirts.id}/attributes/effective`
);
// → { familyId, attributes: [{ attributeId, code, requirementLevel, sourceFamilyId, ... }] }
```

### Effective Attributes Response

```typescript
interface EffectiveAttributeSetResponse {
  familyId: string;
  attributes: EffectiveAttribute[];
}

interface EffectiveAttribute {
  attributeId: string;
  code: string;
  slug: string;
  nameI18n: Record<string, string>;
  descriptionI18n: Record<string, string>;
  dataType: string;
  uiType: string;
  isDictionary: boolean;
  level: string;
  requirementLevel: string;
  validationRules: Record<string, unknown> | null;
  flagOverrides: Record<string, unknown> | null;
  filterSettings: Record<string, unknown> | null;
  sourceFamilyId: string;     // откуда унаследован
  isOverridden: boolean;       // переопределён ли дочерней семьёй
  values: AttributeValue[];
  sortOrder: number;
}
```

### Family Attribute Exclusions

```
POST   .../attribute-families/{id}/exclusions              — исключить
GET    .../attribute-families/{id}/exclusions              — список
DELETE .../attribute-families/{id}/exclusions/{eid}        — отменить
```

```typescript
// Исключить унаследованный атрибут (например, цвет не нужен для "Спортивных футболок")
await api.post(`/catalog/attribute-families/${sportTshirts.id}/exclusions`, {
  attributeId: colorAttrId,
});
```

### Назначить Family категории

```typescript
// PATCH /api/v1/catalog/categories/{id}
await api.patch(`/catalog/categories/${categoryId}`, {
  familyId: tshirts.id,    // null — убрать привязку
});
```

Теперь `GET .../storefront/categories/{categoryId}/form-attributes` вернёт effective атрибуты этой Family.

---

## Полный пример: настройка каталога

```typescript
// ═══ 1. Создать семьи ═══

const clothing = await api.post('/catalog/attribute-families', {
  code: 'clothing',
  nameI18n: { ru: 'Одежда', en: 'Clothing' },
});

// ═══ 2. Привязать атрибут "Размер одежды" ═══

await api.post(`/catalog/attribute-families/${clothing.id}/attributes`, {
  attributeId: clothingSizeId,    // clothing_size [XXS-5XL]
  sortOrder: 1,
  requirementLevel: 'optional',
});

// ═══ 3. Назначить семью категории "Одежда" ═══

await api.patch(`/catalog/categories/${clothingCategoryId}`, {
  familyId: clothing.id,
});

// ═══ 4. Теперь все дочерние категории (Футболки, Худи...) ═══
// ═══ наследуют clothing_size через family ═══

// При создании продукта в "Футболки":
const formAttrs = await api.get(
  `/catalog/storefront/categories/${tshirtsCategoryId}/form-attributes`
);
// → groups[0].attributes[0] = { code: "clothing_size", values: [XXS..5XL] }

// Присвоить размер продукту:
await api.post(`/catalog/products/${productId}/attributes`, {
  attributeId: clothingSizeId,
  attributeValueId: sizeM_ValueId,  // значение "M"
});
```

---

## Response Format

Все backend ответы используют **camelCase** (настроено через `CamelModel`). Трансформация ключей на фронте не нужна.

## CORS

```
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

Allowed headers: `Authorization`, `Content-Type`, `X-Request-ID`
