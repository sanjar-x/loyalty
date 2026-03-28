# Phase 7: Repository & Data Integrity - Context

**Gathered:** 2026-03-28 (auto mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Prove all catalog repository implementations are correct against real PostgreSQL — Data Mapper roundtrips (create-read-update-delete), schema constraints at the DB level, soft-delete filtering consistency, and ORM-to-domain mapping fidelity. This is the first INTEGRATION test phase — tests use real PostgreSQL via testcontainers, not fakes. Prior phases tested domain logic (Phases 2-3) and handler orchestration (Phases 4-6) in isolation.

</domain>

<decisions>
## Implementation Decisions

### Test Scope and Organization
- **D-01:** Extend existing integration test files (test_brand.py, test_category.py) where they exist. Create new files for uncovered repositories: test_product.py, test_attribute.py, test_attribute_template.py, test_media_asset.py, test_product_attribute_value.py.
- **D-02:** All tests under `backend/tests/integration/modules/catalog/infrastructure/repositories/`. Use real PostgreSQL via db_session fixture (nested-transaction rollback per test).
- **D-03:** Do NOT duplicate tests that already exist and pass in test_brand.py and test_category.py — focus on gaps.

### Product Repository Roundtrip (REPO-01)
- **D-04:** Full 3-level roundtrip: Create Product with Variants and SKUs → read back → verify every field survives. This is the most complex and critical test.
- **D-05:** Specifically verify: Money decomposition (amount_minor + currency columns), JSONB i18n fields (title_i18n, description_i18n), nested variant→SKU collections loaded correctly, soft-delete cascade via ORM.
- **D-06:** Test the ProductRepository specifically (it's a custom implementation, NOT inheriting BaseRepository) — verify _to_domain() and _to_orm() mappings are complete.

### Schema Constraint Verification (REPO-03)
- **D-07:** Test DB constraints directly by attempting invalid operations via SQLAlchemy and asserting IntegrityError. This verifies migration-defined constraints, not application validation.
- **D-08:** Constraints to verify: FK constraints (product→brand, product→category, variant→product, SKU→variant), unique constraints (brand slug, category slug, product slug, sku_code), check constraints (if any defined in migrations).
- **D-09:** Also verify that ORM model cascade configurations match domain expectations (e.g., deleting a Product cascades to variants at the DB level).

### Soft-Delete Filter Audit (REPO-04)
- **D-10:** Systematic audit: for every repository method that returns entities, verify soft-deleted records are excluded.
- **D-11:** Test pattern: insert both a soft-deleted and an active entity, call the repository method, verify only the active entity is returned. Build a reusable helper for this.
- **D-12:** Cover all repositories with list/get methods: ProductRepository, BrandRepository, CategoryRepository, AttributeRepository, AttributeValueRepository, MediaAssetRepository.

### ORM Mapping Fidelity (REPO-05)
- **D-13:** For each entity type, verify that ALL fields survive a full create→read roundtrip through ORM models without data loss or type coercion errors.
- **D-14:** Pay special attention to: Money value object (two-column decomposition), JSONB fields (i18n dicts), UUID fields (uuid7 preservation), datetime fields (timezone handling), enum fields (StrEnum↔string mapping), nullable fields (None preservation).

### N+1 Query Detection
- **D-15:** Use Phase 1 query counter (tests/utils/query_counter.py) for ProductRepository tests — the 3-level eager loading (Product→Variant→SKU) is the primary N+1 risk.
- **D-16:** Not needed for simple CRUD repos (Brand, Category, Attribute) — single-level entities have no N+1 risk.

### Optimistic Locking
- **D-17:** STATE.md noted "optimistic locking version_id_col configuration needs inspection during Phase 7 planning." The researcher should inspect the version column usage in ProductRepository and verify it's correctly configured.

### Claude's Discretion
- Exact number of FK constraint tests per entity
- Whether to test all CRUD operations or focus on create-read roundtrip
- Query count baselines for Product repository (exact number depends on eager loading config)
- Whether to create a shared soft-delete audit helper fixture or keep it inline

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Repository implementations (source of truth)
- `backend/src/modules/catalog/infrastructure/repositories/product.py` — ProductRepository (custom, complex 3-level mapping)
- `backend/src/modules/catalog/infrastructure/repositories/base.py` — BaseRepository generic CRUD (inherited by most repos)
- `backend/src/modules/catalog/infrastructure/repositories/brand.py` — BrandRepository
- `backend/src/modules/catalog/infrastructure/repositories/category.py` — CategoryRepository (tree operations)
- `backend/src/modules/catalog/infrastructure/repositories/attribute.py` — AttributeRepository
- `backend/src/modules/catalog/infrastructure/repositories/attribute_value.py` — AttributeValueRepository
- `backend/src/modules/catalog/infrastructure/repositories/attribute_template.py` — AttributeTemplateRepository
- `backend/src/modules/catalog/infrastructure/repositories/attribute_group.py` — AttributeGroupRepository
- `backend/src/modules/catalog/infrastructure/repositories/media_asset.py` — MediaAssetRepository (custom, not BaseRepository)
- `backend/src/modules/catalog/infrastructure/repositories/product_attribute_value.py` — ProductAttributeValueRepository
- `backend/src/modules/catalog/infrastructure/repositories/template_attribute_binding.py` — TemplateAttributeBindingRepository

### ORM models
- `backend/src/modules/catalog/infrastructure/models.py` — All catalog ORM models (defines columns, relationships, cascade config)

### Existing integration tests (extend, don't duplicate)
- `backend/tests/integration/modules/catalog/infrastructure/repositories/test_brand.py` — BrandRepository tests
- `backend/tests/integration/modules/catalog/infrastructure/repositories/test_brand_extended.py` — Extended brand tests
- `backend/tests/integration/modules/catalog/infrastructure/repositories/test_category.py` — CategoryRepository tests
- `backend/tests/integration/modules/catalog/infrastructure/repositories/test_category_extended.py` — Extended category tests
- `backend/tests/integration/modules/catalog/infrastructure/repositories/test_category_effective_family.py` — Category tree tests

### Test infrastructure
- `backend/tests/conftest.py` — Root conftest with db_session fixture (nested transaction rollback)
- `backend/tests/integration/conftest.py` — Integration conftest overrides
- `backend/tests/utils/query_counter.py` — N+1 query detection utility (Phase 1)
- `backend/tests/factories/orm_factories.py` — Polyfactory ORM model factories for DB seeding

### Migrations (schema constraints)
- `backend/alembic/` — Migration files defining FK, unique, check constraints

### Domain entities (mapping targets)
- `backend/src/modules/catalog/domain/entities.py` — Domain entities (what _to_domain() must produce)
- `backend/src/modules/catalog/domain/value_objects.py` — Money, BehaviorFlags (complex mapping)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Existing test_brand.py and test_category.py — extend these, don't rewrite
- Polyfactory ORM factories (orm_factories.py) — seed DB with valid ORM models
- Query counter (tests/utils/query_counter.py) — use for Product repo N+1 detection
- db_session fixture with nested-transaction rollback — per-test isolation

### Established Patterns
- Integration tests use `db_session: AsyncSession` fixture directly
- Repositories constructed with `Repository(session=db_session)`
- Arrange-Act-Assert with comments pattern
- ORM factories create model instances, flush to DB, then test repository reads

### Integration Points
- New test files under `backend/tests/integration/modules/catalog/infrastructure/repositories/`
- Tests import repositories from `src.modules.catalog.infrastructure.repositories.*`
- Tests import ORM models from `src.modules.catalog.infrastructure.models`
- Tests use Polyfactory factories for seeding and entity builders for domain assertions

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Key shift: this is the first phase testing against real PostgreSQL. The Product 3-level roundtrip (REPO-01) is the highest-risk test and should be the first plan.

</specifics>

<deferred>
## Deferred Ideas

- Performance/N+1 benchmarking across all query handlers — v2 PERF-01
- Cursor-based pagination efficiency audit — v2 PERF-02
- Concurrent session tests for optimistic locking — v2 ADV-02

</deferred>

---

*Phase: 07-repository-data-integrity*
*Context gathered: 2026-03-28*
