# Pitfalls Research

**Domain:** EAV Catalog Hardening -- Testing & Refactoring a DDD/CQRS E-Commerce Catalog Module
**Researched:** 2026-03-28
**Confidence:** HIGH (based on codebase analysis + domain research + established patterns)

## Critical Pitfalls

### Pitfall 1: Testing Mocks That Lie -- Unit Tests Pass But Integration Breaks

**What goes wrong:**
Unit tests for the 44 untested command handlers are written with mock repositories that return perfectly shaped data, but the actual SQLAlchemy repository mapping (domain-to-ORM and back) silently corrupts data. The `ProductRepository._sku_to_orm()` method has a 30-line diff-based sync for `SKUAttributeValueLink` rows. The `_sync_variants()` method reconciles nested collections across three levels (Product -> Variant -> SKU -> AttributeValueLinks). Mocking these away means unit tests verify handler orchestration logic, but never catch mapping bugs -- which is where real EAV catalog bugs live.

**Why it happens:**
CQRS handler unit tests naturally mock the repository interface (`IProductRepository`). The handler code itself is often simple orchestration -- fetch, validate FKs, call domain method, persist. The complex logic lives in (a) domain entity methods and (b) repository mapping. Mocking the repository removes (b) from the test entirely. Teams feel productive because 44 handlers get "tested" quickly, but the actual failure surface (Data Mapper layer, ORM relationship sync, Money VO decomposition) is untouched.

**How to avoid:**
1. Write domain entity unit tests FIRST -- these test `Product.add_sku()`, `Product.transition_status()`, `Product.add_variant()` etc. with no mocks at all. Pure Python, fast, and they cover the real business rules.
2. Write integration tests for the Product repository specifically -- roundtrip tests that create a Product with variants/SKUs, persist, reload, and verify every field survived. Cover the `_sync_variants` and `_sync_skus_for_variant` reconciliation paths.
3. Only then write handler-level tests: unit tests with mocked repos for handler orchestration (FK validation, error paths), plus a small set of integration tests for the most complex handlers (`create_product`, `generate_sku_matrix`, `add_sku`, `change_product_status`).

**Warning signs:**
- All 44 handler tests written in under 2 days -- if it was that fast, mapping logic was not tested.
- Zero `db_session` fixture usage in unit tests -- means no real DB roundtrip.
- Mock return values are hand-crafted dicts instead of domain entities built through factory methods.
- `ProductRepository.update()` never called in any test (the most complex method with 3-level sync).

**Phase to address:**
Phase 1 (Domain model analysis + entity tests) and Phase 2 (Repository integration tests) -- before handler tests.

---

### Pitfall 2: God-Class Split Breaks Import Compatibility Silently

**What goes wrong:**
Splitting `entities.py` (2,220 lines, 9+ classes) into separate files (`brand.py`, `category.py`, `product.py`, etc.) breaks every module that imports from the old path. The codebase has cross-references everywhere: `from src.modules.catalog.domain.entities import Product, Brand, Category, SKU`. One missed re-export in `entities/__init__.py` and a handler fails at import time -- but only if that specific handler is actually invoked. Python does not eagerly validate all imports.

More dangerously, the entities share private module-level helpers (`_validate_slug`, `_validate_i18n_values`, `_generate_id`, `_validate_sort_order`, and the `_*_GUARDED_FIELDS` frozensets). Moving classes to separate files requires either duplicating these helpers or creating a shared `_helpers.py` module. Getting this wrong causes subtle `NameError` or `ImportError` at runtime, not at import time.

**Why it happens:**
The refactoring seems straightforward -- "just move each class to its own file." But Python module initialization order matters. Circular imports between entity files (e.g., `Product` references `ProductVariant` which references `SKU`) require careful ordering or deferred imports. The `__setattr__` guard pattern used across 6 entities references module-level frozensets that must be importable in the new file location.

**How to avoid:**
1. Create `entities/` package directory with `__init__.py` that re-exports every public name from the old `entities.py` -- maintaining backward compatibility.
2. Extract shared helpers into `entities/_helpers.py` first. Verify all tests pass.
3. Move one entity at a time, starting with the simplest (Brand, AttributeGroup) that have no intra-entity dependencies.
4. Move Product last because it depends on ProductVariant and SKU.
5. After each file move, run the full test suite AND run `python -c "from src.modules.catalog.domain.entities import Product, Brand, Category, SKU, ..."` to verify import compatibility.
6. Keep the re-export `__init__.py` permanently -- never force downstream code to change import paths.

**Warning signs:**
- `ImportError` or `AttributeError` in tests that were passing before the split.
- Circular import errors (`ImportError: cannot import name 'X' from partially initialized module`).
- `NameError: name '_validate_slug' is not defined` at runtime in a handler path.

**Phase to address:**
Phase 3 or later -- do this AFTER test coverage is in place, so the split can be verified against existing tests. Never refactor structure before having tests.

---

### Pitfall 3: Optimistic Locking Not Tested -- Concurrency Bugs Ship to Production

**What goes wrong:**
The Product aggregate has a `version` field for optimistic locking, and the repository catches `StaleDataError`. But the version field is never actually incremented in the domain entity -- it relies on the ORM's `version_id_col` on the database side. The repository's `_to_orm()` method explicitly says "Only set version and timestamps on create; let DB handle them on update." This means the domain entity's `version` is always stale after an update. If two concurrent requests both load version=1, both modify the product, and both try to persist -- the optimistic lock SHOULD reject one. But if the version field in the ORM model is not properly configured with `version_id_col`, both writes succeed silently, and the last one wins.

Additionally, the `_sync_variants()` / `_sync_skus_for_variant()` methods modify child collections but do NOT bump the parent Product's version. Per the research, "the version number managed by SQLAlchemy is only bumped on the table where the INSERT/UPDATE/DELETE is happening." So adding a SKU to a variant may not trigger a version conflict at the Product level, even though it should.

**Why it happens:**
Optimistic locking is easy to implement on paper but hard to verify. Teams add the `version` field and assume it works. Testing requires actually simulating concurrent transactions, which is awkward in a test environment where everything runs sequentially by default.

**How to avoid:**
1. Write a specific integration test that: (a) loads a Product in two separate sessions, (b) modifies it in both, (c) commits the first, (d) verifies the second raises `ConcurrencyError`.
2. Verify the ORM model (`infrastructure/models.py`) has `version_id_col` properly configured on the Product table.
3. Add an `updated_at` touch in every domain mutation method (already present in most methods via `self.updated_at = datetime.now(UTC)`) and ensure the ORM model's `onupdate` triggers a version bump.
4. Test the child-entity-only update path: load product, add SKU only (no product-level field changes), verify version is bumped.

**Warning signs:**
- No test file with "concurrency" or "version" or "optimistic" in the name.
- The `version` field is always 1 in test assertions (never tested that it increments).
- Two browser tabs editing the same product simultaneously silently overwrite each other.

**Phase to address:**
Phase 2 (Repository integration tests) -- include a dedicated concurrency test section.

---

### Pitfall 4: EAV Attribute Integrity -- Orphan Values and Type Mismatches

**What goes wrong:**
The EAV system has a layered attribute governance chain: `Category -> (effective) AttributeTemplate -> TemplateAttributeBinding -> Attribute -> AttributeValue`. A product's valid attributes are determined by its category's effective template. But the system currently has no mechanism to detect or clean up:

1. **Orphan attribute values**: If an attribute is unbound from a template, existing products' attribute values for that attribute become "orphans" -- the data remains but is no longer governed.
2. **Template drift**: A category's `effective_template_id` is computed at creation time (`template_id or parent.effective_template_id`). If a parent category's template changes later, child categories' effective templates are NOT automatically recomputed.
3. **Level mismatch data**: The `generate_sku_matrix` handler validates `AttributeLevel.VARIANT`, but `assign_product_attribute` may not enforce `AttributeLevel.PRODUCT`. Tests that do not verify both paths end up with variant-level attributes assigned at product level or vice versa.

**Why it happens:**
EAV systems push schema enforcement out of the database and into application code. There are no foreign key constraints that prevent assigning an attribute value for attribute A to a product that should only have attributes B and C. The "template bindings" concept is essentially a soft-schema that must be enforced by every command handler independently.

**How to avoid:**
1. Write integration tests that verify the full governance chain: create category with template, bind attributes, create product, assign attribute values -- then verify only valid attributes are accepted.
2. Write negative tests: try assigning an attribute not in the template, verify rejection.
3. Write a test for template drift: change parent category's template, verify child's effective_template_id behavior.
4. Consider adding a database-level check constraint or trigger for attribute level validation on `product_attribute_values` and `sku_attribute_value_links`.

**Warning signs:**
- Product detail pages showing attributes that do not belong to the product's category.
- `AttributeNotInTemplateError` never raised in any test.
- Attribute values in the database referencing deleted or unbound attributes.

**Phase to address:**
Phase 1 (Domain model analysis) to catalog the governance rules, Phase 2 (Integration tests) to verify them.

---

### Pitfall 5: Async SQLAlchemy Lazy-Load Landmines in Tests

**What goes wrong:**
The codebase explicitly warns about this in comments: "Using `_to_domain(orm)` would trigger lazy-load of variant.skus in async context (MissingGreenlet)." The async SQLAlchemy session cannot lazily load relationships. The existing code carefully uses `selectinload` chains and `_to_domain_without_skus()` to avoid this. But test code often builds queries or accesses ORM objects differently than production code. A test that passes in isolation but triggers a `MissingGreenlet` error under slightly different session lifecycle is a common failure mode.

Specifically, the `db_session` fixture uses nested transactions with `join_transaction_mode="create_savepoint"`. The UoW `commit()` in production commits the outer transaction, but in tests, the commit hits a savepoint. If the UoW implementation's `commit()` expires the session (SQLAlchemy default behavior), subsequent access to ORM attributes in the test's assertion phase triggers `MissingGreenlet` because the session's savepoint context has changed.

**Why it happens:**
Async SQLAlchemy's session lifecycle is fundamentally different from sync SQLAlchemy. The `expire_on_commit=False` setting (already present in the test conftest) mitigates this, but developers writing new tests may not understand why it exists. They may also access ORM objects outside the session scope, or use `session.refresh()` without awaiting it properly.

**How to avoid:**
1. Always use `expire_on_commit=False` in test sessions (already configured -- do not change this).
2. In test assertions, query the database with a fresh `session.get()` call rather than accessing attributes on the ORM object returned by the handler. The existing `test_create_brand.py` demonstrates this pattern correctly: it re-fetches `orm_brand = await db_session.get(OrmBrand, result.brand_id)`.
3. Never access relationship attributes on ORM objects outside an eager-load context in tests. Always use `selectinload` or re-query.
4. Document the "assertion pattern" in a test helper or convention guide.

**Warning signs:**
- `sqlalchemy.exc.MissingGreenlet` errors in tests.
- Tests that pass individually but fail when run in a batch.
- Tests that access `product.variants[0].skus[0].price` on an ORM object without explicit eager loading.

**Phase to address:**
Phase 2 (Repository integration tests) -- establish the assertion pattern early, before writing 40+ handler tests.

---

### Pitfall 6: Soft-Delete Leaking Into Queries -- Invisible Zombie Records

**What goes wrong:**
The Product, ProductVariant, and SKU entities all support soft-delete via `deleted_at` timestamp. Every query, every repository method, every listing endpoint must filter `WHERE deleted_at IS NULL`. A single missed filter returns "deleted" products to the storefront, to the admin panel, or to count aggregations. The domain entity methods (`find_variant`, `find_sku`) correctly filter `deleted_at is None`, but the repository's listing/query methods and the CQRS read-side queries (which bypass the domain layer entirely) must independently implement this filter.

**Why it happens:**
Soft-delete is a cross-cutting concern that cannot be centralized in a single place. The domain layer checks it, the repository layer checks it, and the query layer checks it -- each independently. Adding a new query or endpoint without the soft-delete filter is an easy oversight, especially for CQRS read-side queries that use raw SQL or direct ORM queries.

**How to avoid:**
1. Write a systematic test for every list/get endpoint that creates a soft-deleted entity alongside an active one and verifies the deleted one is NOT returned.
2. For the CQRS read-side queries, add soft-delete filter tests to every query handler.
3. Consider adding a SQLAlchemy ORM-level `where_criteria` on the Product/Variant/SKU models that automatically applies `deleted_at IS NULL` to relationship loads (using `relationship(... , primaryjoin=...)` with the filter).
4. Write an architectural test that scans all query files for `SELECT` statements and flags any that reference `products`, `product_variants`, or `skus` tables without a `deleted_at` filter.

**Warning signs:**
- Storefront showing products the admin "deleted" days ago.
- Count mismatches between admin list (filtered) and dashboard aggregates (unfiltered).
- `list_products` returns different counts than expected after a delete operation in tests.

**Phase to address:**
Phase 2 (Integration tests) -- include soft-delete assertions in every repository and query test.

---

### Pitfall 7: Domain Event Accumulation Without Clearing

**What goes wrong:**
The `AggregateRoot.add_domain_event()` appends events to an in-memory list. The `UnitOfWork.commit()` is supposed to extract and persist these events to the Outbox table. But if a handler performs multiple operations on the same aggregate (e.g., `add_variant` then `add_sku` then `transition_status`), the aggregate accumulates 3+ domain events. If `commit()` is called multiple times (which the UoW pattern should prevent but the async context manager might not guarantee), events could be duplicated. Conversely, if `clear_domain_events()` is called prematurely (e.g., in a retry path), events are lost.

In the existing codebase, `Product.create()` emits `ProductCreatedEvent`, `Product.add_variant()` emits `VariantAddedEvent`, `Product.add_sku()` emits `SKUAddedEvent`, and `Product.transition_status()` emits `ProductStatusChangedEvent`. A product creation flow that auto-creates a default variant emits BOTH `ProductCreatedEvent` and the implicit variant event. Tests that verify event emission must account for this multiplicity.

**Why it happens:**
Domain events are an implementation detail that test writers often ignore ("I am testing the command, not the events"). But the Outbox relay processes these events to trigger downstream side effects. If event assertions are skipped, a handler refactoring might accidentally suppress or duplicate events, breaking downstream consumers (e.g., cache invalidation, search index updates) without any test catching it.

**How to avoid:**
1. In every command handler unit test, assert the count AND types of domain events emitted.
2. For `Product.create()`, explicitly verify that both `ProductCreatedEvent` and `VariantAddedEvent` are NOT both emitted (the current code only emits `ProductCreatedEvent` from `create()` -- the default variant is created without a separate event, which is intentional but must be verified).
3. Write an integration test that verifies events actually appear in the Outbox table after a handler execution.

**Warning signs:**
- No test ever accesses `product.domain_events` or `aggregate.domain_events`.
- Outbox relay processing duplicate events in staging/production.
- Downstream consumers receiving unexpected event sequences.

**Phase to address:**
Phase 1 (Domain entity tests) for event emission verification, Phase 3 (Handler tests) for end-to-end event flow.

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Mocking all repos in handler tests | Fast to write, 44 handlers "covered" in days | Zero confidence in mapping layer; bugs discovered in production | Only after repo integration tests exist AND domain entity tests cover business rules |
| Skipping negative test cases | Faster to get to "green" | Invalid inputs accepted silently; data corruption in EAV values | Never -- EAV systems require more negative tests than positive ones because the schema is soft |
| Testing only the happy path for status FSM | One test per transition is quick | Invalid transitions allowed; products published without SKUs | Never -- the FSM has 5 states x multiple transitions, each with preconditions |
| Using `pytest.mark.skip` for flaky async tests | Unblocks CI | Accumulates silently; real bugs hidden behind "known flaky" label | Only with a linked ticket and max 1-week expiry |
| Copy-pasting test fixtures between handler tests | Quick setup | Fixture changes require updating 44 test files | Never -- use shared conftest fixtures and factory functions |

## Integration Gotchas

Common mistakes when connecting components within this system.

| Integration | Common Mistake | Correct Approach |
|-------------|---------------|------------------|
| UoW + Savepoint Tests | Calling `uow.commit()` in test code, expecting rollback to still work -- commit hits the savepoint, but the outer transaction rollback still cleans up | Trust the existing `db_session` fixture's nested transaction pattern. Do NOT call `session.rollback()` inside handler code if it already uses `async with self._uow`. Let the fixture handle cleanup. |
| Dishka DI in Tests | Resolving handlers from the container but forgetting to be inside `async with app_container()` request scope | Always wrap handler resolution in `async with app_container() as request_container:` as shown in existing `test_create_brand.py` |
| Cross-Module Dependencies | `CreateProductHandler` depends on `ISupplierQueryService` from the supplier module. Mocking it incorrectly (e.g., returning wrong SupplierType) causes `SourceUrlRequiredError` in unexpected test paths | Create a shared test helper `stub_supplier_service()` that returns a consistent default, and override it explicitly in supplier-specific test scenarios |
| Domain Entity Construction | Creating domain entities directly via `__init__` instead of through factory methods (`Product.create()`, `Category.create_child()`) -- bypasses validation and guard initialization | Always use factory methods in tests. They validate inputs and properly initialize guards (`__attrs_post_init__`, `__initialized` flags). A `Product` built via `__init__` will not have `_Product__initialized` set correctly. |
| ORM Enum Mapping | Domain uses `ProductStatus.DRAFT` (Python StrEnum), ORM uses `ProductStatus` mapped through SQLAlchemy `Enum()`. Comparing domain enum to ORM enum can fail on `.value` vs direct comparison | Always reconstruct domain enums from ORM values: `ProductStatus(orm.status.value)` as the repo already does. Never compare raw ORM enum to domain enum directly. |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| N+1 in variant/SKU loading | Product list page takes 5+ seconds; DB shows hundreds of SELECT queries for 20 products | Always use `selectinload` chains when loading Products with variants. The `get_for_update_with_variants()` method does this correctly -- verify all query handlers follow the same pattern. | 50+ products with 3+ variants each |
| `COUNT(*)` subquery on every paginated list | Admin product list slows down as catalog grows; pagination adds 200ms+ per request | Already identified in CONCERNS.md. For hardening phase: measure baseline query times and add a performance assertion in integration tests. Do not fix pagination now, but document the baseline. | 5,000+ products |
| Full aggregate reload on every mutation | `ProductRepository.update()` does `selectinload(variants).selectinload(skus).selectinload(attribute_values)` on every update, even if only a product-level field changed | Acceptable for now given catalog size. If update latency becomes an issue, add a "light update" path for product-level-only changes. Log a performance warning if the aggregate has 100+ SKUs. | 50+ SKUs per product |
| Cartesian explosion in SKU matrix generation | `generate_sku_matrix` already caps at 1,000 combinations, but 5 attributes x 10 values each = 100,000 combinations before the cap is checked | The cap exists (MAX_SKU_COMBINATIONS = 1000) but test should verify it is enforced. Also verify the error message is user-friendly. | 4+ attributes selected with 5+ values each |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| EAV attribute injection via unvalidated JSON | Attacker submits arbitrary attribute codes/values that are not in the template, creating phantom data in the EAV tables | Verify `generate_sku_matrix._validate_selections()` and `assign_product_attribute` both enforce template membership. Write tests for rejected attribute IDs. |
| Price manipulation via SKU update | Negative prices, zero-currency prices, or compare_at_price lower than price accepted without validation | The `Money` value object should enforce non-negative amounts and currency validity. Write tests that submit negative price_amount and verify rejection. |
| Soft-delete bypass in admin API | Admin deletes a product but it remains accessible at `/product/{id}` because the get endpoint does not filter `deleted_at` | Already covered in Pitfall 6. Verify every public-facing endpoint filters soft-deleted records. |
| Slug collision after update | Product A has slug "nike-air-max", Product B updates its slug to "nike-air-max" -- the `check_slug_exists` method exists but tests must verify it is called on update, not just create | Write a test that creates two products, then updates the second to have the first's slug, and verify `ProductSlugConflictError` is raised. |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|------------|-----------------|
| Publishing product without prices | Product appears on storefront with no price -- users cannot purchase | The FSM already checks for priced SKUs on PUBLISHED transition. Verify this with tests. Surface the specific missing-price error to admin UI. |
| Deleting an attribute breaks existing products silently | Admin removes "Color" attribute; all products with color values now have orphan data | `delete_attribute` handler should check for existing product attribute values. Write a test verifying this protection exists (or document that it should be added). |
| Category template change invalidates child products | Admin changes "Shoes" category template; all shoe products now have attributes that do not match the new template | Template changes should cascade a "revalidation" or at minimum a warning. For hardening: document this as a known limitation and add it to CONCERNS. |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Product.create() auto-variant**: Creates a default variant, but tests must verify the variant has the correct `name_i18n` (copies from product title) and that `product.variants` is non-empty after creation.
- [ ] **Status FSM preconditions**: `transition_status()` checks for active SKUs when going to PUBLISHED or READY_FOR_REVIEW. But does it check that at least one SKU has a price? The code says yes -- verify with tests for each invalid transition.
- [ ] **Variant hash uniqueness**: `compute_variant_hash()` includes `variant_id` in the hash so different variants can both have empty-attributes SKUs. Test this edge case explicitly -- two variants, each with one SKU with no attributes, should NOT collide.
- [ ] **Soft-delete cascade**: `Product.soft_delete()` cascades to variants, which cascade to SKUs. Test the full cascade: product with 2 variants, 3 SKUs each -- after soft_delete, all 8 entities have non-null `deleted_at`.
- [ ] **Domain event emission after multi-step operations**: After `create_product` (which auto-creates variant), verify exactly one `ProductCreatedEvent` is in the event list, not zero and not two.
- [ ] **Category effective_template_id inheritance**: `Category.create_child()` computes `effective_template_id = template_id or parent.effective_template_id`. Test that a grandchild category inherits from grandparent when parent has no template.
- [ ] **Money VO roundtrip**: Money is decomposed to `price` (integer) + `currency` (string) in ORM. Verify that `compare_at_price > price` constraint is enforced somewhere (in domain or DB). Verify currency is preserved through roundtrip.
- [ ] **update() sentinel pattern**: Multiple entities use `...` (Ellipsis) as sentinel for "keep current value." Tests must verify that passing `None` clears the field while not passing it at all keeps the current value -- these are different behaviors.
- [ ] **Guard bypass in update methods**: Guarded fields (`status`, `slug`, `code`) use `object.__setattr__()` to bypass the `__setattr__` guard. Tests must verify both that direct assignment raises `AttributeError` AND that the official method (e.g., `transition_status()`) succeeds.

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|--------------|----------------|
| Import breakage from entity split | LOW | Revert the file split (git revert). Re-export from `__init__.py`. All downstream code continues working. |
| Mock-heavy tests hiding real bugs | MEDIUM | Identify the untested repository paths. Write targeted integration tests for the specific mapping methods (`_sync_variants`, `_sku_to_orm`). Do not rewrite all handler tests -- supplement them. |
| Orphan EAV data from template changes | HIGH | Write a data migration script that joins product_attribute_values against template bindings and flags orphans. Admin review + bulk cleanup. Cannot be automated safely without human verification. |
| Optimistic locking not working | MEDIUM | Add `version_id_col` to ORM model if missing. Write the concurrent-session test. Deploy fix. Existing data is unaffected -- the risk is overwritten data, which cannot be recovered without audit logs. |
| Soft-delete leaks in queries | LOW | Add `WHERE deleted_at IS NULL` to the offending query. Write the test. Redeploy. No data loss -- records were not actually deleted, just incorrectly visible. |
| Async MissingGreenlet in tests | LOW | Add `selectinload` to the offending query, or restructure the test to use `session.get()` for assertions. Pattern is well-established in existing tests. |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|-----------------|--------------|
| Mock-heavy tests hiding real bugs | Phase 1 (Domain entity tests) + Phase 2 (Repo integration tests) | Domain entity test file exists for Product with 20+ test cases. Repository roundtrip test exists with variant/SKU sync. |
| God-class split breaking imports | Phase 4 (Refactoring -- after tests exist) | All tests pass after split. `python -c "from src.modules.catalog.domain.entities import ..."` succeeds for all public names. |
| Optimistic locking untested | Phase 2 (Repository integration tests) | Test file contains concurrent-session test that verifies `ConcurrencyError`. |
| EAV attribute integrity gaps | Phase 1 (Domain analysis) + Phase 2 (Integration tests) | Negative tests exist for invalid attribute assignment. Template governance chain tested end-to-end. |
| Async lazy-load landmines | Phase 2 (Repository integration tests -- establish pattern) | All integration tests follow the "re-fetch for assertions" pattern. No `MissingGreenlet` in CI. |
| Soft-delete leaks | Phase 2 (Integration tests) + Phase 3 (Query handler tests) | Every list/get test includes a "soft-deleted entity is excluded" assertion. |
| Domain event accumulation | Phase 1 (Domain entity tests) + Phase 3 (Handler tests) | Event emission assertions present in every command handler test. |

## Sources

- Codebase analysis: `backend/src/modules/catalog/domain/entities.py`, `backend/src/modules/catalog/infrastructure/repositories/product.py`, `backend/src/modules/catalog/application/commands/create_product.py`, `backend/src/modules/catalog/application/commands/generate_sku_matrix.py`
- [EAV Anti-pattern analysis](https://cedanet.com.au/antipatterns/eav.php)
- [EAV design in PostgreSQL](https://www.cybertec-postgresql.com/en/entity-attribute-value-eav-design-in-postgresql-dont-do-it/)
- [DDD Aggregate Root design and the "God Aggregate" problem](https://fsck.sh/en/blog/ddd-eventsourcing-aggregates/)
- [DDD Testing Strategy](http://www.taimila.com/blog/ddd-and-testing-strategy/)
- [Testing strategies for CQRS applications](https://reintech.io/blog/testing-strategies-cqrs-applications)
- [Optimistic locking with SQLAlchemy -- child entity version bumping issue](https://github.com/cosmicpython/code/issues/53)
- [Optimistic locking in SQLAlchemy](https://oneuptime.com/blog/post/2026-01-25-optimistic-locking-sqlalchemy/view)
- [SQLAlchemy nested transaction testing](https://github.com/sqlalchemy/sqlalchemy/discussions/11658)
- [Transactional unit tests with async SQLAlchemy](https://www.core27.co/post/transactional-unit-tests-with-pytest-and-async-sqlalchemy)
- [N+1 problem in SQLAlchemy -- selectinload](https://sgoel.dev/posts/handling-the-n-1-selects-problem-in-sqlalchemy/)
- [Refactoring God Class in Python](https://softwarepatternslexicon.com/patterns-python/11/2/4/)
- [Mocks for Commands, Stubs for Queries](https://blog.ploeh.dk/2013/10/23/mocks-for-commands-stubs-for-queries/)

---
*Pitfalls research for: EAV Catalog Hardening*
*Researched: 2026-03-28*
