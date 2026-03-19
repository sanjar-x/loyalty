# Categories Settings Page — Design Spec

**Date:** 2026-03-19
**Scope:** Admin settings page for managing product categories — full CRUD (without parent reassignment) + tree view UI + BFF API layer.

---

## 1. Backend API (existing)

All endpoints under `/api/v1/catalog/categories`:

| Method | Path | Auth | Request | Response |
|--------|------|------|---------|----------|
| GET | `/tree` | None | — | `CategoryTreeResponse[]` |
| GET | `/` | None | `?offset&limit` | `CategoryListResponse` |
| GET | `/{id}` | None | — | `CategoryResponse` |
| POST | `/` | `catalog:manage` | `CategoryCreateRequest` | `CategoryCreateResponse` |
| PATCH | `/{id}` | `catalog:manage` | `CategoryUpdateRequest` | `CategoryResponse` |
| DELETE | `/{id}` | `catalog:manage` | — | 204 |

**Schemas:**

CategoryCreateRequest: `{ name (2-255), slug (3-255, ^[a-z0-9-]+$), parent_id (uuid|null), sort_order (int, default 0) }`

CategoryUpdateRequest: `{ name?, slug?, sort_order? }` (at least one required)

CategoryTreeResponse: `{ id, name, slug, full_slug, level, sort_order, children: CategoryTreeResponse[] }`

CategoryResponse: `{ id, name, slug, full_slug, level, sort_order, parent_id }`

---

## 2. BFF Route Handlers

Frontend calls BFF, BFF proxies to backend with Bearer token from httpOnly cookie.

| Frontend Route | Method | Backend Target |
|---------------|--------|---------------|
| `/api/categories/tree` | GET | `GET /api/v1/catalog/categories/tree` |
| `/api/categories` | POST | `POST /api/v1/catalog/categories` |
| `/api/categories/[id]` | PATCH | `PATCH /api/v1/catalog/categories/{id}` |
| `/api/categories/[id]` | DELETE | `DELETE /api/v1/catalog/categories/{id}` |

All handlers use `backendFetch()` from `lib/api-client.js` and `getAccessToken()` from `lib/auth.js`. Mutations pass `Authorization: Bearer <token>`. Errors proxied as-is (backend error envelope: `{error: {code, message, details}}`).

**Key implementation notes:**

- **DELETE returns 204 (no body):** `backendFetch` calls `res.json()` which returns `null` for 204. The DELETE route handler checks `res.status === 204` and returns `{success: true}` to the client.
- **CamelCase → snake_case mapping:** Backend expects `parent_id` and `sort_order` (snake_case). The POST route handler transforms `{parentId, sortOrder}` → `{parent_id, sort_order}` before forwarding. PATCH sends `{name?, slug?, sort_order?}`.
- **Backend unavailable fallback:** If `backendFetch` returns `data === null` on error, route handlers return `{error: {code: 'SERVICE_UNAVAILABLE', message: 'Backend unavailable', details: {}}}` with status 502.
- **Paginated list endpoint** (`GET /api/v1/catalog/categories`) is intentionally excluded — the page uses only the tree endpoint.

**Note on existing mock data:** `src/data/productCategories.js` and `src/services/categories.js` are left as-is. They are used by the product add form (`findProductCategoryPath`). Future work will replace them with API calls.

---

## 3. File Structure

### New files (8)

| File | Type | Purpose |
|------|------|---------|
| `src/app/api/categories/tree/route.js` | Route Handler | Proxy GET tree |
| `src/app/api/categories/route.js` | Route Handler | Proxy POST create |
| `src/app/api/categories/[id]/route.js` | Route Handler | Proxy PATCH update, DELETE |
| `src/app/admin/settings/categories/page.jsx` | Page | Categories settings page |
| `src/components/admin/settings/categories/CategoryTree.jsx` | Component | Recursive tree renderer |
| `src/components/admin/settings/categories/CategoryNode.jsx` | Component | Single tree node |
| `src/components/admin/settings/categories/CategoryModal.jsx` | Component | Create/edit/delete modal |
| `src/components/admin/settings/categories/CategorySkeleton.jsx` | Component | Loading skeleton |

### Modified files (1)

| File | Change |
|------|--------|
| `src/app/admin/settings/layout.jsx` | Add "Категории" after "Бренды" in navItems |

---

## 4. UI Layout

### Page

```
┌─────────────────────────────────────────────────┐
│  Категории                   [+ Добавить]       │
├─────────────────────────────────────────────────┤
│  ▼ Одежда, обувь и аксессуары            [+][✎] │
│    ▼ Одежда                              [+][✎] │
│      • Футболки                          [+][✎] │
│      • Худи                              [+][✎] │
│    ▶ Обувь                               [+][✎] │
│  ▶ Электроника                           [+][✎] │
└─────────────────────────────────────────────────┘
```

- ▶/▼ toggles expand/collapse (client state, no API call)
- First level expanded by default, deeper levels collapsed
- [+] on node → create child modal (parent_id = node.id)
- [+ Добавить] button top-right → create root modal (parent_id = null)
- [✎] on node → edit modal (fields prefilled)
- Empty state: "Категории не добавлены" with "Добавить первую" button

### Modal (Create / Edit)

```
┌──────────────────────────────┐
│  Новая категория       [✕]   │
├──────────────────────────────┤
│  Название                    │
│  [___________________________]│
│                              │
│  Slug (URL)                  │
│  [___________________________]│
│                              │
│  Порядок сортировки          │
│  [__0________________________]│
│                              │
│  {error message if any}      │
│                              │
│  [       Сохранить          ]│
│                              │
│  [Удалить] (edit mode only)  │
└──────────────────────────────┘
```

- Title: "Новая категория" (create) / "Редактирование" (edit)
- Auto-slug: on name input, auto-generate slug. Since category names are typically Cyrillic, auto-slug only works as a hint for Latin names. For Cyrillic, the user enters slug manually. Formula: `name.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')`. If result is empty (pure Cyrillic), slug field stays empty for manual input.
- Delete: confirmation inline — "Вы уверены?" with "Да, удалить" / "Отмена"
- After any mutation → refetch tree from API

---

## 5. Error Handling

Backend error codes mapped to Russian messages:

| Code | UI Message |
|------|-----------|
| `CATEGORY_SLUG_CONFLICT` | Категория с таким slug уже существует на этом уровне |
| `CATEGORY_MAX_DEPTH_REACHED` | Достигнута максимальная глубина вложенности |
| `CATEGORY_HAS_CHILDREN` | Нельзя удалить категорию с дочерними элементами |
| `CATEGORY_NOT_FOUND` | Категория не найдена |
| `VALIDATION_ERROR` | Проверьте введённые данные |
| `INSUFFICIENT_PERMISSIONS` | Недостаточно прав |

Errors displayed inside modal as red block. Unknown codes fallback to `error.message` from backend.

---

## 6. Component Behavior

### CategoriesPage (`page.jsx`)
- `'use client'`
- State: `tree` (array), `loading`, `modalState` (null | {mode: 'create'|'edit', parentId?, category?})
- On mount: fetch `GET /api/categories/tree`
- Passes `onAddChild`, `onEdit` callbacks to tree
- After mutation success: refetch tree, close modal

### CategoryTree
- Receives `nodes[]`, `onAddChild(parentId)`, `onEdit(category)`
- Maps nodes to `CategoryNode` recursively

### CategoryNode
- Props: `node`, `level`, `onAddChild`, `onEdit`
- State: `expanded` (default: true for level 0, false for deeper)
- Renders: toggle icon (▶/▼ if has children, • if leaf), name, [+] and [✎] buttons
- Indentation: `paddingLeft: level * 24px`

### CategoryModal
- Wraps existing `src/components/ui/Modal.jsx` for consistency with other modals in the project
- Props: `mode` ('create'|'edit'), `parentId?`, `category?`, `onClose`, `onSuccess`
- State: `name`, `slug`, `sortOrder`, `error`, `loading`, `confirmDelete`
- Create: POST `/api/categories` with `{name, slug, parentId, sortOrder}`
- Edit: PATCH `/api/categories/{id}` with changed fields only
- Delete: DELETE `/api/categories/{id}` (after confirmation)
