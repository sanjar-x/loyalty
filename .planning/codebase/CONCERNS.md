# Codebase Concerns

**Analysis Date:** 2026-03-28

## Tech Debt

**Admin Frontend: Hardcoded Seed Data Instead of API Integration:**
- Issue: Most admin service modules use local in-memory seed data arrays instead of actual backend API calls. Orders, users, reviews, staff, promocodes, and referrals all read from static `@/data/*.js` files, meaning the admin panel operates as a UI prototype for these features, not a production tool.
- Files:
  - `frontend/admin/src/services/orders.js` (imports `ordersSeed`)
  - `frontend/admin/src/services/users.js` (imports `usersSeed`)
  - `frontend/admin/src/services/reviews.js` (imports `reviewsSeed`)
  - `frontend/admin/src/services/staff.js` (imports `staffSeed`)
  - `frontend/admin/src/services/promocodes.js` (imports `promocodesSeed`)
  - `frontend/admin/src/services/referrals.js` (imports `referralsSeed`)
  - `frontend/admin/src/data/orders.js`, `frontend/admin/src/data/products.js`, etc.
- Impact: Admin users see fake data; any changes (e.g., order status updates) are lost on page reload. Real backend endpoints for orders, reviews, referrals, and promocodes do not exist yet.
- Fix approach: Build backend modules for orders, reviews, referrals, and promocodes. Replace seed imports in service files with `fetch('/api/...')` calls, following the pattern already used in `frontend/admin/src/services/brands.js` and `frontend/admin/src/services/suppliers.js`.

**Admin Frontend: Plain JavaScript (No TypeScript):**
- Issue: The entire admin frontend (`frontend/admin/src/`) uses `.js`/`.jsx` files with zero TypeScript. The main frontend (`frontend/main/`) uses TypeScript. This creates a type-safety gap in the admin panel where runtime bugs are harder to catch.
- Files: All files under `frontend/admin/src/` (0 `.ts`/`.tsx` files found)
- Impact: Refactoring the admin panel is error-prone; no compile-time type checking; API response shapes are implicitly trusted.
- Fix approach: Incrementally rename `.jsx` to `.tsx` starting with service and hook files. Add TypeScript interfaces for API responses.

**Catalog Domain Entity God-File (2,220 lines):**
- Issue: `backend/src/modules/catalog/domain/entities.py` contains Brand, Category, AttributeTemplate, TemplateAttributeBinding, AttributeGroup, Attribute, ProductVariant, SKU, and Product aggregates all in a single file. At 2,220 lines, this is the largest file in the backend by a significant margin.
- Files: `backend/src/modules/catalog/domain/entities.py`
- Impact: Difficult to navigate, high merge-conflict risk, cognitive overload when modifying any single entity.
- Fix approach: Split into separate files per aggregate root: `brand.py`, `category.py`, `attribute.py`, `attribute_template.py`, `product.py` (with ProductVariant + SKU). Keep a barrel `__init__.py` for backward-compatible imports.

**Catalog DI Provider Mega-File (518 lines):**
- Issue: `backend/src/modules/catalog/presentation/dependencies.py` registers all catalog command handlers, query handlers, and repositories in a single Dishka provider file. With 45 command handlers alone, this file is bloated with imports.
- Files: `backend/src/modules/catalog/presentation/dependencies.py`
- Impact: Adding any new catalog feature requires editing this file, which grows monotonically.
- Fix approach: Split into per-subdomain providers (e.g., `BrandProvider`, `AttributeProvider`, `ProductProvider`) in separate files and compose them in the container.

**Multiple Unimplemented Frontend Features (TODOs):**
- Issue: Numerous TODO comments mark unimplemented functionality across both frontends.
- Files:
  - `frontend/main/lib/hooks/useItemFavorites.ts` - Favorites API stub (returns empty data)
  - `frontend/main/app/product/[id]/page.tsx` - "connect to API" comments on lines 386/390
  - `frontend/main/app/profile/about/page.tsx` - 4 unimplemented legal document links
  - `frontend/main/app/profile/settings/page.tsx` - Pickup point add/edit not implemented
  - `frontend/main/app/profile/purchased/review/[id]/ReviewClient.tsx` - Review submission stub
  - `frontend/main/components/blocks/catalog/BrandsList.tsx` - Brands API not connected
- Impact: Users encounter dead-end UI flows for favorites, reviews, and legal pages.
- Fix approach: Prioritize favorites and reviews as they affect core UX. Legal document links can point to static pages initially.

**Hardcoded Domain in Admin Staff Invite:**
- Issue: Staff invitation link domain is hardcoded as `invite.admin.loyaltymarket.ru`.
- Files: `frontend/admin/src/app/admin/settings/staff/page.jsx` (line 133)
- Impact: Broken in non-production environments; requires code change to use different domain.
- Fix approach: Use `NEXT_PUBLIC_INVITE_DOMAIN` environment variable as the TODO suggests.

**Duplicated StatsIcon Component:**
- Issue: `StatsIcon` SVG component is duplicated in two admin pages.
- Files:
  - `frontend/admin/src/app/admin/settings/promocodes/page.jsx`
  - `frontend/admin/src/app/admin/settings/staff/page.jsx`
- Impact: Minor; duplicated code that diverges over time.
- Fix approach: Extract to `frontend/admin/src/components/icons/StatsIcon.jsx`.

## Known Bugs

**Image Backend Auth Bypass in Dev Mode:**
- Symptoms: When `INTERNAL_API_KEY` is an empty string (default), authentication is completely disabled. The `verify_api_key` dependency returns immediately without validating anything.
- Files: `image_backend/src/api/dependencies/auth.py` (line 31: `if not internal_key: return`)
- Trigger: Deploy image_backend without setting `INTERNAL_API_KEY` env var.
- Workaround: Always set `INTERNAL_API_KEY` in all environments, including dev.

**Outbox Relay: Silently Marks Unknown Events as Processed:**
- Symptoms: When an outbox event has an `event_type` that has no registered handler, the relay logs a warning but still marks it as processed (line 143-147). If a handler is deployed later, those events are lost.
- Files: `backend/src/infrastructure/outbox/relay.py` (lines 137-148)
- Trigger: Deploy new domain events before deploying the corresponding consumer handler.
- Workaround: Deploy consumer handlers before producers, or change the relay to leave unknown events unprocessed.

## Security Considerations

**No API Rate Limiting on Backend HTTP Endpoints:**
- Risk: Login, registration, and all authenticated endpoints lack HTTP-level rate limiting. The bot has throttling (`backend/src/bot/middlewares/throttling.py`), but the REST API does not.
- Files: `backend/src/bootstrap/web.py`, `backend/src/modules/identity/presentation/router_auth.py`
- Current mitigation: None at the application level.
- Recommendations: Add rate limiting middleware (e.g., `slowapi` or a custom Redis-based limiter) on `/auth/login`, `/auth/register`, `/auth/refresh` at minimum. Consider per-IP and per-identity limits.

**CSP Allows unsafe-inline and unsafe-eval (Admin Frontend):**
- Risk: The admin frontend's Content-Security-Policy includes `'unsafe-inline' 'unsafe-eval'` for scripts, which significantly weakens XSS protection.
- Files: `frontend/admin/next.config.js` (line 16)
- Current mitigation: The admin is behind authentication. The main frontend does not set CSP headers at all (only X-Frame-Options and X-Content-Type-Options via middleware).
- Recommendations: Use nonce-based CSP for the admin. Add CSP headers to the main frontend middleware.

**Admin Frontend CSP connect-src Restricts to 'self' Only:**
- Risk: The admin CSP sets `connect-src 'self'` which blocks fetch requests to any external domain. If the admin ever needs to call an external API (e.g., for image uploads to S3 presigned URLs), these requests will be blocked by the browser.
- Files: `frontend/admin/next.config.js` (line 16)
- Current mitigation: All API calls currently route through the Next.js BFF proxy (`/api/*` routes), so `connect-src 'self'` works today.
- Recommendations: When adding direct-to-S3 uploads from the admin, expand `connect-src` to include the S3 domain.

**Browser Debug Auth Includes Hardcoded User Credentials:**
- Risk: `frontend/main/lib/auth/debug.ts` contains a hardcoded Telegram user ID (`7427756366`) and username (`yokub_janovich`). While debug mode is properly gated to non-production, these are real-looking credentials committed to source.
- Files: `frontend/main/lib/auth/debug.ts`
- Current mitigation: `isBrowserDebugAuthEnabled()` returns false when `NODE_ENV === "production"`.
- Recommendations: Use generic placeholder data (e.g., `telegram_id: "0000000000"`) to avoid any confusion with real accounts.

**JWT Access Token Valid for 15 Minutes After Logout:**
- Risk: After logout, the access token remains valid until its JWT expiry (default 15 minutes). This is documented in a design comment but represents a window of unauthorized access.
- Files: `backend/src/modules/identity/presentation/dependencies.py` (lines 59-64, design comment)
- Current mitigation: Token version validation (`tv` claim vs `identity.token_version`) catches global invalidations. Session-level revocation is not checked.
- Recommendations: For sensitive operations, add a lightweight Redis blacklist check for revoked session IDs.

**Wildcard Remote Image Patterns:**
- Risk: The admin frontend allows loading images from any HTTPS hostname (`hostname: '**'` in `next.config.js` image configuration).
- Files: `frontend/admin/next.config.js` (line 23)
- Current mitigation: None.
- Recommendations: Restrict to known image hosting domains (S3 bucket domain, CDN domain).

## Performance Bottlenecks

**COUNT(*) Subquery on Every Paginated Endpoint:**
- Problem: The shared `paginate()` helper executes a `SELECT COUNT(*) FROM (base_query)` subquery on every paginated request, doubling the query load.
- Files: `backend/src/shared/pagination.py` (line 34)
- Cause: Standard offset-based pagination always needs the total count for UI pagination controls.
- Improvement path: For list-heavy endpoints (products, attributes), consider cursor-based pagination or caching total counts with short TTL. For admin endpoints with moderate traffic, the current approach is acceptable.

**Catalog Domain Entities: Nested Loop Searches:**
- Problem: `Product.find_sku()` and `Product.remove_sku()` iterate through all variants and their SKUs with nested loops to find a single SKU by ID. `Product.add_sku()` also iterates all variants' SKUs to check for duplicate hashes.
- Files: `backend/src/modules/catalog/domain/entities.py` (lines 2124-2170, 2172-2195)
- Cause: Pure domain entities without indexing; in-memory scans are O(variants * skus).
- Improvement path: Maintain a private `dict[UUID, SKU]` index on the Product aggregate for O(1) lookups. For typical products (1-5 variants, 1-50 SKUs each), current performance is acceptable but will degrade with large variant matrices.

**External Image Import Downloads Entire File Into Memory:**
- Problem: The image_backend external import endpoint downloads the entire external image (up to 10 MB) into memory before processing.
- Files: `image_backend/src/modules/storage/presentation/router.py` (lines 349-357, `response.content`)
- Cause: httpx `response.content` buffers the full response body.
- Improvement path: Use `response.aiter_bytes()` for streaming download with size-checking, or accept this for the 10 MB limit.

## Fragile Areas

**Category Tree Slug Cascade:**
- Files:
  - `backend/src/modules/catalog/application/commands/update_category.py`
  - `backend/src/modules/catalog/domain/entities.py` (Category entity)
  - `backend/src/modules/catalog/infrastructure/repositories/category.py`
- Why fragile: Renaming a category slug triggers `update_descendants_full_slug()` to rewrite all descendant `full_slug` values via string prefix replacement. If the operation partially fails or the cache invalidation after commit fails, the category tree can have inconsistent slugs. Also, the `effective_template_id` propagation via `propagate_effective_template_id()` runs in the same transaction.
- Safe modification: Always test slug changes with deep category trees (3+ levels). Verify both `full_slug` and `effective_template_id` on descendants after changes.
- Test coverage: Unit tests exist for `test_category_effective_family.py` but no integration tests for the full cascade with real DB.

**Admin Frontend BFF Proxy (Catch-All Route):**
- Files: `frontend/main/app/api/backend/[...path]/route.ts`
- Why fragile: This single catch-all route proxies ALL HTTP methods to the backend. It handles path encoding, trailing slash normalization, header filtering, timeout management, and error formatting. Any change can break API calls from the entire main frontend.
- Safe modification: Add integration tests for edge cases (encoded paths, trailing slashes, large request bodies). The current extensive error-detail extraction (lines 121-184) suggests past debugging difficulty.
- Test coverage: No tests.

**Outbox Relay Event Dispatch:**
- Files:
  - `backend/src/infrastructure/outbox/relay.py`
  - `backend/src/infrastructure/outbox/tasks.py`
  - `backend/src/bootstrap/scheduler.py`
- Why fragile: The relay uses `FOR UPDATE SKIP LOCKED` for concurrent safety but fetches event IDs in one transaction, then re-locks each event individually in separate transactions. A slow handler or network issue can cause the relay batch to take a long time, potentially triggering duplicate processing if the scheduler fires the next relay before the current one finishes.
- Safe modification: Ensure relay batch size and scheduler interval are tuned together. Monitor `outbox_messages` table size for unprocessed event buildup.
- Test coverage: Unit tests in `backend/tests/unit/infrastructure/outbox/test_relay.py`.

**ImageBackend Client (Best-Effort Deletes):**
- Files: `backend/src/modules/catalog/infrastructure/image_backend_client.py`
- Why fragile: The `ImageBackendClient.delete()` method silently swallows all exceptions and only logs warnings. If the image backend is down, media records in the main backend will reference deleted products but the S3 files will remain orphaned.
- Safe modification: Consider adding a dead-letter mechanism or scheduled cleanup job for orphaned S3 objects.
- Test coverage: Unit test exists at `backend/tests/unit/modules/catalog/infrastructure/test_image_backend_client.py`.

## Scaling Limits

**Single Alembic Migration File:**
- Current capacity: One migration file covers the entire initial schema (`backend/alembic/versions/2026/03/27_0911_19_7ce70774f240_init.py`).
- Limit: All schema changes are in a single migration. As the application grows, running migrations in production will lock tables for longer.
- Scaling path: Standard practice going forward -- create incremental migrations for each schema change.

**Connection Pool Sizing:**
- Current capacity: `pool_size=15`, `max_overflow=10` (25 max connections) in `backend/src/infrastructure/database/provider.py` (line 54-55).
- Limit: With 25 max DB connections per API process, scaling to multiple API replicas will multiply connection count against PostgreSQL's `max_connections`.
- Scaling path: Use PgBouncer or another connection pooler in front of PostgreSQL when scaling beyond 3-4 API replicas.

## Dependencies at Risk

**Python 3.14 (Pre-Release):**
- Risk: Both Dockerfiles use `python:3.14-slim-trixie`. Python 3.14 is scheduled for release in October 2026 and is currently in pre-release. Running pre-release Python in production risks encountering bugs in the interpreter, and some dependencies may not be fully compatible.
- Files: `backend/Dockerfile`, `image_backend/Dockerfile`
- Impact: Potential runtime issues with C extensions or async behavior.
- Migration plan: Pin to a stable release (e.g., `python:3.13-slim-bookworm`) until 3.14 reaches GA.

## Missing Critical Features

**No CI/CD Pipeline:**
- Problem: No GitHub Actions, GitLab CI, or any CI/CD configuration files exist in the repository. No `.github/workflows/`, no `.gitlab-ci.yml`.
- Blocks: Automated testing, linting enforcement, deployment automation, and merge-request quality gates.

**No Backend Modules for Orders, Payments, or Shipping:**
- Problem: The backend has modules for `catalog`, `identity`, `user`, `geo`, and `supplier`, but no modules for orders, payments, shipping/delivery, reviews, referrals, or promocodes -- all of which have admin UI pages using seed data.
- Blocks: Completing the admin panel API integration; launching any commerce flow.

**No Error Tracking / APM:**
- Problem: No Sentry, Datadog, or similar error tracking integration. Errors are logged via structlog but there is no alerting or aggregation service.
- Files: `backend/src/infrastructure/logging/` (structlog only)
- Blocks: Proactive production monitoring; crash reporting.

## Test Coverage Gaps

**Zero Frontend Tests:**
- What's not tested: Both frontend applications (`frontend/admin/` and `frontend/main/`) have no test files whatsoever.
- Files: All files under `frontend/admin/src/` and `frontend/main/`
- Risk: UI regressions, broken API integrations, and auth flow bugs go undetected.
- Priority: High -- the main frontend's auth flow (`TelegramProvider`, cookie helpers, BFF proxy) and checkout flow are critical paths with complex logic.

**Backend Catalog Domain: No Unit Tests for Product Aggregate:**
- What's not tested: The 2,220-line `Product` aggregate root (including `add_variant`, `add_sku`, `remove_sku`, `remove_variant`, status transitions, and media management) has no unit tests.
- Files: `backend/src/modules/catalog/domain/entities.py` (Product, ProductVariant, SKU entities)
- Risk: Product creation/SKU generation/variant management are core business operations. Logic errors in variant hash computation, duplicate detection, or status transitions would go unnoticed.
- Priority: High -- Product is the most complex aggregate in the system.

**Backend Catalog Commands: Sparse Test Coverage:**
- What's not tested: Of 45 catalog command handlers, only a handful have integration tests (e.g., `test_create_brand.py`). Most command handlers for attributes, templates, products, variants, and SKUs are untested.
- Files: `backend/src/modules/catalog/application/commands/` (45 files, ~2 tested)
- Risk: Business rule enforcement in commands like `generate_sku_matrix.py` (313 lines) and `bulk_assign_product_attributes.py` is unverified.
- Priority: High.

**Backend Geo Module: No Tests:**
- What's not tested: The entire geo module (city/region/country queries and repositories) has no test files.
- Files: `backend/src/modules/geo/`
- Risk: Low -- geo data is read-only reference data.
- Priority: Low.

**Image Backend: Minimal Coverage:**
- What's not tested: Router endpoints (upload, confirm, reupload, delete, external import), SSE streaming, and the S3 integration layer.
- Files: `image_backend/src/modules/storage/presentation/router.py`, `image_backend/src/infrastructure/storage/factory.py`
- Risk: The presigned-URL upload flow and image processing pipeline are untested end-to-end.
- Priority: Medium.

---

*Concerns audit: 2026-03-28*
