# Milestones

## v1.0 Product Creation Flow Integration Fix (Shipped: 2026-03-30)

**Phases completed:** 8 phases, 10 plans, 14 tasks

**Key accomplishments:**

- buildI18nPayload helper + product form and category CRUD i18n fixes — backend never receives incomplete locale dicts
- Fixed 24 I18n→I18N occurrences, corrected to_camel explanation, added countryOfOrigin docs and en locale to storefront examples
- Server-side fetch wrapper for image_backend with X-API-Key auth and structured 502 error handling
- POST /api/media/upload route strips product-specific fields and forwards {contentType, filename} to image_backend
- Two media proxy routes: confirm (POST 202, no body) and external import (POST 201, URL passthrough)
- Fixed all media field names (presignedUrl, storageObjectId, filename, url) and rewired to new BFF routes
- BFF GET route + pollMediaStatus with exponential backoff, wired into upload orchestration
- BFF product detail/completeness routes + 3 service functions + FSM transition map matching backend exactly
- Product detail page with CompletenessPanel (missing attrs), StatusTransitionBar (5 FSM statuses), version tracking, and ProductRow edit link

---
