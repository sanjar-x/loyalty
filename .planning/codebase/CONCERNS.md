# Codebase Concerns

**Analysis Date:** 2026-03-28

## Tech Debt

**Domain layer depends on application layer (DDD layer violation):**
- Issue: `backend/src/modules/catalog/domain/value_objects.py` imports from `backend/src/modules/catalog/application/constants.py` (line 14: `from src.modules.catalog.application.constants import DEFAULT_CURRENCY, DEFAULT_SEARCH_WEIGHT, REQUIRED_LOCALES`). The domain layer's own docstring declares "zero infrastructure imports" but violates the analogous rule for application imports. The domain layer must not depend on any outer layer.
- Files: `backend/src/modules/catalog/domain/value_objects.py:14-18`, `backend/src/modules/catalog/application/constants.py`
- Impact: Creates a circular dependency risk. Domain entities cannot be used or tested without pulling in the application layer. Breaks hexagonal architecture's dependency inversion principle.
- Fix approach: Move `DEFAULT_CURRENCY`, `DEFAULT_SEARCH_WEIGHT`, and `REQUIRED_LOCALES` into `backend/src/modules/catalog/domain/constants.py` (which already exists but may not contain these values). Update imports throughout. Keep cache-key builders in `application/constants.py` since those are application-level concerns.

**Catalog domain entities: God-class file (2220 lines):**
- Issue: `backend/src/modules/catalog/domain/entities.py` is 2220 lines containing 9+ entity/aggregate classes (Brand, Category, AttributeTemplate, TemplateAttributeBinding, AttributeGroup, Attribute, AttributeValue, ProductVariant, SKU, Product, ProductAttributeValue, MediaAsset). The Product aggregate alone spans ~500 lines with variant and SKU management.
- Files: `backend/src/modules/catalog/domain/entities.py`
- Impact: Difficult to navigate, test in isolation, and reason about. Merge conflicts likely when multiple developers touch catalog features. All entities share private helper functions at module level, making extraction non-trivial.
- Fix approach: Split into separate files per entity/aggregate: `brand.py`, `category.py`, `attribute.py`, `product.py`, etc. Move shared validators (`_validate_slug`, `_generate_id`, `_validate_sort_order`, `_validate_i18n_values`, `_validate_filter_settings`) into a `validators.py` helper module. Re-export from `entities/__init__.py` or a barrel file to preserve existing import paths.

**Pervasive broad `except Exception` in command handlers:**
- Issue: 21 out of 46 catalog command handlers catch bare `except Exception` to wrap errors. Examples include `create_category.py:161`, `update_category.py:197,211`, `delete_attribute.py:110`, `update_attribute.py:151`, `add_attribute_value.py:165`, `bind_attribute_to_template.py:172`. These catches swallow cache invalidation failures post-commit, but the pattern is used inconsistently -- some commands use targeted `except RedisError` while others catch everything.
- Files: All files listed in `backend/src/modules/catalog/application/commands/` (see the grep output above for the full list of 21 handlers)
- Impact: Genuine errors during cache invalidation (e.g., serialization bugs, connection pool exhaustion) are silently swallowed. Only a warning log is emitted. Different handlers handle the same failure pattern differently, making behavior unpredictable.
- Fix approach: Standardize on catching `RedisError` or `Exception` with a shared helper function that logs and continues. Extract a `_safe_invalidate_cache(cache, keys, logger)` utility to eliminate the duplicated try/except blocks across all 21 handlers.

**Commands import from queries (CQRS boundary bleed):**
- Issue: 12 command handlers import from `backend/src/modules/catalog/application/queries/resolve_template_attributes.py` to use `resolve_effective_attribute_ids()` and `collect_attribute_cache_keys()`. While these are utility functions, placing them in a query module couples the write side to the read side.
- Files: `backend/src/modules/catalog/application/commands/assign_product_attribute.py`, `bulk_assign_product_attributes.py`, `generate_sku_matrix.py`, `delete_attribute.py`, `update_attribute.py`, `update_attribute_value.py`, `delete_attribute_value.py`, `bind_attribute_to_template.py`, `unbind_attribute_from_template.py`, `reorder_template_bindings.py`, `update_template_attribute_binding.py`, `bulk_add_attribute_values.py` (2 use deferred imports inside the handler method)
- Impact: The query module `resolve_template_attributes.py` (301 lines) mixes read-side query handler logic with shared utility functions. This makes the CQRS boundary unclear and creates a hidden coupling.
- Fix approach: Extract `resolve_effective_attribute_ids()` and `collect_attribute_cache_keys()` into a dedicated service module (e.g., `backend/src/modules/catalog/application/services/template_resolution.py`) that both commands and queries can depend on.

**ImageBackendClient is APP-scoped singleton without lifecycle management:**
- Issue: `ImageBackendClient` is registered with `Scope.APP` in `backend/src/modules/catalog/presentation/dependencies.py:493-498`, creating a singleton `httpx.AsyncClient` for the entire app lifetime. However, the Dishka container does not call `aclose()` on teardown, meaning the HTTP client's connection pool is never explicitly closed.
- Files: `backend/src/modules/catalog/infrastructure/image_backend_client.py:20-24`, `backend/src/modules/catalog/presentation/dependencies.py:493-498`
- Impact: On graceful shutdown, the httpx connection pool may leak file descriptors or TCP connections. Under high load, connection pool exhaustion is possible if the underlying client is not properly managed.
- Fix approach: Register a Dishka `teardown` callback or use `provide(..., teardown=lambda c: c.aclose())` to ensure the client is closed on app shutdown. Alternatively, provide a factory that uses httpx connection pooling at the app level.

**`noqa: C901` complexity suppression on bulk handlers:**
- Issue: Two command handlers suppress McCabe complexity warnings: `BulkAssignProductAttributesHandler.handle()` in `backend/src/modules/catalog/application/commands/bulk_assign_product_attributes.py:74` and `BulkCreateAttributesHandler.handle()` in `backend/src/modules/catalog/application/commands/bulk_create_attributes.py:99`. Both have deeply nested validation loops with multiple early-exit raises.
- Files: `backend/src/modules/catalog/application/commands/bulk_assign_product_attributes.py:74`, `backend/src/modules/catalog/application/commands/bulk_create_attributes.py:99`
- Impact: High cyclomatic complexity makes the handlers hard to test exhaustively and reason about.
- Fix approach: Extract the validation loop body into a private `_validate_item()` method. Each iteration's validation (template check, attribute exists, value exists, duplicate check) can be a separate method call.

**Defensive `getattr` in product response mapping hides missing data:**
- Issue: `_to_product_response()` in `backend/src/modules/catalog/presentation/router_products.py:319-320` uses `getattr(a, "attribute_value_code", "")` and `getattr(a, "attribute_value_name_i18n", {})` with fallback defaults. This silently returns empty strings/dicts when the read model lacks these fields instead of failing fast.
- Files: `backend/src/modules/catalog/presentation/router_products.py:319-320`
- Impact: If the read model changes or the query fails to join attribute values, the API silently returns incomplete data rather than erroring. Clients may receive products with blank attribute codes.
- Fix approach: Add the `attribute_value_code` and `attribute_value_name_i18n` fields to the read model explicitly. Remove the defensive `getattr` and let missing fields surface as errors.

**Pervasive `# type: ignore[assignment]` for Dishka DI injection:**
- Issue: 15+ endpoint signatures use `handler: FromDishka[HandlerType] = ...  # type: ignore[assignment]` because the Ellipsis default does not match the handler type annotation. This suppresses real type errors alongside the Dishka-specific ones.
- Files: `backend/src/api/dependencies/auth.py:29`, `backend/src/modules/identity/presentation/dependencies.py:34-35,131`, `backend/src/modules/identity/presentation/router_account.py:44,74,108`, `backend/src/modules/identity/presentation/router_auth.py:184,206`, `backend/src/modules/user/presentation/router.py:41,63`, and others
- Impact: Mypy cannot detect genuine type mismatches in these function signatures. The suppression is inherited from the Dishka integration pattern but should be limited to Dishka-specific parameters.
- Fix approach: Create a typed helper (e.g., `INJECTED: Any = ...`) or use a Dishka-provided sentinel that satisfies mypy. Alternatively, confine `# type: ignore` to a single type alias definition.

**Admin Frontend: Entirely JavaScript (no TypeScript):**
- Issue: The entire admin panel (`frontend/admin/src/`) is written in JavaScript (145+ `.js`/`.jsx` files, zero `.ts`/`.tsx`). No type checking, no interfaces, no compile-time safety.
- Files: All files under `frontend/admin/src/`
- Impact: Bugs from type mismatches surface only at runtime. Refactoring is risky without types. API contract changes silently break the admin UI.
- Fix approach: Incrementally migrate to TypeScript starting with service layer files (`frontend/admin/src/services/*.js`, `frontend/admin/src/hooks/*.js`), then components. Add a `tsconfig.json` and rename files one at a time.

**Admin Frontend: Hardcoded seed/mock data throughout services:**
- Issue: Most admin services return static seed data instead of calling the backend API. Orders, users, reviews, staff, referrals, and promocodes all read from `frontend/admin/src/data/*.js` mock files.
- Files: `frontend/admin/src/services/products.js`, `frontend/admin/src/services/users.js`, `frontend/admin/src/services/orders.js`, `frontend/admin/src/services/reviews.js`, `frontend/admin/src/services/staff.js`, `frontend/admin/src/services/referrals.js`, `frontend/admin/src/services/promocodes.js`
- Impact: The admin panel displays fake data. Admin features relying on these services are non-functional in production.
- Fix approach: Replace seed-based service functions with fetch calls to backend BFF routes (the pattern already exists in `frontend/admin/src/services/categories.js`).

**Main Frontend: Stub hooks with no implementation:**
- Issue: Core e-commerce hooks are empty stubs: `useCart` returns static empty data; `useItemFavorites` is not connected to API.
- Files: `frontend/main/components/blocks/cart/useCart.ts`, `frontend/main/lib/hooks/useItemFavorites.ts`
- Impact: Cart and favorites are completely non-functional. The checkout page renders a full UI but cannot process orders.
- Fix approach: Implement with RTK Query endpoints backed by cart/favorites backend APIs. RTK Query infrastructure exists in `frontend/main/lib/store/api.ts`.

## Known Bugs

**No confirmed bugs identified.** The codebase is in an early development state with many features unimplemented rather than broken.

## Security Considerations

**No API-level rate limiting on backend:**
- Risk: Authentication endpoints (`/api/v1/auth/login`, `/api/v1/auth/register`) lack rate limiting, enabling brute-force attacks. Only the Telegram bot has throttling (`backend/src/bot/middlewares/throttling.py`).
- Files: `backend/src/bootstrap/web.py`, `backend/src/api/middlewares/`
- Current mitigation: None for HTTP API.
- Recommendations: Add a rate-limiting middleware (e.g., `slowapi` or custom Redis-based limiter) to auth endpoints at minimum. Consider per-IP and per-identity limits.

**No input sanitization for i18n string fields:**
- Risk: Multilingual `i18n` fields (title_i18n, description_i18n, name_i18n) accept arbitrary strings. While Pydantic validates the dict structure, there is no HTML/XSS sanitization on the values. If these values are rendered without escaping in the frontend (e.g., via `dangerouslySetInnerHTML`), stored XSS is possible.
- Files: `backend/src/modules/catalog/domain/entities.py` (all `create()` and `update()` methods accepting i18n dicts), `backend/src/modules/catalog/presentation/schemas.py` (all `I18nDict` fields)
- Current mitigation: React auto-escapes by default. SQL queries use parameterized statements. The `_validate_i18n_values()` at `entities.py:96-99` checks for non-blank values but does not sanitize.
- Recommendations: Add a domain-level sanitizer that strips HTML tags from i18n values. Or add a Pydantic validator on `I18nDict` that rejects strings containing `<script>`, `<iframe>`, etc.

**Health endpoint exposes environment name without authentication:**
- Risk: The `/health` endpoint at `backend/src/bootstrap/web.py:99-102` returns `{"status": "ok", "environment": "prod"}` without requiring authentication. This leaks deployment environment information.
- Files: `backend/src/bootstrap/web.py:99-102`
- Current mitigation: None.
- Recommendations: Remove the `environment` field from the health response, or restrict it to authenticated admin requests.

**CSP allows `unsafe-inline` and `unsafe-eval` in admin:**
- Risk: Admin frontend sets `script-src 'self' 'unsafe-inline' 'unsafe-eval'` which negates XSS protection from CSP.
- Files: `frontend/admin/next.config.js:16`
- Current mitigation: HttpOnly cookies prevent token theft via XSS.
- Recommendations: Tighten CSP to use nonces. Remove `unsafe-eval` if not required by dependencies.

**Main frontend has no CSP header:**
- Risk: The main customer-facing app does not set a Content-Security-Policy header at all.
- Files: `frontend/main/next.config.ts`, `frontend/main/middleware.ts`
- Current mitigation: None.
- Recommendations: Add CSP header via `next.config.ts` headers.

**`source_url` validation allows HTTP URLs in product creation:**
- Risk: `ProductCreateRequest.source_url` validates with `pattern=r"^https?://"` (line 731 in schemas.py), allowing plain HTTP URLs. Product `source_url` fields point to external supplier pages (Poizon, Taobao) and should enforce HTTPS.
- Files: `backend/src/modules/catalog/presentation/schemas.py:731`
- Current mitigation: The brand `logo_url` correctly requires `^https://` (line 249). The product `source_url` is less strict.
- Recommendations: Change the pattern to `^https://` to match the brand logo validation.

## Performance Bottlenecks

**Pagination uses COUNT(*) subquery on every list request:**
- Problem: The shared `paginate()` helper at `backend/src/shared/pagination.py:34` wraps the entire base query in a subquery and runs `SELECT COUNT(*)` before the paginated query. This doubles the DB work on every list endpoint.
- Files: `backend/src/shared/pagination.py`, used by 15+ query handlers across catalog and identity modules
- Cause: Standard approach but wasteful when total count is not always needed.
- Improvement path: Consider cursor-based pagination for high-volume endpoints. Alternatively, cache the count or only compute when the client explicitly requests it.

**Storefront cache deserializes full Pydantic models from JSON on every cache hit:**
- Problem: All 4 storefront query handlers (`backend/src/modules/catalog/application/queries/storefront.py`) call `model_validate(json.loads(cached))` on Redis cache hits. This parses JSON and validates the entire Pydantic model tree on every cached request.
- Files: `backend/src/modules/catalog/application/queries/storefront.py:114,186,273,333`
- Cause: Cache stores serialized JSON strings; deserialization cost is O(n) in the number of attributes.
- Improvement path: Use `model_validate_json()` (Pydantic v2 optimized path) instead of `json.loads()` + `model_validate()`. Consider using msgpack or pickle for internal cache serialization. Or return raw JSON strings from the cache and skip Pydantic validation on cache hits.

**Product `find_sku()` and `find_variant()` use O(V*S) linear scan:**
- Problem: `Product.find_sku()` at `backend/src/modules/catalog/domain/entities.py:2157-2170` iterates all variants and all SKUs to find a single SKU by ID. `Product.remove_sku()` (lines 2172-2195) does the same. With many variants and SKUs per product, this is quadratic.
- Files: `backend/src/modules/catalog/domain/entities.py:2042-2054,2157-2195`
- Cause: Variants and SKUs are stored as flat lists without indexing.
- Improvement path: For the current catalog size this is acceptable. If products grow to have many variants (e.g., fashion with 50+ size/color combos), consider maintaining a `dict[UUID, SKU]` index. However, the DDD aggregate pattern intentionally keeps the aggregate small enough that this should not be a bottleneck in practice.

**Bulk operations iterate N+1-style within batch despite batch prefetch:**
- Problem: `BulkCreateAttributesHandler` at `backend/src/modules/catalog/application/commands/bulk_create_attributes.py:146-147` checks `check_code_exists()` and `check_slug_exists()` individually for each item in the batch, resulting in 2N queries per batch. The `BulkAssignProductAttributesHandler` correctly batch-prefetches (`get_many`, `check_assignments_exist_bulk`), but `BulkCreateAttributes` does not.
- Files: `backend/src/modules/catalog/application/commands/bulk_create_attributes.py:146-147`
- Cause: Incremental development -- newer bulk handlers use batch patterns while older ones were not retrofitted.
- Improvement path: Add `check_codes_exist_bulk()` and `check_slugs_exist_bulk()` methods to `IAttributeRepository` and use them in the handler.

## Fragile Areas

**Outbox relay: failed events silently remain unprocessed:**
- Files: `backend/src/infrastructure/outbox/relay.py:162-169`, `backend/src/infrastructure/outbox/tasks.py:137-138`
- Why fragile: When event processing fails, the exception is caught and logged, but the event remains in the outbox table without a retry counter or dead-letter mechanism. Events can sit indefinitely if the same error recurs.
- Safe modification: The relay runs every minute via TaskIQ scheduler. Test against failure scenarios before modifying relay logic.
- Test coverage: Unit tests exist in `backend/tests/unit/infrastructure/outbox/test_relay.py` and `backend/tests/unit/infrastructure/outbox/test_tasks.py`.

**Catalog Product aggregate: deep nesting with async ORM interaction:**
- Files: `backend/src/modules/catalog/domain/entities.py` (Product, lines 1700-2220), `backend/src/modules/catalog/infrastructure/repositories/product.py` (557 lines)
- Why fragile: The Product aggregate root contains variants which contain SKUs which contain attribute values. The repository must use precise `selectinload` chains (3 levels deep) to avoid `MissingGreenlet` errors in async context. The comment at `product.py:398` and `product.py:454` explicitly documents this: "Using _to_domain(orm) would trigger lazy-load of variant.skus in async context (MissingGreenlet)." A missed eager-load in any new query method silently crashes at runtime.
- Safe modification: Always copy the `selectinload` chain from `get_with_variants()` (line 540-548) when adding new product query methods. Never rely on ORM lazy loading.
- Test coverage: Product repository has integration tests only for brand/category repos. No integration tests for product repo methods `get_with_variants`, `get_for_update_with_variants`, `update`, or `add`.

**Category effective_template_id cascade propagation:**
- Files: `backend/src/modules/catalog/application/commands/update_category.py:177-185`, `backend/src/modules/catalog/domain/entities.py` (Category)
- Why fragile: When a category's `template_id` changes, the handler calls `propagate_effective_template_id()` to cascade the change to all inheriting descendants. This is a recursive operation that touches multiple rows in a single transaction. If the category tree is deep or wide, this could lock many rows and cause contention.
- Safe modification: Test with a multi-level category tree (3 levels, many siblings) before modifying propagation logic. The `update_descendants_full_slug()` method (line 188-191) has a similar cascade pattern.
- Test coverage: Integration tests exist for effective_template_id in `backend/tests/integration/modules/catalog/infrastructure/repositories/test_category_effective_family.py` (7 tests).

**Cache invalidation happens after commit, outside the UoW:**
- Files: All command handlers in `backend/src/modules/catalog/application/commands/` that invalidate cache
- Why fragile: Cache invalidation runs after `await self._uow.commit()` and outside the `async with self._uow:` block. If the process crashes between commit and cache invalidation, stale cache entries remain until TTL expiry (3600s for storefront caches). The TTL provides a safety net, but for 1 hour the storefront may serve stale attribute data.
- Safe modification: Do not move cache invalidation inside the UoW -- that would couple cache availability to transaction success. The current approach is correct but accept the window of staleness.
- Test coverage: No tests verify cache invalidation behavior in command handlers.

**`_provided_fields` pattern for partial updates:**
- Files: `backend/src/modules/catalog/application/commands/update_brand.py:41`, `backend/src/modules/catalog/application/commands/update_category.py:53`, `backend/src/modules/catalog/presentation/update_helpers.py`
- Why fragile: Update commands carry a `_provided_fields: frozenset[str]` field populated by `build_update_command()` at the presentation layer. If a new field is added to the command dataclass but the presentation layer does not populate `_provided_fields` correctly, the field will be silently ignored during update.
- Safe modification: When adding new updatable fields, ensure they appear in the Pydantic schema's `model_fields_set` tracking (which feeds `_provided_fields` via `build_update_command`).
- Test coverage: Only `test_brand_handlers.py` tests the update flow with `_provided_fields`.

## Scaling Limits

**Single outbox relay table with polling:**
- Current capacity: Relay polls every minute with configurable batch size. Throughput: ~100 events/minute.
- Limit: Under high write load, the outbox grows faster than the relay drains it.
- Scaling path: Increase batch size, decrease poll interval, or use PostgreSQL LISTEN/NOTIFY. RabbitMQ is already configured (`RABBITMQ_PRIVATE_URL`) but not used for outbox relay.

**Storefront cache per-category with TTL-only expiry:**
- Current capacity: Each category gets 4 cache keys (filters, card, comparison, form). With 100 categories, that's 400 cache entries.
- Limit: With 1000+ categories and frequent attribute template changes, cache invalidation generates large `DELETE_MANY` calls to Redis. The `update_category` handler can invalidate all 4 keys for every descendant category in a single call (line 204-210).
- Scaling path: Use cache tags or a generation counter instead of per-key deletion.

## Dependencies at Risk

**Python 3.14 (pre-release):**
- Risk: The backend uses Python 3.14 (`.python-version` pinned to 3.14). Python 3.14 is in development/beta as of this analysis date.
- Impact: Library incompatibilities, undiscovered runtime bugs, lack of production-hardened releases.
- Migration plan: Pin to Python 3.12 or 3.13 (latest stable) for production.

**SQLAlchemy 2.1 (beta):**
- Risk: `pyproject.toml` requires `sqlalchemy>=2.1.0b1`. SQLAlchemy 2.1 is a beta release.
- Impact: API changes between beta and stable could break ORM code. The async session and relationship loading behavior may change.
- Migration plan: Track SQLAlchemy 2.1 release notes. Pin to a specific beta version until stable is released.

## Missing Critical Features

**No order/checkout backend:**
- Problem: The frontend has a complete checkout UI (`frontend/main/app/checkout/page.tsx`) but there is no order module in `backend/src/modules/`.
- Blocks: End-to-end purchasing, payment processing, order tracking.

**No cart backend:**
- Problem: Cart hook (`frontend/main/components/blocks/cart/useCart.ts`) is a stub. No cart module exists in the backend.
- Blocks: Users cannot add items to cart or proceed through checkout.

**No payment integration:**
- Problem: Checkout page displays payment options but no payment provider is integrated.
- Blocks: Revenue generation and transaction processing.

## Test Coverage Gaps

**Catalog command handlers: 44 of 46 untested:**
- What's not tested: Of the 46 command handlers in `backend/src/modules/catalog/application/commands/`, only `create_brand` and `sync_product_media` have unit or integration tests. Critical handlers like `create_product.py`, `add_variant.py`, `add_sku.py`, `change_product_status.py`, `generate_sku_matrix.py`, `update_product.py`, `delete_product.py`, `assign_product_attribute.py`, `bulk_assign_product_attributes.py`, and all attribute/category/template commands are untested.
- Files: `backend/src/modules/catalog/application/commands/` (44 files without corresponding test files)
- Risk: Product creation, variant management, SKU generation, status transitions, attribute assignment, and category operations are all core business flows without test coverage.
- Priority: High -- this is the primary focus of the EAV Catalog Hardening milestone.

**Catalog query handlers: 0 of 21 tested:**
- What's not tested: None of the 21 query handlers in `backend/src/modules/catalog/application/queries/` have tests. This includes critical storefront queries (`storefront.py` with 4 handlers), `list_products.py`, `get_product.py`, `get_product_completeness.py`, `resolve_template_attributes.py`, and all list/get handlers.
- Files: `backend/src/modules/catalog/application/queries/` (21 files)
- Risk: Storefront data delivery, product listing, and template resolution could return incorrect data without detection.
- Priority: High

**Catalog repositories: only brand and category have integration tests:**
- What's not tested: Product repository (557 lines with complex variant/SKU sync), attribute repository, attribute_value repository, attribute_template repository, template_attribute_binding repository, media_asset repository, and product_attribute_value repository all lack integration tests.
- Files: `backend/src/modules/catalog/infrastructure/repositories/product.py`, `attribute.py`, `attribute_value.py`, `attribute_template.py`, `template_attribute_binding.py`, `media_asset.py`, `product_attribute_value.py`
- Risk: ORM-to-domain mapping, eager loading chains, and constraint handling in the product repository are critical paths that could silently produce wrong domain objects or fail with `MissingGreenlet` errors.
- Priority: High

**E2E API tests: minimal coverage:**
- What's not tested: Only 5 e2e test files exist (auth, auth_telegram, brands, categories, users) with a total of 382 lines. The brands e2e has 1 test (22 lines). The categories e2e has 1 test (33 lines). No e2e tests exist for products, attributes, attribute values, templates, SKUs, variants, media, or storefront endpoints.
- Files: `backend/tests/e2e/api/v1/` (5 files, 382 total lines)
- Risk: API contract compliance, HTTP status codes, request/response schema validation, and authorization enforcement are not verified end-to-end.
- Priority: High

**Frontend: Zero tests across both apps:**
- What's not tested: All TypeScript files in `frontend/main/` and all JavaScript files in `frontend/admin/src/` have no tests.
- Files: Entire `frontend/` directory
- Risk: Any refactoring or API contract change could break the UI silently.
- Priority: Medium (not in scope for current catalog hardening milestone)

**Geo module: Zero tests:**
- What's not tested: The entire geo module (15 source files) has no tests.
- Files: `backend/src/modules/geo/`
- Risk: Geographic data queries could return incorrect results.
- Priority: Low

---

*Concerns audit: 2026-03-28*
