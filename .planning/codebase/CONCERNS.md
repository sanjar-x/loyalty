# Codebase Concerns

**Analysis Date:** 2026-03-29

## Tech Debt

**Domain Layer Imports Application Layer:**
- Issue: `backend/src/modules/catalog/domain/value_objects.py` (line 14) imports `DEFAULT_CURRENCY`, `DEFAULT_SEARCH_WEIGHT`, and `REQUIRED_LOCALES` from `backend/src/modules/catalog/application/constants.py`. This violates the Dependency Inversion Principle -- the domain layer must not depend on outer layers.
- Files: `backend/src/modules/catalog/domain/value_objects.py`, `backend/src/modules/catalog/application/constants.py`
- Impact: The architecture fitness test in `backend/tests/architecture/test_boundaries.py` (Rule 1: domain purity, Rule 7: no reverse deps) should fail on this import, meaning either the test is not running or using a library that misses it. New developers may introduce more domain-to-application leaks following this precedent.
- Fix approach: Move `DEFAULT_CURRENCY`, `DEFAULT_SEARCH_WEIGHT`, and `REQUIRED_LOCALES` into a new file `backend/src/modules/catalog/domain/constants.py`. Update imports in both the domain and application layers accordingly.

**Cross-Module Coupling: Catalog -> Supplier:**
- Issue: `CreateProductHandler` in the catalog module imports directly from the supplier module's domain layer (`SourceUrlRequiredError`, `ISupplierQueryService`, `SupplierType`). This creates a tight coupling between bounded contexts.
- Files: `backend/src/modules/catalog/application/commands/create_product.py` (lines 25-27)
- Impact: The architecture boundary test (`backend/tests/architecture/test_boundaries.py`) `MODULES` list does not include `"supplier"` or `"geo"`, so this violation is not detected. Changes to the supplier domain will break catalog compilation.
- Fix approach: Define a cross-module interface (anti-corruption layer) in the catalog module or shared kernel that abstracts the supplier validation. Add `"supplier"` and `"geo"` to the `MODULES` list in `backend/tests/architecture/test_boundaries.py`.

**`source_url` Not Updatable After Creation:**
- Issue: `Product._UPDATABLE_FIELDS` (line 219-228 in `backend/src/modules/catalog/domain/entities/product.py`) does not include `"source_url"`. The `ProductUpdateRequest` schema also lacks this field. Once set at creation, `source_url` can never be changed via the API.
- Files: `backend/src/modules/catalog/domain/entities/product.py`, `backend/src/modules/catalog/presentation/schemas.py`
- Impact: Cross-border products with incorrect or outdated source URLs cannot have their URLs corrected without direct database manipulation.
- Fix approach: Add `"source_url"` to `Product._UPDATABLE_FIELDS` and add a corresponding field to `ProductUpdateRequest` and `UpdateProductCommand`.

**Catalog Domain Events Persisted but Never Consumed:**
- Issue: The catalog module defines 28+ domain event types in `backend/src/modules/catalog/domain/events.py` (e.g., `BrandCreatedEvent`, `ProductStatusChangedEvent`, `CategoryUpdatedEvent`), and all are persisted to the `outbox_messages` table via the UnitOfWork. However, only 3 identity-related event types are registered as handlers in `backend/src/infrastructure/outbox/tasks.py`. All catalog events accumulate in the outbox until the 7-day prune job deletes them.
- Files: `backend/src/modules/catalog/domain/events.py` (28+ event classes), `backend/src/infrastructure/outbox/tasks.py` (only 3 registered handlers)
- Impact: Wasted database storage and I/O from writing events that are never consumed. The outbox relay processes these events each minute, looks up the handler, finds none, logs a warning, and marks them as processed -- unnecessary work.
- Fix approach: Either (a) register consumers for catalog events that need downstream processing (e.g., search index updates, cache invalidation), or (b) stop emitting events that have no consumers by removing `add_domain_event()` calls from entities that do not yet need eventing.

**Settings Singleton Coupling in JWT Provider:**
- Issue: `JwtTokenProvider` in `backend/src/infrastructure/security/jwt.py` imports `settings` directly from `backend/src/bootstrap/config.py` at module level, using `settings.SECRET_KEY` and `settings.ALGORITHM` inside methods. This tightly couples the infrastructure to the config module and makes unit testing require a real `.env` file or monkeypatching.
- Files: `backend/src/infrastructure/security/jwt.py`, `backend/src/infrastructure/cache/provider.py`, `backend/src/infrastructure/database/provider.py`
- Impact: Tests that import these modules require all env vars to be set. Makes isolated unit testing difficult.
- Fix approach: Inject configuration values (secret key, algorithm, expiry) via constructor parameters through the DI container instead of reading the global singleton.

**Defensive `getattr` in Product Router:**
- Issue: `router_products.py` (line 319-320) uses `getattr(a, "attribute_value_code", "")` and `getattr(a, "attribute_value_name_i18n", {})` to access fields that are already defined with defaults on `ProductAttributeReadModel` in `read_models.py` (lines 348-349).
- Files: `backend/src/modules/catalog/presentation/router_products.py` (lines 319-320), `backend/src/modules/catalog/application/queries/read_models.py` (lines 348-349)
- Impact: Minor: no functional bug, but the defensive coding obscures the actual contract and suggests the read model was incomplete at some point. Misleads future developers.
- Fix approach: Replace `getattr` with direct attribute access (`a.attribute_value_code`, `a.attribute_value_name_i18n`).

**Hardcoded Invite Domain in Admin Frontend:**
- Issue: Staff invitation link generation uses a hardcoded domain `https://invite.admin.loyaltymarket.ru/`.
- Files: `frontend/admin/src/app/admin/settings/staff/page.jsx` (line 133)
- Impact: Cannot deploy the admin to a different domain without code changes.
- Fix approach: Use `NEXT_PUBLIC_INVITE_DOMAIN` environment variable as the TODO comment already suggests.

**Duplicated `StatsIcon` Component:**
- Issue: The `StatsIcon` SVG component is duplicated in two admin pages.
- Files: `frontend/admin/src/app/admin/settings/staff/page.jsx`, `frontend/admin/src/app/admin/settings/promocodes/page.jsx`
- Impact: Any visual change must be applied in two places.
- Fix approach: Extract to a shared component at `frontend/admin/src/components/icons/StatsIcon.jsx`.

## Known Bugs

**No bugs confirmed** at this time. The codebase has no `FIXME` or `BUG` comments. The areas below are potential issues that require verification.

**Pagination Count Query May Be Expensive:**
- Symptoms: `backend/src/shared/pagination.py` fires a `SELECT COUNT(*)` subquery for every paginated list endpoint, even when total count is not needed by the consumer.
- Files: `backend/src/shared/pagination.py` (line 34)
- Trigger: Any paginated listing with complex filters (e.g., products filtered by status + brand + published_after).
- Workaround: None currently; all paginated endpoints pay the count cost.

## Security Considerations

**No API-Level Rate Limiting:**
- Risk: The REST API has no rate limiting middleware. The bot has Redis-backed throttling (`backend/src/bot/middlewares/throttling.py`), but HTTP endpoints are unprotected. An attacker can brute-force auth endpoints or flood mutation endpoints without any throttle.
- Files: `backend/src/bootstrap/web.py` (no rate limiting middleware), `backend/src/api/middlewares/` (only access logging)
- Current mitigation: Railway PaaS may provide basic DDoS protection at the platform level. JWT expiry (15 min) limits token abuse window.
- Recommendations: Add a rate limiting middleware (e.g., `slowapi` or custom Redis-based limiter). Prioritize auth endpoints (`/api/v1/auth/login`, `/api/v1/auth/telegram`) and mutation endpoints.

**User-Supplied Regex in Attribute Validation Rules (Potential ReDoS):**
- Risk: Attribute validation rules accept a `pattern` field (regex string) via `backend/src/modules/catalog/domain/value_objects.py` `_validate_string_rules()`. This regex is stored in the database and could later be compiled against user input, enabling Regular Expression Denial of Service (ReDoS) attacks.
- Files: `backend/src/modules/catalog/domain/value_objects.py` (lines 193-254), `backend/src/modules/catalog/presentation/schemas.py` (attribute schemas)
- Current mitigation: The validation function only checks that `pattern` is a string -- it does not compile or test the regex. Whether the regex is ever applied to product data at runtime needs verification.
- Recommendations: Add pattern length limits and regex complexity validation (e.g., reject patterns with nested quantifiers). Consider using Google RE2 for safe regex evaluation.

**Shallow Health Check:**
- Risk: The `/health` endpoint returns `{"status": "ok"}` without verifying database, Redis, or RabbitMQ connectivity. A load balancer using this endpoint may route traffic to an instance with a broken DB connection.
- Files: `backend/src/bootstrap/web.py` (lines 99-102)
- Current mitigation: None.
- Recommendations: Add a `/health/ready` readiness probe that checks: (a) PostgreSQL connection via a lightweight query, (b) Redis ping, (c) optionally RabbitMQ connection. Keep the existing `/health` as a liveness probe (fast, no dependencies).

**Access Token Window After Logout:**
- Risk: After logout or token revocation, the JWT access token remains valid until its natural expiry (default 15 minutes). This is a documented design decision (see comment in `backend/src/modules/identity/presentation/dependencies.py` lines 59-64) but still presents a risk window.
- Files: `backend/src/modules/identity/presentation/dependencies.py` (lines 59-64)
- Current mitigation: Token version validation (`tv` claim) catches bulk invalidation (password reset, account deactivation). Individual session revocation is NOT covered by this mechanism.
- Recommendations: If the 15-minute window is unacceptable, add a lightweight Redis token blacklist checked in `get_auth_context()`.

## Performance Bottlenecks

**Product Aggregate Eager Loading Pattern:**
- Problem: `ProductRepository.get_with_variants()` and `get_for_update_with_variants()` use nested `selectinload` chains: Product -> Variants -> SKUs -> AttributeValues. For a product with many variants and SKUs, this generates multiple SELECT queries (one per `selectinload` level).
- Files: `backend/src/modules/catalog/infrastructure/repositories/product.py` (lines 506-531, 533-557)
- Cause: `selectinload` issues one IN-query per relationship level. With 10 variants x 50 SKUs x 3 attributes each, that's 4 queries loading potentially thousands of rows.
- Improvement path: For read-only queries, consider a flat SQL query with JOINs returning denormalized data. For mutations, the current pattern is acceptable since `FOR UPDATE` is needed. Monitor query count and latency as product complexity grows.

**Pagination COUNT(*) on Every Request:**
- Problem: Every paginated endpoint runs two queries: a `COUNT(*)` and the actual `SELECT`. The count query can be slow on large tables with complex filters since it must scan all matching rows.
- Files: `backend/src/shared/pagination.py` (line 34)
- Cause: The `paginate()` helper unconditionally computes total count even when the frontend only needs "has more" semantics.
- Improvement path: Offer a cursor-based pagination alternative for high-volume endpoints (product listing, order listing). For offset pagination, consider caching the count or using `EXPLAIN` estimates for approximate counts.

**No Product Listing Filter by Category:**
- Problem: `ListProductsQuery` in `backend/src/modules/catalog/application/queries/list_products.py` supports filtering by `status` and `brand_id` but NOT by `primary_category_id`. The storefront requires category-based browsing.
- Files: `backend/src/modules/catalog/application/queries/list_products.py` (lines 27-46)
- Cause: The filter was not implemented.
- Improvement path: Add `primary_category_id: uuid.UUID | None = None` to `ListProductsQuery` and a corresponding `.where()` clause. The existing `ix_products_catalog_listing` index already covers `(brand_id, primary_category_id, status, popularity_score)`.

## Fragile Areas

**Product Aggregate State Synchronization:**
- Files: `backend/src/modules/catalog/infrastructure/repositories/product.py` (`_sync_variants`, `_sync_skus_for_variant` methods, lines 304-360)
- Why fragile: The Data Mapper reconciliation between domain entities and ORM models uses list-based iteration and set-diff logic to detect additions, updates, and removals of child entities (variants and SKUs). If the domain entity mutation order is unexpected (e.g., variant removed then re-added with same ID), the ORM reconciliation could produce incorrect results.
- Safe modification: Always test product mutations through the full repository round-trip (create -> mutate -> update -> re-read). The integration tests in `backend/tests/integration/modules/catalog/infrastructure/repositories/test_product.py` cover the happy path but should be expanded for edge cases.
- Test coverage: Happy path covered; edge cases (concurrent variant removal, re-adding deleted SKUs, soft-delete cascade) partially covered.

**ORM-to-Domain Mapping for Products:**
- Files: `backend/src/modules/catalog/infrastructure/repositories/product.py` (`_to_domain`, `_to_domain_without_skus`, lines 241-261)
- Why fragile: Two different mapping methods exist: `_to_domain()` (with variants loaded) and `_to_domain_without_skus()` (empty variants list). The `get()` method returns a product with empty variants, which means calling domain methods like `transition_status()` on a product loaded via `get()` will fail (no active SKUs). Callers must know which method was used.
- Safe modification: Use `get_with_variants()` or `get_for_update_with_variants()` for any operation that inspects child entities. Never call domain methods on entities loaded via `get()`.
- Test coverage: Integration tests cover the correct loading patterns; no test verifies that `get()` + `transition_status()` raises correctly.

**`__setattr__` Guard Pattern (DDD-01):**
- Files: `backend/src/modules/catalog/domain/entities/product.py` (lines 136-143)
- Why fragile: The guard uses a `_Product__initialized` flag set in `__attrs_post_init__`. If attrs changes its initialization order or a subclass overrides `__attrs_post_init__`, the guard may fire prematurely or not at all. The pattern relies on `object.__setattr__` to bypass the guard in `transition_status()`.
- Safe modification: Do not subclass `Product`. If modifying the guard, ensure unit tests in `backend/tests/unit/modules/catalog/domain/test_product.py` pass. The guard is well-tested.
- Test coverage: Good -- unit tests verify both blocked and allowed mutations.

## Scaling Limits

**Outbox Table Growth:**
- Current capacity: Pruning runs daily at 03:00 UTC, deleting processed records older than 7 days.
- Limit: With high write throughput, the `outbox_messages` table can accumulate millions of rows between prune cycles. The relay polls every minute with a batch size of 100, meaning at most ~144,000 events/day can be processed.
- Scaling path: Increase relay frequency or batch size. Add a partial index on `(processed_at IS NULL)` to speed up the relay query. For extreme throughput, switch from polling to WAL-based change data capture (Debezium).

**Single-Database Architecture:**
- Current capacity: All modules share a single PostgreSQL instance.
- Limit: The EAV pattern with JSONB columns and GIN indexes is I/O-intensive. As product count grows beyond ~100K with full attribute data, GIN index maintenance and JSONB filtering will become bottlenecks.
- Scaling path: Read replicas for query handlers (CQRS read side). Materialized views for storefront queries. Eventually, a dedicated search engine (Elasticsearch/Meilisearch) for catalog browsing.

## Dependencies at Risk

**Python 3.14 (Pre-Release):**
- Risk: The project targets Python 3.14, which as of the analysis date is very new. Third-party libraries (especially C extensions) may have compatibility issues. The `pyproject.toml` pins `python = ">=3.14"`.
- Impact: Deployment issues if any dependency drops Python 3.14 support or has undiscovered bugs on this version.
- Migration plan: Keep a fallback plan for Python 3.13. Monitor CI for library compatibility regressions.

**SQLAlchemy 2.1 Beta:**
- Risk: The project uses `sqlalchemy>=2.1.0b1` -- a beta version. Beta APIs may change before the stable release.
- Impact: Breaking changes on upgrade to stable 2.1.0 or later. Bugs in beta ORM features (e.g., `selectinload` with `.and_()` filter) may cause incorrect data loading.
- Migration plan: Pin to a specific beta version in the lockfile (`backend/uv.lock`). Test thoroughly when upgrading to stable release.

## Missing Critical Features

**No Full-Text Search:**
- Problem: Product search is limited to exact slug matching and JSONB GIN indexes on `title_i18n`. No full-text search capability exists.
- Blocks: Storefront search bar, admin product search.

**No Inventory/Stock Management:**
- Problem: SKUs have `is_active` flag but no stock quantity tracking. The EAV catalog must integrate with an inventory system before orders can be fulfilled.
- Blocks: Cart validation, order creation, stock alerts.

**No Cart or Order Module:**
- Problem: The catalog is designed as a foundation for e-commerce, but cart, checkout, and order modules do not exist yet.
- Blocks: End-to-end purchase flow.

## Test Coverage Gaps

**Zero Tests for Geo Module:**
- What's not tested: All query handlers, repositories, and domain logic for countries, currencies, languages, and subdivisions.
- Files: `backend/src/modules/geo/` (14 source files, 0 test files)
- Risk: Schema or query changes to geo data (used by currency FK references in SKUs and variants) could break silently.
- Priority: Low (read-only reference data, unlikely to change frequently)

**Zero Tests for Bot Module:**
- What's not tested: Telegram bot handlers, callbacks, keyboards, throttling middleware, and user identification middleware.
- Files: `backend/src/bot/` (11 source files, 0 test files)
- Risk: Bot behavior changes (FSM states, message formatting, throttle logic) are untested.
- Priority: Medium (user-facing interaction channel)

**No Catalog Query Handler Tests:**
- What's not tested: All CQRS read-side handlers: `list_products.py`, `get_product.py`, `get_product_completeness.py`, `storefront.py`, `resolve_template_attributes.py`, `list_brands.py`, `get_category_tree.py`, etc.
- Files: `backend/src/modules/catalog/application/queries/` (11 source files), `backend/tests/unit/modules/catalog/application/` (no query test files), `backend/tests/integration/modules/catalog/application/` (only `test_create_brand.py`)
- Risk: Query logic bugs (incorrect filters, wrong sorting, broken caching, missing eager loads) are not caught before deployment. Storefront queries serve end-user traffic and are performance-sensitive.
- Priority: High (directly affects storefront correctness and admin usability)

**No User Infrastructure/Repository Tests:**
- What's not tested: Customer and StaffMember repository implementations, username checker service.
- Files: `backend/src/modules/user/infrastructure/repositories/customer_repository.py`, `backend/src/modules/user/infrastructure/repositories/staff_member_repository.py`, `backend/src/modules/user/infrastructure/services/username_checker.py`
- Risk: User profile persistence bugs (duplicate usernames, broken anonymization) would go undetected.
- Priority: Medium (user profiles are a dependency for the upcoming order system)

**Architecture Tests Exclude Supplier and Geo Modules:**
- What's not tested: Boundary enforcement for `supplier` and `geo` modules is completely missing from the architecture fitness tests.
- Files: `backend/tests/architecture/test_boundaries.py` (line 12: `MODULES = ["catalog", "identity", "user"]`)
- Risk: Cross-module violations (like the catalog -> supplier coupling already present) are not caught.
- Priority: High (cheap to fix -- just add module names to the list)

**Zero Frontend Tests:**
- What's not tested: Both frontend applications (`frontend/admin/` and `frontend/main/`) have zero test files.
- Files: All of `frontend/admin/src/` and `frontend/main/`
- Risk: UI regressions, broken API integrations, and routing issues are only caught by manual testing.
- Priority: Medium (frontends are changing actively with many TODO items for API integration)

---

*Concerns audit: 2026-03-29*
