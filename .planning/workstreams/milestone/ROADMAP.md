# Roadmap: Product Creation Flow Integration Fix

## Overview

This roadmap fixes 14 integration issues that prevent the admin panel's product creation flow from working end-to-end. The work progresses from independent backend/frontend fixes through BFF media proxy infrastructure and route handlers, to frontend media integration and UI enhancements. The dependency chain is: backend schema fixes and i18n are independent foundations, BFF infrastructure enables route handlers, working routes enable frontend media integration, and UI enhancements can run after backend fixes land.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Backend Schema Fixes** - Make descriptionI18n truly optional and add countryOfOrigin to ProductCreateRequest
- [x] **Phase 2: Frontend i18n & Spec Alignment** - Enforce dual-locale i18n payloads and update spec naming convention
- [x] **Phase 3: BFF Media Proxy Infrastructure** - Create imageBackendFetch() utility with X-API-Key auth targeting IMAGE_BACKEND_URL
- [x] **Phase 4: BFF Upload Route** - Proxy /api/media/upload to image_backend with correct URL mapping and request filtering
- [x] **Phase 5: BFF Confirm & External Routes** - Proxy confirm and external import routes to image_backend
- [x] **Phase 6: Frontend Media Field Alignment** - Fix field names and request schemas to match image_backend API
- [ ] **Phase 7: Frontend Media Status Polling** - Poll processing status before attaching media to product
- [ ] **Phase 8: Admin UI Enhancements** - Completeness endpoint, full FSM transitions, and optimistic locking

## Phase Details

### Phase 1: Backend Schema Fixes
**Goal**: Backend accepts product creation payloads with optional description and country of origin
**Depends on**: Nothing (first phase)
**Requirements**: BKND-01, BKND-02
**Success Criteria** (what must be TRUE):
  1. API consumer can POST /products without descriptionI18n field and receive 201 (not 422)
  2. API consumer can POST /products with countryOfOrigin field and the value persists in the created product
  3. Existing product creation requests with descriptionI18n still work unchanged (backward compatible)
**Plans**: 1 plan
Plans:
- [x] 01-01-PLAN.md — Fix ProductCreateRequest schema (optional descriptionI18n + countryOfOrigin) with e2e tests

### Phase 2: Frontend i18n & Spec Alignment
**Goal**: Admin form always sends valid i18n payloads and spec documentation matches actual backend behavior
**Depends on**: Nothing (independent of Phase 1)
**Requirements**: I18N-01, I18N-02
**Success Criteria** (what must be TRUE):
  1. Admin product form always sends both ru and en locales in every i18n field (empty en falls back to ru value)
  2. Backend never returns 422 "Missing required locales" when admin form submits i18n fields
  3. product-creation-flow.md spec uses I18N (uppercase N) naming convention matching actual backend output
**Plans**: 2 plans
Plans:
- [x] 02-01-PLAN.md — Fix admin form i18n payloads (product form + category modal/display) with shared helper
- [x] 02-02-PLAN.md — Update product-creation-flow.md spec (I18N naming, to_camel explanation, Phase 1 changes)

### Phase 3: BFF Media Proxy Infrastructure
**Goal**: Admin BFF has a working HTTP client for image_backend with correct auth and error handling
**Depends on**: Nothing (independent infrastructure)
**Requirements**: BFF-01
**Success Criteria** (what must be TRUE):
  1. imageBackendFetch() utility exists and sends X-API-Key header (not JWT Bearer) to IMAGE_BACKEND_URL
  2. imageBackendFetch() returns structured error (502) when image_backend is unreachable
  3. IMAGE_BACKEND_URL and IMAGE_BACKEND_API_KEY are configured as server-only env vars in admin frontend
**Plans**: 1 plan
Plans:
- [x] 03-01-PLAN.md — Create imageBackendFetch() utility and configure image_backend env vars

### Phase 4: BFF Upload Route
**Goal**: Admin BFF correctly proxies media upload requests to image_backend
**Depends on**: Phase 3
**Requirements**: BFF-02
**Success Criteria** (what must be TRUE):
  1. POST /api/media/upload in admin BFF forwards to image_backend POST /api/v1/media/upload (not main backend)
  2. BFF strips product-specific fields (mediaType, role, sortOrder) before forwarding to image_backend
  3. Response returns presignedUrl and storageObjectId from image_backend to the browser
**Plans**: 1 plan
Plans:
- [x] 04-01-PLAN.md — Create POST /api/media/upload BFF proxy route with field stripping and auth gating

### Phase 5: BFF Confirm & External Routes
**Goal**: Admin BFF correctly proxies media confirm and external import requests to image_backend
**Depends on**: Phase 3
**Requirements**: BFF-03, BFF-04
**Success Criteria** (what must be TRUE):
  1. POST /api/media/{id}/confirm in admin BFF forwards to image_backend POST /api/v1/media/{id}/confirm
  2. POST /api/media/external in admin BFF forwards to image_backend POST /api/v1/media/external
  3. Both routes use imageBackendFetch() with X-API-Key auth (not backendFetch with JWT)
**Plans**: 1 plan
Plans:
- [x] 05-01-PLAN.md — Create BFF confirm and external import proxy routes using imageBackendFetch()

### Phase 6: Frontend Media Field Alignment
**Goal**: Admin frontend uses correct field names and request schemas when communicating with image_backend via BFF
**Depends on**: Phase 4, Phase 5
**Requirements**: MEDIA-01, MEDIA-02
**Success Criteria** (what must be TRUE):
  1. Admin frontend reads presignedUrl (not presignedUploadUrl) from upload response
  2. Admin frontend reads storageObjectId (not id) from upload response
  3. Admin frontend sends {contentType, filename} in upload request (not {mimeType, fileName, mediaType, role})
**Plans**: 1 plan
Plans:
- [x] 06-01-PLAN.md — Fix media service functions and orchestration callsites to use correct BFF routes, request schemas, and response fields

### Phase 7: Frontend Media Status Polling
**Goal**: Admin frontend waits for media processing completion before displaying uploaded media
**Depends on**: Phase 6
**Requirements**: MEDIA-03
**Success Criteria** (what must be TRUE):
  1. After upload confirm, admin frontend polls or subscribes for processing status
  2. Media is only displayed/attached to product after status reaches COMPLETED
  3. User sees processing indicator while media is being processed
**Plans**: 1 plan
Plans:
- [ ] 07-01-PLAN.md — BFF GET media route, pollMediaStatus with backoff, wire into useSubmitProduct

### Phase 8: Admin UI Enhancements
**Goal**: Admin product form uses completeness endpoint, supports all FSM transitions, and sends version for optimistic locking
**Depends on**: Phase 1 (backend must accept correct payloads)
**Requirements**: UI-01, UI-02, UI-03
**Success Criteria** (what must be TRUE):
  1. Admin product form displays missing required/recommended attributes sourced from completeness endpoint
  2. Admin FSM UI shows all 5 valid transitions and disables invalid ones based on current product status
  3. All PATCH requests from admin include version field from the last-fetched product for optimistic locking
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order. Phases 1, 2, 3 are independent and can parallelize. Phase 4 and 5 depend on Phase 3. Phase 6 depends on 4+5. Phase 7 depends on 6. Phase 8 depends on 1.

| Phase                             | Plans Complete | Status      | Completed  |
| --------------------------------- | -------------- | ----------- | ---------- |
| 1. Backend Schema Fixes           | 1/1            | Complete    | 2026-03-29 |
| 2. Frontend i18n & Spec Alignment | 2/2            | Complete    | 2026-03-30 |
| 3. BFF Media Proxy Infrastructure | 1/1            | Complete    | 2026-03-30 |
| 4. BFF Upload Route               | 1/1            | Complete    | 2026-03-30 |
| 5. BFF Confirm & External Routes  | 1/1            | Complete    | 2026-03-30 |
| 6. Frontend Media Field Alignment | 1/1            | Complete    | 2026-03-30 |
| 7. Frontend Media Status Polling  | 0/1            | Not started | -          |
| 8. Admin UI Enhancements          | 0/TBD          | Not started | -          |
