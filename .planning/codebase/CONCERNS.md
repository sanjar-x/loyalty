# Codebase Concerns

**Analysis Date:** 2026-03-28

## Tech Debt

**Stubbed-out cart and favorites hooks (frontend/main):**
- Issue: `useCart` at `frontend/main/components/blocks/cart/useCart.ts` returns hardcoded empty arrays and no-op callbacks. Every cart operation (add, remove, setQuantity, toggleFavorite) does nothing. Similarly, `useItemFavorites` at `frontend/main/lib/hooks/useItemFavorites.ts` is completely stubbed with `// TODO: connect to API`.
- Files: `frontend/main/components/blocks/cart/useCart.ts`, `frontend/main/lib/hooks/useItemFavorites.ts`
- Impact: Cart and favorites functionality is non-functional for end users. The checkout page (`frontend/main/app/checkout/page.tsx`) imports useCart but operates on empty data. Any features depending on cart state (checkout flow, badge counts in `frontend/main/components/layout/Footer.tsx`) are broken.
- Fix approach: Implement RTK Query endpoints in `frontend/main/lib/store/api.ts` for cart CRUD and favorites, then wire hooks to use them. Backend cart/favorites endpoints need to be built first if not present.

**Non-semantic CSS class names across main frontend:**
- Issue: CSS module classes use auto-generated names like `.c1`, `.c170`, `.tw67` instead of descriptive names. 448 occurrences across 24 files.
- Files: `frontend/main/app/checkout/page.module.css` (1661 lines), `frontend/main/app/checkout/pickup/page.module.css`, `frontend/main/app/trash/page.module.css`, and others.
- Impact: CSS is unreadable and unmaintainable. Developers cannot understand layout intent from class names. Refactoring any component requires tracing numeric class names back and forth between TSX and CSS files.
- Fix approach: Rename classes to semantic names (e.g., `.c170` to `.cardHolderError`) incrementally per page component. Prioritize `checkout/page.module.css` and `checkout/pickup/page.module.css` as the largest files.

**Admin frontend entirely in JavaScript (no TypeScript):**
- Issue: The admin app (`frontend/admin/src/`) contains 145 `.js`/`.jsx` files and zero `.ts`/`.tsx` files, while the main app is fully TypeScript (154 `.ts`/`.tsx` files, 0 JS).
- Files: All files under `frontend/admin/src/`
- Impact: No compile-time type safety in the admin panel. Refactoring is error-prone. API response shapes are not validated. Inconsistency between the two frontend apps makes it harder for developers to context-switch.
- Fix approach: Gradually migrate admin files from JS to TSX, starting with the API proxy layer (`frontend/admin/src/lib/api-client.js`, `frontend/admin/src/proxy.js`) and shared utilities (`frontend/admin/src/lib/auth.js`, `frontend/admin/src/lib/utils.js`).

**Monolithic page components (1000+ lines):**
- Issue: Several page components contain entire features in a single file with inline state, validation, modals, and rendering.
- Files: `frontend/main/app/checkout/page.tsx` (1645 lines), `frontend/main/app/checkout/pickup/page.tsx` (1597 lines), `frontend/main/app/search/page.tsx` (1159 lines), `frontend/main/app/product/[id]/page.tsx` (790 lines), `frontend/main/app/trash/page.tsx` (753 lines)
- Impact: Difficult to test, review, or modify individual features. State logic is entangled with UI rendering. Custom hooks like `useAnimatedPresence` are defined inline instead of extracted.
- Fix approach: Extract custom hooks (e.g., `useCheckoutRecipient`, `useCheckoutCard`, `useCheckoutCustoms`), break modals into separate components, and move validation logic to dedicated utilities.

**Duplicated components and patterns:**
- Issue: `StatsIcon` is duplicated between `frontend/admin/src/app/admin/settings/staff/page.jsx` and `frontend/admin/src/app/admin/settings/promocodes/page.jsx` (both files note the TODO). API proxy patterns are also reimplemented differently between the admin (`frontend/admin/src/lib/api-client.js` with `backendFetch`) and main (`frontend/main/app/api/backend/[...path]/route.ts` with a full proxy) frontend apps.
- Files: `frontend/admin/src/app/admin/settings/staff/page.jsx`, `frontend/admin/src/app/admin/settings/promocodes/page.jsx`, `frontend/admin/src/lib/api-client.js`, `frontend/main/app/api/backend/[...path]/route.ts`
- Impact: Bug fixes must be applied in multiple places. Inconsistent proxy behavior between admin and main apps.
- Fix approach: Extract `StatsIcon` to a shared component. Consider unifying the backend proxy approach across both apps.

**Many unconnected frontend features (TODO: connect to API):**
- Issue: Multiple frontend features are marked as not yet wired to backend APIs.
- Files:
  - `frontend/main/components/blocks/catalog/BrandsList.tsx:51` - brand listing
  - `frontend/main/app/product/[id]/page.tsx:386,390` - product page features
  - `frontend/main/app/profile/about/page.tsx:25,43,61,79` - legal document links (user agreement, public offer, privacy policy, consent)
  - `frontend/main/app/profile/settings/page.tsx:424,451` - pickup point management
  - `frontend/main/app/profile/purchased/review/[id]/ReviewClient.tsx:344` - review submission
  - `frontend/admin/src/components/admin/TopMetrics.jsx:9` - date range filter
  - `frontend/admin/src/components/admin/products/ProductMetrics.jsx:11,17` - product metrics (hardcoded percentages)
- Impact: UI is rendered but features are non-functional. Users see buttons and forms that do nothing.
- Fix approach: Prioritize by user-facing impact. Review submission, brand listing, and pickup point management should be connected first.

**Product entity file at 2220 lines:**
- Issue: `backend/src/modules/catalog/domain/entities.py` contains Brand, Category, AttributeTemplate, TemplateAttributeBinding, AttributeGroup, Attribute, AttributeValue, ProductVariant, SKU, and Product domain entities all in a single file.
- Files: `backend/src/modules/catalog/domain/entities.py` (2220 lines)
- Impact: Hard to navigate and maintain. A change to Brand entity requires opening a 2200-line file. Git merge conflicts are more likely.
- Fix approach: Split into separate files per aggregate root: `brand.py`, `category.py`, `attribute_template.py`, `attribute.py`, `product.py`. Keep a barrel `__init__.py` re-exporting all entities for backward compatibility.

## Known Bugs

**Order details page returns null (no data source):**
- Symptoms: `OrderDetailsClient.tsx` comments say "Previously used getMockOrderById - now returns null (no mock data)". The order detail view renders with no data.
- Files: `frontend/main/app/profile/orders/[id]/OrderDetailsClient.tsx:357`
- Trigger: Navigate to any order detail page.
- Workaround: None. The page is non-functional.

**Console.log left in production code:**
- Symptoms: Debug `console.log` statements in button onClick handlers.
- Files: `frontend/main/app/profile/reviews/[brand]/page.tsx:545,552` -- `console.log("buyNow", ...)` and `console.log("addToCart", ...)` in click handlers that should trigger real actions.
- Trigger: Click "Buy Now" or "Add to Cart" on the brand reviews page.
- Workaround: None. The buttons only log to console.

## Security Considerations

**Sensitive PII stored in localStorage (checkout page):**
- Risk: Passport series, passport number, issue date, birth date, INN (tax ID), and payment card details (last 4, expiry, holder name) are persisted in `localStorage` across sessions. localStorage is accessible to any JavaScript running on the same origin, including XSS payloads and browser extensions.
- Files: `frontend/main/app/checkout/page.tsx` (lines 99-191, keys: `loyaltymarket_checkout_customs_v1`, `loyaltymarket_checkout_card_v1`, `loyaltymarket_checkout_recipient_v1`)
- Current mitigation: None. Data is stored in plaintext JSON.
- Recommendations: Move sensitive data to `sessionStorage` (cleared on tab close) at minimum. For card data, use a payment gateway's hosted fields or tokenization service instead of collecting card numbers directly. For passport data, avoid client-side persistence entirely and submit directly to the backend.

**Payment card numbers handled directly in frontend:**
- Risk: The checkout page collects full card numbers, expiry, and CVV in browser state (`CheckoutCardDraft` interface with `numberDigits`, `exp`, `cvc`, `holder`). This likely violates PCI-DSS requirements. Card data flows through application JavaScript before (presumably) being sent to a backend.
- Files: `frontend/main/app/checkout/page.tsx` (lines 72-77, 1510-1595)
- Current mitigation: Only `last4`, `exp`, and `holder` are persisted to localStorage. Full card number and CVV are kept only in React state.
- Recommendations: Replace with a PCI-compliant payment gateway integration (Stripe Elements, Yandex Pay, etc.) that uses iframe-based card collection.

**No API rate limiting on HTTP endpoints:**
- Risk: The backend API has no rate limiting middleware. Only the Telegram bot has throttling (`backend/src/bot/middlewares/throttling.py`). Authentication endpoints (`/api/v1/auth/login`, `/api/v1/auth/telegram`) are vulnerable to brute-force attacks.
- Files: `backend/src/bootstrap/web.py`, `backend/src/bot/middlewares/throttling.py`
- Current mitigation: JWT expiry (15 min access, 30 day refresh) limits damage from compromised tokens.
- Recommendations: Add rate limiting middleware (e.g., slowapi or a custom Redis-based limiter). Prioritize auth endpoints, then apply globally with per-IP limits.

**Image backend external import lacks SSRF protection:**
- Risk: The `POST /media/external` endpoint accepts an arbitrary URL and fetches it server-side using `httpx.AsyncClient`. No validation prevents requests to internal/private IP ranges (127.0.0.1, 10.x.x.x, 169.254.x.x, etc.).
- Files: `image_backend/src/modules/storage/presentation/router.py` (lines 337-404), `image_backend/src/modules/storage/presentation/schemas.py` (line 53-54 -- `url: str` with no validation)
- Current mitigation: 10 MB file size limit and 30s timeout. API key required (but disabled when `INTERNAL_API_KEY` is empty).
- Recommendations: Validate the URL scheme (only `http`/`https`), resolve DNS and reject private/loopback/link-local IP ranges before fetching. Add URL pattern allowlist if possible.

**Image backend API key auth can be disabled:**
- Risk: When `INTERNAL_API_KEY` is empty string (the default), the `verify_api_key` dependency returns immediately without checking, making all image backend endpoints publicly accessible.
- Files: `image_backend/src/api/dependencies/auth.py` (lines 30-31)
- Current mitigation: Presumably the key is set in production deployment.
- Recommendations: Fail-closed: require the key in non-dev environments. Add an explicit check like `if settings.ENVIRONMENT != "dev" and not internal_key: raise`.

**Debug/mock auth generates predictable tokens:**
- Risk: In development mode, the Telegram auth endpoint generates tokens like `debug_{tg_id}_{timestamp}` which are not real JWTs and bypass all backend authentication.
- Files: `frontend/main/app/api/auth/telegram/route.ts` (lines 104-111), `frontend/main/lib/auth/debug.ts` (hardcoded debug user with `tg_id: "7427756366"`)
- Current mitigation: Protected by `NODE_ENV !== "production"` check and localhost-only guard in `isLocalBrowserDebugRequest`.
- Recommendations: Ensure `BROWSER_DEBUG_AUTH` env var is never set in production. Consider removing the mock token fallback entirely and always requiring a running backend.

**Hardcoded admin domain URL:**
- Risk: Invite link generation uses a hardcoded domain: `https://invite.admin.loyaltymarket.ru/{token}`.
- Files: `frontend/admin/src/app/admin/settings/staff/page.jsx:133`
- Current mitigation: None.
- Recommendations: Move domain to `NEXT_PUBLIC_INVITE_DOMAIN` environment variable as the TODO suggests.

## Performance Bottlenecks

**Linear SKU search in Product aggregate:**
- Problem: `find_sku()` and `remove_sku()` iterate through all variants and all SKUs with nested loops. `add_sku()` checks variant hash uniqueness across all SKUs.
- Files: `backend/src/modules/catalog/domain/entities.py` (lines 2157-2195)
- Cause: SKUs are stored as flat lists on variants. No index/hash map for lookup.
- Improvement path: For products with many variants and SKUs, consider adding a `_sku_by_id` dict for O(1) lookup, or a `_variant_hashes` set for O(1) duplicate checking. Only matters for products with 50+ SKUs.

**Checkout page single-file bundle size:**
- Problem: The checkout page (`frontend/main/app/checkout/page.tsx`, 1645 lines) and its CSS module (1661 lines) are loaded as a single chunk. All modals (recipient, customs, card) and their validation logic are included even if the user never opens them.
- Files: `frontend/main/app/checkout/page.tsx`, `frontend/main/app/checkout/page.module.css`
- Cause: Everything is in one "use client" component with no code splitting.
- Improvement path: Use `React.lazy()` and `Suspense` for modals. Extract modal components to separate files that are dynamically imported.

## Fragile Areas

**Checkout page state management (localStorage + React state):**
- Files: `frontend/main/app/checkout/page.tsx` (lines 97-191)
- Why fragile: State is split across 5 localStorage keys and React state. Read/write functions have manual JSON parse/serialize with empty catch blocks. Any schema change to stored data (e.g., adding a field to `CheckoutRecipient`) silently returns `null` on read, causing the form to reset.
- Safe modification: Always maintain backward compatibility in read functions. Add version keys to localStorage data for migration support.
- Test coverage: Zero tests. No unit tests for any frontend code.

**Outbox relay (event-driven messaging):**
- Files: `backend/src/infrastructure/outbox/relay.py`, `backend/src/infrastructure/outbox/tasks.py`
- Why fragile: Uses raw SQL with `FOR UPDATE SKIP LOCKED` for concurrent processing. The event handler registry is a module-level mutable dict (`_EVENT_HANDLERS`). If a handler is not registered for an event type, the event is silently skipped (logged as warning).
- Safe modification: Always register handlers before starting the relay. Test with concurrent workers to verify SKIP LOCKED behavior.
- Test coverage: Unit tests exist (`backend/tests/unit/infrastructure/outbox/test_relay.py`, `backend/tests/unit/infrastructure/outbox/test_tasks.py`).

**Empty catch blocks throughout frontend:**
- Files: At least 30+ instances across `frontend/main/` and `frontend/admin/` (found in `TelegramProvider.tsx`, `checkout/page.tsx`, `InviteLinkActions.tsx`, `PriceSheet.tsx`, and many others)
- Why fragile: Errors are swallowed silently. When something breaks in production, there is no visibility. localStorage parsing failures, clipboard API failures, and Telegram SDK failures all fail silently.
- Safe modification: Replace empty `catch {}` blocks with at minimum `catch { /* intentionally ignored: clipboard not supported */ }` comments, or better, log to an error tracking service.
- Test coverage: None.

## Scaling Limits

**Single database migration file:**
- Current capacity: The backend has a single Alembic migration (`backend/alembic/versions/2026/03/27_0911_19_7ce70774f240_init.py`). The image backend has one migration as well.
- Limit: As the schema evolves, having started from a single init migration means there is no migration history to rollback to intermediate states.
- Scaling path: Standard practice -- create incremental migrations for every schema change going forward. Never modify the init migration.

**No CI/CD pipeline:**
- Current capacity: No GitHub Actions, GitLab CI, or any CI/CD configuration detected. No root `.gitignore`. No docker-compose for local development.
- Limit: All testing, linting, and deployment are manual. No automated quality gates prevent broken code from being merged.
- Scaling path: Add GitHub Actions with: lint (ruff + eslint), test (pytest + vitest), build check (docker build), and deploy stages.

## Dependencies at Risk

**Python 3.14 (pre-release):**
- Risk: The Dockerfile uses `python:3.14-slim-trixie`. Python 3.14 is not yet released (scheduled for October 2026). Using a pre-release Python version in production risks encountering bugs in the runtime itself.
- Files: `backend/Dockerfile`
- Impact: Build failures, runtime bugs, or incompatible packages when the final 3.14 release changes behavior.
- Migration plan: Pin to a stable Python version (3.12 or 3.13) for production. Use 3.14 only in a development/testing branch.

## Missing Critical Features

**No frontend test suite:**
- Problem: Both frontend applications (admin and main) have zero test files. No `.test.ts`, `.test.tsx`, `.spec.ts`, or `.spec.tsx` files exist anywhere under `frontend/`.
- Blocks: Refactoring any component safely. Validating checkout flow logic. Ensuring Telegram auth flow works after changes.

**No error monitoring/tracking:**
- Problem: No Sentry, Datadog, LogRocket, or similar error tracking integration in either frontend app. Backend uses structlog for logging but no external monitoring service.
- Blocks: Detecting production errors. Understanding user-facing failures. Measuring error rates.

## Test Coverage Gaps

**No tests for geo module:**
- What's not tested: The entire `backend/src/modules/geo/` module (countries, currencies, subdivisions, languages) has no unit or integration tests.
- Files: `backend/src/modules/geo/domain/`, `backend/src/modules/geo/infrastructure/`, `backend/src/modules/geo/application/`
- Risk: Geo data queries, value object validation (currency codes, country codes), and i18n handling could break unnoticed.
- Priority: Medium -- geo data is mostly reference data loaded from seeds.

**No tests for bot module:**
- What's not tested: All Telegram bot handlers, callbacks, keyboards, and middlewares.
- Files: `backend/src/bot/handlers/`, `backend/src/bot/callbacks/`, `backend/src/bot/middlewares/`, `backend/src/bot/keyboards/`
- Risk: Bot command handling, user identification middleware, throttling behavior, and error handling could break without detection.
- Priority: Medium -- bot is an auxiliary interface.

**Catalog module has low test coverage relative to complexity:**
- What's not tested: Only 9 test files for the largest module (2220-line entity file, 913-line models file, 1354-line schemas file, 557-line product repository). Product CRUD commands, SKU generation, media sync, attribute value operations, and storefront queries lack dedicated tests.
- Files: `backend/src/modules/catalog/application/commands/` (15+ command handlers), `backend/src/modules/catalog/application/queries/` (7 query handlers)
- Risk: The most business-critical module (product catalog) has the highest risk of undetected regressions.
- Priority: High -- catalog is the core business domain.

**Zero frontend tests:**
- What's not tested: All 154 TypeScript files in the main app and 145 JavaScript files in the admin app.
- Files: All files under `frontend/main/` and `frontend/admin/src/`
- Risk: Checkout validation logic, authentication flows, Telegram SDK integration, cart behavior, search/filter functionality -- all untested.
- Priority: High -- user-facing code with complex client-side logic.

---

*Concerns audit: 2026-03-28*
