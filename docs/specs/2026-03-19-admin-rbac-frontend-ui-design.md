# Admin RBAC Frontend UI — Design Spec

**Date:** 2026-03-19
**Scope:** Three admin pages — Пользователи (Users), Роли (Roles), Права (Permissions) — with full API integration to backend admin endpoints.
**Depends on:** `2026-03-19-admin-rbac-backend-api-design.md` (backend endpoints must be implemented first)

---

## 1. Pages Overview

| Page | Path | Purpose |
|------|------|---------|
| Пользователи | `/admin/users` | List all users, search/filter, assign roles, deactivate |
| Роли | `/admin/settings/roles` | List roles, create/edit, manage permissions per role |
| Права | (section within Roles page) | Checkbox grid of permissions per role |

**Navigation changes:**
- `/admin/users` — existing sidebar item, currently shows mock data → replace with real API
- `/admin/settings/roles` — new item in settings nav after "Категории"

---

## 2. BFF Route Handlers

### Users/Identities BFF

| Frontend Route | Method | Backend Target |
|---------------|--------|---------------|
| `/api/admin/identities` | GET | `GET /api/v1/admin/identities?offset&limit&search&roleId&isActive&sortBy&sortOrder` |
| `/api/admin/identities/[id]` | GET | `GET /api/v1/admin/identities/{id}` |
| `/api/admin/identities/[id]/deactivate` | POST | `POST /api/v1/admin/identities/{id}/deactivate` |
| `/api/admin/identities/[id]/reactivate` | POST | `POST /api/v1/admin/identities/{id}/reactivate` |
| `/api/admin/identities/[id]/roles` | POST | `POST /api/v1/admin/identities/{id}/roles` |
| `/api/admin/identities/[id]/roles/[roleId]` | DELETE | `DELETE /api/v1/admin/identities/{id}/roles/{roleId}` |

### Roles BFF

| Frontend Route | Method | Backend Target |
|---------------|--------|---------------|
| `/api/admin/roles` | GET | `GET /api/v1/admin/roles` |
| `/api/admin/roles` | POST | `POST /api/v1/admin/roles` |
| `/api/admin/roles/[id]` | GET | `GET /api/v1/admin/roles/{id}` |
| `/api/admin/roles/[id]` | PATCH | `PATCH /api/v1/admin/roles/{id}` |
| `/api/admin/roles/[id]` | DELETE | `DELETE /api/v1/admin/roles/{id}` |
| `/api/admin/roles/[id]/permissions` | PUT | `PUT /api/v1/admin/roles/{id}/permissions` |

### Permissions BFF

| Frontend Route | Method | Backend Target |
|---------------|--------|---------------|
| `/api/admin/permissions` | GET | `GET /api/v1/admin/permissions` |

All BFF handlers use `backendFetch()` + `getAccessToken()`. Auth required for all. Backend returns camelCase (CamelModel).

---

## 3. Пользователи Page (`/admin/users`)

### Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Пользователи                                                   │
├─────────────────────────────────────────────────────────────────┤
│  [🔍 Поиск по email или имени]  [Роль ▼]  [Статус ▼]  [Сброс] │
├─────────────────────────────────────────────────────────────────┤
│  Email          │ Имя          │ Роли         │ Статус │ Действия │
│  admin@test.com │ Иван Петров  │ super_admin  │ ●Актив │ [✎]     │
│  user@test.com  │ Мария Сидор. │ customer     │ ●Актив │ [✎]     │
│  old@test.com   │ [DELETED]    │ —            │ ○Неакт │ [✎]     │
├─────────────────────────────────────────────────────────────────┤
│  < 1 2 3 ... 5 >                   Показано 1-20 из 95         │
└─────────────────────────────────────────────────────────────────┘
```

### Components

| Component | File | Purpose |
|-----------|------|---------|
| `UsersPage` | `app/admin/users/page.jsx` | Replace existing mock page |
| `UserTable` | `components/admin/users/UserTable.jsx` | Table with sortable columns |
| `UserRow` | `components/admin/users/UserRow.jsx` | Replace existing mock component |
| `UserDetailModal` | `components/admin/users/UserDetailModal.jsx` | View/edit user, manage roles |
| `UserFilters` | `components/admin/users/UserFilters.jsx` | Search + role/status dropdowns |

### UserDetailModal

```
┌───────────────────────────────────────┐
│  Пользователь                   [✕]   │
├───────────────────────────────────────┤
│  Email: admin@test.com                │
│  Имя: Иван Петров                    │
│  Телефон: +7 999 123-45-67           │
│  Статус: Активен                      │
│  Дата регистрации: 19 марта 2026     │
│                                       │
│  Роли:                                │
│  ┌─────────────────────────────────┐  │
│  │ super_admin              [✕]   │  │
│  │ manager                  [✕]   │  │
│  └─────────────────────────────────┘  │
│  [+ Назначить роль ▼]                │
│                                       │
│  ─────────────────────────────────── │
│  [Деактивировать аккаунт]            │
└───────────────────────────────────────┘
```

**Behavior:**
- Click [✕] on role badge → revoke role (with confirmation)
- [+ Назначить роль] → dropdown with available roles → assign
- [Деактивировать] → confirmation → POST deactivate
- If deactivated → show [Реактивировать] instead

---

## 4. Роли Page (`/admin/settings/roles`)

### Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  Роли                                        [+ Создать роль]   │
├─────────────────────────────────────────────────────────────────┤
│  Название     │ Тип      │ Прав │ Действия                     │
│  super_admin  │ Системная│  19  │ [Настроить права]            │
│  manager      │ Системная│  14  │ [Настроить права]            │
│  customer     │ Системная│   8  │ [Настроить права]            │
│  moderator    │ Кастомная│   5  │ [✎] [Настроить права] [🗑]  │
└─────────────────────────────────────────────────────────────────┘
```

### Components

| Component | File | Purpose |
|-----------|------|---------|
| `RolesPage` | `app/admin/settings/roles/page.jsx` | Roles list page |
| `RoleRow` | `components/admin/settings/roles/RoleRow.jsx` | Single role row |
| `RoleModal` | `components/admin/settings/roles/RoleModal.jsx` | Create/edit role (name, description) |
| `RolePermissionsModal` | `components/admin/settings/roles/RolePermissionsModal.jsx` | Checkbox grid for permissions |

### RoleModal (Create / Edit)

```
┌───────────────────────────────────────┐
│  Новая роль / Редактирование    [✕]   │
├───────────────────────────────────────┤
│  Название                             │
│  [___________________________________]│
│                                       │
│  Описание                             │
│  [___________________________________]│
│                                       │
│  {error message}                      │
│  [Сохранить]                          │
│                                       │
│  [Удалить роль] (edit, custom only)   │
└───────────────────────────────────────┘
```

### RolePermissionsModal (Checkbox Grid)

```
┌───────────────────────────────────────────────────┐
│  Права роли: manager                        [✕]   │
├───────────────────────────────────────────────────┤
│                                                   │
│  Бренды          [✓]create [✓]read [✓]update [✓]delete │
│  Категории       [✓]create [✓]read [✓]update [✓]delete │
│  Товары          [✓]create [✓]read [✓]update [✓]delete │
│  Заказы          [✓]create [✓]read [✓]update [ ]delete │
│  Пользователи   [ ]create [✓]read [ ]update [ ]delete │
│  Роли            [ ]manage                        │
│  Идентификации   [ ]manage                        │
│                                                   │
│  {error message}                                  │
│  [Сохранить]                                      │
└───────────────────────────────────────────────────┘
```

**Behavior:**
- On open: `GET /api/admin/permissions` (grouped) + `GET /api/admin/roles/{id}` (current permissions)
- Checkboxes prefilled based on role's current permissions
- [Сохранить] → `PUT /api/admin/roles/{id}/permissions` with list of checked permission IDs
- Error `PRIVILEGE_ESCALATION` → "Нельзя назначить права, которых у вас нет"

---

## 5. Error Handling

| Code | UI Message |
|------|-----------|
| `IDENTITY_NOT_FOUND` | Пользователь не найден |
| `IDENTITY_ALREADY_DEACTIVATED` | Аккаунт уже деактивирован |
| `IDENTITY_ALREADY_ACTIVE` | Аккаунт уже активен |
| `SELF_DEACTIVATION_FORBIDDEN` | Нельзя деактивировать свой аккаунт |
| `LAST_ADMIN_PROTECTION` | Нельзя деактивировать последнего администратора |
| `ROLE_NOT_FOUND` | Роль не найдена |
| `ROLE_ALREADY_EXISTS` | Роль с таким именем уже существует |
| `SYSTEM_ROLE_MODIFICATION` | Системные роли нельзя изменить |
| `PRIVILEGE_ESCALATION` | Нельзя назначить права, которых у вас нет |
| `PERMISSION_NOT_FOUND` | Право не найдено |
| `INSUFFICIENT_PERMISSIONS` | Недостаточно прав |
| `VALIDATION_ERROR` | Проверьте введённые данные |

Unknown codes fallback to `error.message` from backend.

---

## 6. File Structure

### New files

**BFF Route Handlers (7 files):**
- `src/app/api/admin/identities/route.js` — GET list
- `src/app/api/admin/identities/[id]/route.js` — GET detail
- `src/app/api/admin/identities/[id]/deactivate/route.js` — POST
- `src/app/api/admin/identities/[id]/reactivate/route.js` — POST
- `src/app/api/admin/identities/[id]/roles/route.js` — POST assign
- `src/app/api/admin/identities/[id]/roles/[roleId]/route.js` — DELETE revoke
- `src/app/api/admin/roles/route.js` — GET list, POST create
- `src/app/api/admin/roles/[id]/route.js` — GET detail, PATCH update, DELETE
- `src/app/api/admin/roles/[id]/permissions/route.js` — PUT set permissions
- `src/app/api/admin/permissions/route.js` — GET grouped list

**Pages (2 files):**
- `src/app/admin/users/page.jsx` — replace existing mock
- `src/app/admin/settings/roles/page.jsx` — new

**User Components (4 files):**
- `src/components/admin/users/UserTable.jsx`
- `src/components/admin/users/UserRow.jsx` — replace existing mock
- `src/components/admin/users/UserDetailModal.jsx`
- `src/components/admin/users/UserFilters.jsx`

**Role Components (3 files):**
- `src/components/admin/settings/roles/RoleRow.jsx`
- `src/components/admin/settings/roles/RoleModal.jsx`
- `src/components/admin/settings/roles/RolePermissionsModal.jsx`

### Modified files
- `src/app/admin/settings/layout.jsx` — add "Роли" after "Категории" in navItems

---

## 7. Implementation Order

1. **Backend API first** — implement all 8 endpoints from backend spec
2. **BFF Route Handlers** — proxy layer
3. **Users page** — replace mock with API, add detail modal
4. **Roles page** — list, create/edit modal
5. **Permissions modal** — checkbox grid with PUT save
6. **Settings nav** — add "Роли" link
