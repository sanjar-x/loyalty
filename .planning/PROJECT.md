# Product Creation Flow — Integration Fix

## What This Is

Административная панель для управления товарным каталогом маркетплейса. Сквозной flow создания товара (form → draft → media upload → SKU → attributes → publish) работает end-to-end через admin panel. Исправлены все 14 интеграционных расхождений между backend, admin frontend и image_backend, выявленных аудитом 2026-03-29.

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

(None — all v1.0 requirements shipped. See v2 backlog: Phase 999.1)

### Shipped in v1.0

- ✓ Admin BFF media proxy routes (upload/confirm/external/status GET) — v1.0 Phase 3-5, 7
- ✓ Admin frontend field name alignment (presignedUrl, storageObjectId) — v1.0 Phase 6
- ✓ Admin frontend request schema alignment ({contentType, filename}) — v1.0 Phase 6
- ✓ Admin frontend dual-locale i18n (buildI18nPayload helper) — v1.0 Phase 2
- ✓ Backend descriptionI18N truly optional — v1.0 Phase 1
- ✓ Backend countryOfOrigin field — v1.0 Phase 1
- ✓ Admin frontend media processing status polling — v1.0 Phase 7
- ✓ Admin frontend completeness endpoint display — v1.0 Phase 8
- ✓ Admin frontend FSM UI (5 statuses, 7 transitions) — v1.0 Phase 8
- ✓ Admin frontend version tracking infrastructure — v1.0 Phase 8
- ✓ Spec I18N naming convention corrected — v1.0 Phase 2

### Out of Scope

- frontend/main TypeScript types (i18n naming, ProductStatus enum) — will fix when connecting API layer
- frontend/main RTK Query API endpoints — separate project
- New features or UX improvements beyond fixing existing issues
- Image backend changes — all endpoints already correct per audit

## Context

- Product Creation Flow реализован по спецификации `product-creation-flow.md` (обновлена в Phase 2)
- v1.0 shipped 2026-03-30: все 14 integration issues из audit.md исправлены
- Admin BFF: `backendFetch()` → main backend, `imageBackendFetch()` → image_backend (X-API-Key auth)
- Media pipeline: reserve → S3 upload → confirm → pollMediaStatus (exponential backoff) → COMPLETED
- i18n: `buildI18nPayload(ru, en)` для записи, `i18n(obj)` для чтения — обе в `lib/utils.js`
- Product detail page: CompletenessPanel + StatusTransitionBar + version tracking
- Tech debt: product list page uses mock data, media not attached to product entity, updateProduct() unused

## Constraints

- **Architecture:** Admin BFF proxy → image_backend напрямую для media операций (не через main backend)
- **Backend contracts:** Не ломать существующие API-контракты — только расширять (добавлять поля, делать optional)
- **I18n convention:** Backend отдаёт `I18N` (uppercase N) — это факт, frontend адаптируется
- **Tech stack:** Существующий стек без изменений (FastAPI, Next.js, Pydantic)

## Key Decisions

| Decision                     | Rationale                                                                                    | Outcome     |
| ---------------------------- | -------------------------------------------------------------------------------------------- | ----------- |
| BFF → image_backend напрямую | Main backend не должен быть прокси для binary uploads. BFF уже имеет IMAGE_BACKEND_URL в env | ✓ Good      |
| frontend/main вне scope      | API слой не подключён вообще — отдельный проект                                              | ✓ Good      |
| Все 14 проблем в scope       | Minor-проблемы (completeness, FSM UI, version) улучшают UX и предотвращают future bugs       | ✓ Good      |
| Polling вместо SSE           | Railway может буферизовать SSE; polling проще и deployment-safe                              | ✓ Good      |
| buildI18nPayload(ru, en)     | Единая точка формирования i18n payloads, en || ru fallback                                   | ✓ Good      |
| Product detail read-only     | Edit form — отдельная задача, version tracking infrastructure готова                         | ⚠️ Revisit |

## Current State

v1.0 shipped 2026-03-30. All 14 integration issues resolved. Next: connect product list to real API, add media-to-product attachment, build product edit form.

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
*Last updated: 2026-03-30 after v1.0 milestone completed*
