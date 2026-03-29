# Requirements: Product Creation Flow Integration Fix

**Defined:** 2026-03-29
**Core Value:** Сквозной flow создания товара (form -> draft -> media upload -> SKU -> attributes -> publish) должен работать end-to-end через admin panel без ошибок интеграции.

## v1 Requirements

Requirements for fixing all integration issues identified in audit.md.

### Backend Schema Fixes

- [x] **BKND-01**: User can create product without descriptionI18n (field truly optional: `I18nDict | None = None`)
- [x] **BKND-02**: User can set countryOfOrigin when creating product (field added to ProductCreateRequest and wired through command)

### Frontend i18n

- [x] **I18N-01**: Admin form always sends both ru+en locales in all i18n fields (fallback: ru value used for empty en)
- [x] **I18N-02**: Spec product-creation-flow.md updated to reflect actual backend naming convention (titleI18N, uppercase N)

### BFF Media Proxy

- [x] **BFF-01**: Admin BFF has imageBackendFetch() utility targeting IMAGE_BACKEND_URL with X-API-Key auth
- [x] **BFF-02**: Admin BFF route /api/media/upload proxies to image_backend POST /api/v1/media/upload
- [x] **BFF-03**: Admin BFF route /api/media/{id}/confirm proxies to image_backend POST /api/v1/media/{id}/confirm
- [x] **BFF-04**: Admin BFF route /api/media/external proxies to image_backend POST /api/v1/media/external

### Frontend Media Integration

- [ ] **MEDIA-01**: Admin frontend uses correct field names from image_backend responses (presignedUrl, storageObjectId)
- [ ] **MEDIA-02**: Admin frontend sends correct upload request schema to image_backend ({contentType, filename})
- [ ] **MEDIA-03**: Admin frontend polls media processing status before attaching to product (wait for COMPLETED)

### Admin UI Enhancements

- [ ] **UI-01**: Admin product form displays missing required/recommended attributes from completeness endpoint
- [ ] **UI-02**: Admin FSM UI supports all 5 transitions (DRAFT<->ENRICHING, ENRICHING->READY_FOR_REVIEW, READY_FOR_REVIEW->PUBLISHED, PUBLISHED->ARCHIVED, ARCHIVED->DRAFT)
- [ ] **UI-03**: Admin sends version field in all PATCH requests for optimistic locking support

## v2 Requirements

### Frontend Main Integration

- **MAIN-01**: frontend/main TypeScript types use correct i18n field names (I18N uppercase)
- **MAIN-02**: frontend/main ProductStatus type matches backend enum values
- **MAIN-03**: frontend/main RTK Query API endpoints connected to backend

## Out of Scope

| Feature | Reason |
|---------|--------|
| frontend/main API layer | API completely unconnected, separate project -- user decision |
| frontend/main TypeScript type fixes | Deferred until API layer is connected |
| Image backend changes | All endpoints already correct per audit |
| New product features (bulk operations, import/export) | Not part of integration fix |
| Backend i18n naming change | Backend uses I18N (uppercase) correctly via to_camel -- no change needed |
| SSE streaming for media status | Polling is simpler and deployment-safe; SSE can be added later |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| BKND-01 | Phase 1 | Complete |
| BKND-02 | Phase 1 | Complete |
| I18N-01 | Phase 2 | Complete |
| I18N-02 | Phase 2 | Complete |
| BFF-01 | Phase 3 | Complete |
| BFF-02 | Phase 4 | Complete |
| BFF-03 | Phase 5 | Complete |
| BFF-04 | Phase 5 | Complete |
| MEDIA-01 | Phase 6 | Pending |
| MEDIA-02 | Phase 6 | Pending |
| MEDIA-03 | Phase 7 | Pending |
| UI-01 | Phase 8 | Pending |
| UI-02 | Phase 8 | Pending |
| UI-03 | Phase 8 | Pending |

**Coverage:**
- v1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0

---
*Requirements defined: 2026-03-29*
*Last updated: 2026-03-29 after plan 01-01 completion (BKND-01, BKND-02 marked complete)*
