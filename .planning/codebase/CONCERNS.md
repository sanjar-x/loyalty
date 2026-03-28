# Codebase Concerns

**Analysis Date:** 2026-03-28

## Tech Debt

**Admin Frontend: Entirely JavaScript (no TypeScript):**
- Issue: The entire admin panel (`frontend/admin/src/`) is written in JavaScript (145 `.js`/`.jsx` files, zero `.ts`/`.tsx`). No type checking, no interfaces, no compile-time safety.
- Files: All 145 files under `frontend/admin/src/`
- Impact: Bugs from type mismatches surface only at runtime. Refactoring is risky without types. API contract changes silently break the admin UI.
- Fix approach: Incrementally migrate to TypeScript starting with service layer files (`frontend/admin/src/services/*.js`, `frontend/admin/src/hooks/*.js`), then components. Add a `tsconfig.json` and rename files one at a time.

**Admin Frontend: Hardcoded seed/mock data throughout services:**
- Issue: Most admin services return static seed data instead of calling the backend API. Orders, users, products, reviews, staff, referrals, and promocodes all read from `frontend/admin/src/data/*.js` mock files.
- Files: `frontend/admin/src/services/products.js`, `frontend/admin/src/services/users.js`, `frontend/admin/src/services/orders.js`, `frontend/admin/src/services/reviews.js`, `frontend/admin/src/services/staff.js`, `frontend/admin/src/services/referrals.js`, `frontend/admin/src/services/promocodes.js`
- Impact: The admin panel displays fake data. Any admin features that rely on these services (listing, filtering, status changes) are non-functional in production. Only category/brand/product-creation flows use real API calls.
- Fix approach: Replace seed-based service functions with fetch calls to backend BFF routes (the pattern already exists in `frontend/admin/src/services/categories.js` and `frontend/admin/src/services/products.js` for product creation). Build out corresponding backend endpoints for orders, reviews, referrals, and promocodes.

**Main Frontend: Stub hooks with no implementation:**
- Issue: Core e-commerce hooks are empty stubs that return static empty data.
- Files: `frontend/main/components/blocks/cart/useCart.ts` (all cart operations are no-ops), `frontend/main/lib/hooks/useItemFavorites.ts` (favorites not connected to API)
- Impact: Cart and favorites are completely non-functional. The checkout page (`frontend/main/app/checkout/page.tsx`, 1645 lines) renders a full UI but cannot actually process orders. "Add to Cart" and "Buy Now" on product pages are also stubs (`frontend/main/app/product/[id]/page.tsx:386-390`).
- Fix approach: Implement `useCart` with RTK Query endpoints backed by a cart backend API. Implement `useItemFavorites` similarly. The RTK Query infrastructure already exists in `frontend/main/lib/store/api.ts`.

**Main Frontend: Illegible auto-generated CSS class names:**
- Issue: 428 occurrences of opaque auto-generated CSS class names (`styles.c1`, `styles.c15`, `styles.c169`, `styles.tw6`, etc.) across 20+ component files. The corresponding CSS modules use these same meaningless names (e.g., `frontend/main/app/checkout/page.module.css` has 163 such classes across 1661 lines).
- Files: `frontend/main/app/checkout/page.tsx`, `frontend/main/app/trash/page.tsx`, `frontend/main/app/checkout/pickup/page.tsx`, `frontend/main/app/favorites/page.tsx`, `frontend/main/components/blocks/profile/*.tsx`, `frontend/main/components/blocks/favorites/*.tsx`, and others
- Impact: CSS is unmaintainable. Developers cannot understand what `.c169` styles without cross-referencing the CSS module. Refactoring or theming is extremely difficult.
- Fix approach: Rename classes to semantic names (e.g., `styles.c169` -> `styles.cvcError`, `styles.c15` -> `styles.cartItemCard`). This is a large but low-risk refactoring task. Do it file-by-file when touching components.

**Catalog Module: God-class entity file (2220 lines):**
- Issue: `backend/src/modules/catalog/domain/entities.py` is 2220 lines containing 9+ entity/aggregate classes (Brand, Category, AttributeTemplate, TemplateAttributeBinding, AttributeGroup, Attribute, ProductVariant, SKU, Product). The Product aggregate alone spans hundreds of lines.
- Files: `backend/src/modules/catalog/domain/entities.py`
- Impact: Difficult to navigate, test in isolation, and reason about. Merge conflicts are likely when multiple developers touch catalog features.
- Fix approach: Split into separate files per entity/aggregate: `brand.py`, `category.py`, `attribute.py`, `product.py`, etc. Re-export from `entities/__init__.py` to preserve the existing import paths.

**Legal documents not linked (About page):**
- Issue: Four legal document buttons on the About page have empty `onClick` handlers: user agreement, public offer, privacy policy, and personal data processing consent.
- Files: `frontend/main/app/profile/about/page.tsx:25-80`
- Impact: Users cannot access legally required documents. This may be a compliance issue depending on jurisdiction.
- Fix approach: Host legal documents as static pages or PDFs and link the buttons to them.

**Review submission not connected to API:**
- Issue: The review creation flow has a complete UI but the submit handler contains `// TODO: send to API when backend exists`.
- Files: `frontend/main/app/profile/purchased/review/[id]/ReviewClient.tsx:344`
- Impact: Users can fill in reviews but submissions are silently discarded.
- Fix approach: Build a reviews API endpoint on the backend and connect the frontend submit handler.

## Known Bugs

**No confirmed bugs identified.** The codebase is in an early development state with many features simply unimplemented rather than broken.

## Security Considerations

**No API-level rate limiting on backend:**
- Risk: Authentication endpoints (`/api/v1/auth/login`, `/api/v1/auth/register`) lack rate limiting, enabling brute-force attacks. Only the Telegram bot has throttling (`backend/src/bot/middlewares/throttling.py`).
- Files: `backend/src/bootstrap/web.py`, `backend/src/api/middlewares/`
- Current mitigation: None for HTTP API.
- Recommendations: Add a rate-limiting middleware (e.g., `slowapi` or custom Redis-based limiter) to auth endpoints at minimum. Consider per-IP and per-identity limits.

**CSP allows `unsafe-inline` and `unsafe-eval`:**
- Risk: Both frontends set `script-src 'self' 'unsafe-inline' 'unsafe-eval'` which effectively negates XSS protection from CSP.
- Files: `frontend/admin/next.config.js:16`, `frontend/main/next.config.ts` (main frontend has no CSP at all in its `next.config.ts`; only the middleware sets basic headers without CSP)
- Current mitigation: HttpOnly cookies prevent token theft via XSS. Next.js provides some built-in escaping.
- Recommendations: Tighten CSP to use nonces instead of `unsafe-inline`. Remove `unsafe-eval` if not required by dependencies.

**Main frontend has no CSP header:**
- Risk: The main customer-facing app (`frontend/main/next.config.ts`) does not set a Content-Security-Policy header at all (unlike the admin panel). The middleware (`frontend/main/middleware.ts`) sets `X-Content-Type-Options`, `X-Frame-Options`, and `Referrer-Policy` but not CSP.
- Files: `frontend/main/next.config.ts`, `frontend/main/middleware.ts`
- Current mitigation: None.
- Recommendations: Add CSP header via `next.config.ts` headers, matching or exceeding the admin panel configuration.

**Admin panel BFF does not forward auth tokens on API proxy:**
- Risk: The admin `backendFetch` helper (`frontend/admin/src/lib/api-client.js`) does not include authentication headers when proxying requests to the backend. Only the login route sets cookies. Admin API routes that need auth must manually read cookies and forward tokens.
- Files: `frontend/admin/src/lib/api-client.js`, `frontend/admin/src/app/api/` routes
- Current mitigation: Individual BFF routes handle auth tokens where needed.
- Recommendations: Add a centralized authenticated fetch helper that reads the access token cookie and includes `Authorization: Bearer <token>` on proxied requests, similar to the main frontend's `frontend/main/app/api/backend/[...path]/route.ts` proxy pattern.

**`window as any` for Telegram WebApp globals:**
- Risk: Multiple places use `(window as any).__LM_TG_INIT_DATA__` to pass Telegram initData between components, bypassing type safety.
- Files: `frontend/main/lib/telegram/TelegramProvider.tsx:169-172,264,269,357-358`, `frontend/main/components/blocks/telegram/TelegramAuthBootstrap.tsx:27,30`, `frontend/main/lib/telegram/core.ts:28`
- Current mitigation: Values are read back immediately in the same runtime context.
- Recommendations: Define a typed global interface (via `declare global`) or use a module-level variable instead of `window` globals.

**Hardcoded invite domain in admin staff page:**
- Risk: Staff invitation links use a hardcoded domain instead of environment variable.
- Files: `frontend/admin/src/app/admin/settings/staff/page.jsx:132`
- Current mitigation: TODO comment acknowledges the issue.
- Recommendations: Use `NEXT_PUBLIC_INVITE_DOMAIN` environment variable.

## Performance Bottlenecks

**Pagination uses COUNT(*) subquery for every paginated request:**
- Problem: The shared `paginate()` helper (`backend/src/shared/pagination.py:34`) wraps the entire base query in a subquery and does `SELECT COUNT(*)` on it, before running the actual paginated query. This doubles the DB work on every list endpoint.
- Files: `backend/src/shared/pagination.py`, used by 15+ query handlers in `backend/src/modules/catalog/application/queries/`, `backend/src/modules/identity/application/queries/`
- Cause: Standard approach but wasteful when total count is not always needed by the client.
- Improvement path: Consider cursor-based pagination for high-volume endpoints (catalog product listing, storefront queries). Alternatively, cache the count or only compute it when the client explicitly requests it.

**Raw SQL string concatenation in list queries:**
- Problem: `ListIdentitiesHandler` and `ListCustomersHandler` build SQL strings via concatenation with `f" ORDER BY {sort_col} {sort_dir}"`. While `sort_col` is validated against a whitelist (`_SORT_COLUMNS` dict), this pattern is fragile and prevents query plan caching.
- Files: `backend/src/modules/identity/application/queries/list_identities.py:162-163`, `backend/src/modules/identity/application/queries/list_customers.py:152`
- Cause: CQRS read-side queries use raw SQL for flexibility, but the dynamic ORDER BY prevents parameterization.
- Improvement path: Use SQLAlchemy Core expressions or build parameterized queries to allow PostgreSQL prepared statement caching.

**Checkout page: 1645 lines, 20+ useState hooks in single component:**
- Problem: The checkout page is a single monolithic component with 20+ `useState` calls, multiple modals (recipient, customs, card), session storage persistence, and complex validation logic.
- Files: `frontend/main/app/checkout/page.tsx` (1645 lines)
- Cause: All checkout logic was written as a single page component without extraction.
- Improvement path: Extract modal components (RecipientModal, CustomsModal, CardModal) into separate files. Move form state into a custom hook (e.g., `useCheckoutForm`). Move validation logic into utility functions.

## Fragile Areas

**Outbox relay: failed events are silently skipped:**
- Files: `backend/src/infrastructure/outbox/relay.py:162-169`
- Why fragile: When an event handler fails during relay processing, the exception is caught and the event is skipped (remains unprocessed in the DB). There is no retry mechanism or alerting beyond the log message. Events could sit indefinitely in the outbox table.
- Safe modification: The outbox relay runs every minute via TaskIQ scheduler. Changes to event handlers or the relay logic should be tested against failure scenarios.
- Test coverage: Unit tests exist in `backend/tests/unit/infrastructure/outbox/test_relay.py` and `backend/tests/unit/infrastructure/outbox/test_tasks.py`, but they may not cover all failure modes.

**Catalog domain entities: tightly coupled aggregate:**
- Files: `backend/src/modules/catalog/domain/entities.py`
- Why fragile: The Product aggregate contains variants, which contain SKUs, which contain attribute values. Nested operations like `find_sku` iterate all variants and all SKUs (O(V*S) linear scan). Adding new business rules to any level ripples through the aggregate.
- Safe modification: Always load via `get_for_update()` in `backend/src/modules/catalog/infrastructure/repositories/product.py:511-523` which uses `selectinload` chains to prevent lazy-load errors in async context.
- Test coverage: Only 238 LOC of unit tests for 21,853 LOC of catalog module source (1.1% test-to-source ratio). This is the least-tested module.

**Admin BFF API route pattern: no centralized auth middleware:**
- Files: `frontend/admin/src/app/api/` (30+ route files)
- Why fragile: Each BFF API route independently handles authentication, token forwarding, and error responses. There is no shared middleware or wrapper.
- Safe modification: When adding new admin API routes, copy the auth pattern from existing routes like `frontend/admin/src/app/api/auth/me/route.js`.
- Test coverage: Zero frontend tests exist anywhere in the project.

## Scaling Limits

**Single outbox relay table with polling:**
- Current capacity: Relay polls every minute with batch size 100. Throughput: ~100 events/minute.
- Limit: Under high write load (hundreds of product updates/minute), the outbox table grows faster than the relay can drain it, causing event delivery latency to increase.
- Scaling path: Increase batch size, decrease poll interval, or switch to PostgreSQL LISTEN/NOTIFY for push-based relay. Long-term: consider a dedicated message broker (RabbitMQ is already available via `RABBITMQ_PRIVATE_URL` in config but not used for outbox relay).

**Image processing: single-file serial pipeline:**
- Current capacity: Each image is downloaded, processed, and re-uploaded serially in `image_backend/src/modules/storage/presentation/tasks.py:29-110`. Processing runs in a thread pool but uploads are sequential.
- Limit: Large batches of product images (e.g., bulk product imports with 100 images each) will bottleneck on the image processing queue.
- Scaling path: Parallelize variant uploads with `asyncio.gather()`. Scale horizontally by running multiple TaskIQ workers.

## Dependencies at Risk

**Python 3.14 (pre-release):**
- Risk: The backend uses Python 3.14 (evidenced by `.venv/include/site/python3.14/`). Python 3.14 is still in development/pre-release as of this analysis date.
- Impact: Library incompatibilities, undiscovered runtime bugs, and lack of production-hardened releases.
- Migration plan: Consider pinning to Python 3.12 or 3.13 (latest stable) for production deployments.

## Missing Critical Features

**No order/checkout backend:**
- Problem: The frontend has a complete checkout UI (`frontend/main/app/checkout/page.tsx`) but there is no order or checkout module in the backend (`backend/src/modules/`). The backend has catalog, identity, user, supplier, and geo modules but no order processing.
- Blocks: End-to-end purchasing, payment processing, order tracking, and all order-related admin features.

**No payment integration:**
- Problem: The checkout page displays payment method options (SBP, card, split payment) but there is no payment provider integration on the backend.
- Blocks: Revenue generation and transaction processing.

**No cart backend:**
- Problem: The cart hook (`frontend/main/components/blocks/cart/useCart.ts`) is a complete stub. There is no cart module or storage mechanism in the backend.
- Blocks: Users cannot add items to cart or proceed through checkout.

**No search/filtering backend for storefront:**
- Problem: The storefront query handler exists (`backend/src/modules/catalog/application/queries/storefront.py`) but the search page (`frontend/main/app/search/page.tsx`, 1159 lines) has extensive filter UI (price, size, brand, category) that needs corresponding backend endpoints.
- Blocks: Product discovery and catalog browsing.

## Test Coverage Gaps

**Frontend: Zero tests across both apps:**
- What's not tested: All 154 TypeScript files in `frontend/main/` and all 145 JavaScript files in `frontend/admin/src/` have no tests whatsoever.
- Files: Entire `frontend/` directory
- Risk: Any refactoring, API contract change, or component modification could break the UI silently. The checkout page alone (1645 lines) has complex validation logic that is untested.
- Priority: High

**Catalog module: 1.1% test ratio (worst in codebase):**
- What's not tested: The catalog module has 21,853 LOC of source but only 796 LOC of tests (3 unit test files, 6 integration test files). Of the 46 command handlers in `backend/src/modules/catalog/application/commands/`, only `create_brand` and `sync_product_media` have tests.
- Files: `backend/src/modules/catalog/application/commands/` (44 untested commands including `create_product.py`, `add_variant.py`, `add_sku.py`, `change_product_status.py`, `generate_sku_matrix.py`, etc.)
- Risk: Product creation, variant management, SKU generation, attribute assignment, and category operations are all untested. These are core business operations.
- Priority: High

**Geo module: Zero tests:**
- What's not tested: The entire geo module (15 source files) has no unit or integration tests.
- Files: `backend/src/modules/geo/` (models, repositories, queries for countries, subdivisions, currencies)
- Risk: Geographic data queries could return incorrect results without detection.
- Priority: Medium

**User module: No integration tests:**
- What's not tested: The user module has 7 unit test files but zero integration tests. Consumer handlers (`identity_events.py`, 270 lines) that create customer profiles and handle GDPR anonymization are tested only with mocks.
- Files: `backend/src/modules/user/application/consumers/identity_events.py`, `backend/src/modules/user/infrastructure/repositories/`
- Risk: Integration between identity events and user profile creation could fail without detection.
- Priority: Medium

**Image backend: Minimal test coverage:**
- What's not tested: 4,895 LOC of source with only 696 LOC of tests (5 test files). Image processing pipeline, S3 upload/download, and orphan cleanup are not integration-tested.
- Files: `image_backend/src/modules/storage/presentation/tasks.py`, `image_backend/src/modules/storage/infrastructure/service.py`
- Risk: Image processing failures could corrupt product media without detection.
- Priority: Medium

---

*Concerns audit: 2026-03-28*
