# Product Creation Flow — Integration Fix

## What This Is

Исправление интеграционных расхождений между backend, admin frontend и image_backend в Product Creation Flow. Аудит выявил 14 проблем (6 critical, 4 major, 4 minor), из-за которых сквозной flow создания товара от формы до публикации не работает. Основные блокеры: отсутствующие media proxy-маршруты, несовпадение i18n-полей, несовпадение request/response schemas между frontend и image_backend.

## Core Value

Сквозной flow создания товара (form → draft → media upload → SKU → attributes → publish) должен работать end-to-end через admin panel без ошибок интеграции.

## Requirements

### Validated

- ✓ Backend product CRUD endpoints (POST/GET/PATCH/DELETE) — existing, audit confirmed
- ✓ Backend media endpoints (add/list/update/delete/reorder) — existing, audit confirmed
- ✓ Backend SKU endpoints with variant hash — existing, audit confirmed
- ✓ Backend product attributes (single + bulk) — existing, audit confirmed
- ✓ Backend FSM with 5 transitions + guards — existing, audit confirmed
- ✓ Backend completeness endpoint — existing, audit confirmed
- ✓ Backend optimistic locking (version_id_col) — existing, audit confirmed
- ✓ Backend soft delete with filtered unique indexes — existing, audit confirmed
- ✓ Image backend endpoints (upload/confirm/external/get/delete) — existing, audit confirmed
- ✓ Image processing pipeline (thumbnail/medium/large) — existing, audit confirmed
- ✓ Admin frontend product creation form UI — existing
- ✓ Admin frontend attribute selection UI (all 5 uiTypes) — existing
- ✓ Storefront form-attributes endpoint — existing, audit confirmed

### Active

#### Critical (Blockers)

- [ ] Admin BFF media proxy routes to image_backend (upload/confirm/external) — issue #1
- [ ] Admin frontend field name alignment with image_backend responses — issue #2
- [ ] Admin frontend request schema alignment with image_backend upload API — issue #3
- [ ] Admin frontend always sends both ru+en locales in i18n fields — issue #4

#### Major

- [ ] Backend descriptionI18n truly optional in ProductCreateRequest — issue #7
- [ ] Backend countryOfOrigin in ProductCreateRequest — issue #8
- [ ] Admin frontend media processing status polling — issue #9

#### Minor

- [ ] Admin frontend uses completeness endpoint — issue #11
- [ ] Admin frontend FSM UI supports all transitions — issue #12
- [ ] Admin frontend sends version in PATCH requests — issue #13
- [ ] Spec updated: I18n → I18N naming convention — issue #14

### Out of Scope

- frontend/main TypeScript types (i18n naming, ProductStatus enum) — will fix when connecting API layer
- frontend/main RTK Query API endpoints — separate project
- New features or UX improvements beyond fixing existing issues
- Image backend changes — all endpoints already correct per audit

## Context

- Product Creation Flow реализован по спецификации `product-creation-flow.md`
- Аудит интеграции выполнен 2026-03-29, результаты в `audit.md`
- Backend и image_backend корректны сами по себе — проблемы только на стыках
- Admin BFF (Next.js API routes) проксирует запросы через `backendFetch()` к main backend
- Для media операций нужно направить BFF напрямую на image_backend (решение: отдельный `imageBackendFetch()`)
- `populate_by_name=True` в backend Pydantic — принимает оба варианта i18n полей на вход, но отдаёт только `I18N`

## Constraints

- **Architecture:** Admin BFF proxy → image_backend напрямую для media операций (не через main backend)
- **Backend contracts:** Не ломать существующие API-контракты — только расширять (добавлять поля, делать optional)
- **I18n convention:** Backend отдаёт `I18N` (uppercase N) — это факт, frontend адаптируется
- **Tech stack:** Существующий стек без изменений (FastAPI, Next.js, Pydantic)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| BFF → image_backend напрямую | Main backend не должен быть прокси для binary uploads. BFF уже имеет IMAGE_BACKEND_URL в env | — Pending |
| frontend/main вне scope | API слой не подключён вообще — отдельный проект | — Pending |
| Все 14 проблем в scope | Minor-проблемы (completeness, FSM UI, version) улучшают UX и предотвращают future bugs | — Pending |

## Current Milestone: v1.0 Backend Schema Fixes

**Goal:** Исправить расхождения в Pydantic request-схемах ProductCreateRequest — descriptionI18n сделать truly optional, добавить countryOfOrigin.

**Target features:**
- descriptionI18n: Optional[I18nDict] = None вместо I18nDict = Field(default_factory=dict)
- countryOfOrigin: добавить в ProductCreateRequest (уже есть в ProductUpdateRequest)

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-29 after milestone v1.0 Backend Schema Fixes started*
