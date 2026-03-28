# Phase 7: Repository & Data Integrity - Research

**Researched:** 2026-03-28
**Status:** Complete
**Phase Goal:** All catalog repository implementations are proven correct against real PostgreSQL -- Data Mapper roundtrips, schema constraints, soft-delete filtering, and ORM mapping fidelity

---

## 1. Repository Inventory & Architecture

### Repository Types

The catalog module has **11 repository implementations** split into three categories:

**BaseRepository inheritors (7)** — generic CRUD via `BaseRepository[EntityType, ModelType]`:
1. `BrandRepository` — model: `Brand`, custom `add()` with IntegrityError handling
2. `CategoryRepository` — model: `Category`, tree operations (CTE, full_slug propagation)
3. `AttributeRepository` — model: `Attribute`, BehaviorFlags VO decomposition
4. `AttributeValueRepository` — model: `AttributeValue`, scoped uniqueness (attribute_id + code/slug)
5. `AttributeTemplateRepository` — model: `AttributeTemplate`, code uniqueness
6. `AttributeGroupRepository` — model: `AttributeGroup`, code uniqueness + attribute membership
7. `TemplateAttributeBindingRepository` — model: `TemplateAttributeBinding`, pair uniqueness
8. `ProductAttributeValueRepository` — model: `ProductAttributeValue`, duplicate guard

**Standalone implementations (2)** — custom CRUD, do NOT inherit BaseRepository:
9. `ProductRepository` — complex 3-level mapping (Product -> Variant -> SKU), Money VO decomposition, optimistic locking, variant/SKU sync
10. `MediaAssetRepository` — different interface signature (media/media_id vs entity/entity_id), bulk operations

### BaseRepository Generic CRUD Contract

`BaseRepository` provides: `add()`, `get()`, `update()`, `delete()`, `_field_exists()`, `get_for_update()`.

**Critical finding:** `BaseRepository.get()` does NOT filter soft-deleted records. It returns ANY row by primary key regardless of `deleted_at`. Only `ProductRepository.get()` explicitly checks `deleted_at is not None`. This means `BrandRepository.get()`, `CategoryRepository.get()`, etc. will return soft-deleted entities -- **but Brand and Category don't have `deleted_at` columns**, so this is correct for those entities. However, entities that DO have soft-delete but inherit BaseRepository's `get()` need auditing.

### Soft-Delete Column Audit

Checked ORM models for `deleted_at` column presence:
- **Has `deleted_at`:** Product, ProductVariant, SKU
- **No `deleted_at`:** Brand, Category, Attribute, AttributeValue, AttributeTemplate, AttributeGroup, TemplateAttributeBinding, ProductAttributeValue, MediaAsset, SKUAttributeValueLink

**Finding:** Soft-delete is ONLY on the Product aggregate hierarchy (Product, ProductVariant, SKU). Other entities use hard-delete. This means the REPO-04 soft-delete audit focuses on:
- `ProductRepository.get()` -- already filters deleted_at
- `ProductRepository.get_with_variants()` -- filters deleted Product, deleted Variants, deleted SKUs
- `ProductRepository.get_for_update_with_variants()` -- filters all three levels
- `ProductRepository.check_slug_exists()` -- filters via `_field_exists` which checks `deleted_at IS NULL`
- `ProductRepository.check_sku_code_exists()` -- explicitly filters `deleted_at IS NULL`
- `BrandRepository.has_products()` -- filters `OrmProduct.deleted_at.is_(None)`
- `CategoryRepository.has_products()` -- filters `OrmProduct.deleted_at.is_(None)`

## 2. Data Mapping Complexity Analysis

### Product Repository (Highest Complexity)

**3-level mapping chain:** Product -> ProductVariant -> SKU -> SKUAttributeValueLink

**Money VO decomposition on SKU:**
- `domain.price: Money(amount, currency)` -> `orm.price: int, orm.currency: str`
- `domain.compare_at_price: Money(amount, currency)` -> `orm.compare_at_price: int` (shares currency column)
- Nullable: both price and compare_at_price can be None

**Money VO on ProductVariant:**
- `domain.default_price: Money(amount, currency)` -> `orm.default_price: int, orm.default_currency: str`
- Nullable: default_price can be None

**ORM-only fields (not in domain entity, set on create only):**
- Product: `popularity_score`, `is_visible`, `attributes` (JSONB)
- SKU: `main_image_url`, `attributes_cache` (JSONB)

**Variant/SKU sync (_sync_variants, _sync_skus_for_variant):**
- Diff-based reconciliation: adds new, updates existing, removes missing
- Removal only targets non-deleted entities (`deleted_at is None` check)
- SKU attribute value links use diff-based sync too

**Optimistic locking:**
- Product ORM model: `__mapper_args__ = {"version_id_col": version}` -- SQLAlchemy auto-increments on flush
- SKU ORM model: same `version_id_col` configuration
- `ProductRepository` catches `StaleDataError` and raises `ConcurrencyError`
- **Important:** On create, `_to_orm` sets `version` explicitly; on update, it skips version to let SA manage it

### Attribute Repository (Medium Complexity)

**BehaviorFlags VO decomposition:**
- Domain: `BehaviorFlags(is_filterable, is_searchable, search_weight, is_comparable, is_visible_on_card)`
- ORM: 5 separate columns (`is_filterable`, `is_searchable`, `search_weight`, `is_comparable`, `is_visible_on_card`)
- `_to_domain` wraps into `BehaviorFlags` VO
- `_to_orm` unpacks to flat columns via `entity.is_filterable` etc. (uses properties from domain entity that delegate to behavior)

### Category Repository (Medium Complexity)

**Tree operations:**
- `full_slug` materialized path
- `update_descendants_full_slug()` -- bulk UPDATE with string prefix replacement
- `propagate_effective_template_id()` -- recursive CTE UPDATE
- Slug uniqueness scoped to parent_id (composite unique: parent_id + slug)

### JSONB Fields (All Repositories)

Multiple entities use JSONB for i18n:
- Brand: no JSONB (name is plain string)
- Category: `name_i18n` (JSONB)
- Product: `title_i18n`, `description_i18n` (JSONB)
- ProductVariant: `name_i18n`, `description_i18n` (JSONB)
- Attribute: `name_i18n`, `description_i18n` (JSONB)
- AttributeValue: `value_i18n`, `meta_data` (JSONB)
- AttributeTemplate: `name_i18n`, `description_i18n` (JSONB)
- AttributeGroup: `name_i18n` (JSONB)

**Mapping pattern:** `dict(orm.field) if orm.field else {}` -- converts MutableDict to plain dict for domain

### ARRAY Fields

- Product: `tags: list[str]` (ARRAY(String))
- AttributeValue: `search_aliases: list[str]` (ARRAY(String))

## 3. Schema Constraints Inventory

### Foreign Key Constraints

| Table | Column | References | On Delete |
|-------|--------|------------|-----------|
| categories.parent_id | categories.id | RESTRICT |
| categories.template_id | attribute_templates.id | SET NULL |
| categories.effective_template_id | attribute_templates.id | SET NULL |
| attributes.group_id | attribute_groups.id | SET NULL |
| attribute_values.attribute_id | attributes.id | CASCADE |
| template_attribute_bindings.template_id | attribute_templates.id | CASCADE |
| template_attribute_bindings.attribute_id | attributes.id | CASCADE |
| products.primary_category_id | categories.id | RESTRICT |
| products.brand_id | brands.id | RESTRICT |
| products.supplier_id | suppliers.id | RESTRICT |
| product_variants.product_id | products.id | CASCADE |
| product_variants.default_currency | currencies.code | RESTRICT |
| media_assets.product_id | products.id | CASCADE |
| media_assets.variant_id | product_variants.id | CASCADE |
| skus.product_id | products.id | CASCADE |
| skus.variant_id | product_variants.id | CASCADE |
| skus.currency | currencies.code | RESTRICT |
| sku_attribute_values.sku_id | skus.id | CASCADE |
| sku_attribute_values.attribute_id | attributes.id | CASCADE |
| sku_attribute_values.attribute_value_id | attribute_values.id | RESTRICT |
| product_attribute_values.product_id | products.id | CASCADE |
| product_attribute_values.attribute_id | attributes.id | CASCADE |
| product_attribute_values.attribute_value_id | attribute_values.id | RESTRICT |

### Unique Constraints

| Table | Constraint Name | Columns | Partial |
|-------|----------------|---------|---------|
| brands | uix_brands_name | name | No |
| brands | uix_brands_slug | slug | No |
| categories | uix_categories_slug | parent_id, slug | No (NULLS NOT DISTINCT) |
| attributes | uix_attributes_code | code | No |
| attributes | uix_attributes_slug | slug | No |
| attribute_groups | uix_attribute_groups_code | code | No |
| attribute_templates | (unique on code) | code | No |
| attribute_values | uix_attr_val_code | attribute_id, code | No |
| attribute_values | uix_attr_val_slug | attribute_id, slug | No |
| template_attribute_bindings | uix_template_attr_binding | template_id, attribute_id | No |
| products | uix_products_slug | slug | Yes (WHERE deleted_at IS NULL) |
| skus | uix_skus_sku_code | sku_code | Yes (WHERE deleted_at IS NULL) |
| skus | uix_skus_variant_hash | variant_hash | Yes (WHERE deleted_at IS NULL) |
| sku_attribute_values | uix_sku_single_attribute_value | sku_id, attribute_id | No |
| product_attribute_values | uix_product_single_attribute_value | product_id, attribute_id | No |
| media_assets | uix_media_single_main_per_variant | product_id, variant_id | Yes (WHERE role = 'MAIN') |

### Check Constraints

| Table | Constraint Name | Expression |
|-------|----------------|------------|
| attributes | ck_attributes_search_weight | search_weight BETWEEN 1 AND 10 |

## 4. FK Dependencies for Test Data Setup

Creating a Product with variants and SKUs requires seeding:
1. `currencies` table -- "RUB" entry (FK from product_variants.default_currency and skus.currency)
2. `brands` table -- one brand (FK from products.brand_id)
3. `categories` table -- one category (FK from products.primary_category_id)
4. Optionally: `suppliers` table -- (FK from products.supplier_id, nullable)
5. Optionally: `attributes` + `attribute_values` -- for SKU attribute value links
6. Optionally: `attribute_groups` -- for attributes.group_id

**Important:** The `currencies` table is in the `geo` module. The test infrastructure creates tables via `Base.metadata.create_all` which should include it. Need to verify the `currencies` table is populated with "RUB" before tests.

## 5. Existing Test Coverage

### Already Tested (in test_brand.py):
- `BrandRepository.add()` and `get()` -- basic roundtrip
- `BrandRepository.check_slug_exists()` -- true/false cases

### Already Tested (in test_brand_extended.py, test_category.py, test_category_extended.py, test_category_effective_family.py):
- Need to check what's covered to avoid duplication

### Not Tested:
- ProductRepository -- no test file exists
- AttributeRepository -- no test file exists
- AttributeValueRepository -- no test file exists
- AttributeTemplateRepository -- no test file exists
- AttributeGroupRepository -- no test file exists
- TemplateAttributeBindingRepository -- no test file exists
- MediaAssetRepository -- no test file exists
- ProductAttributeValueRepository -- no test file exists
- All schema constraint violation tests
- All soft-delete filtering tests
- All ORM mapping fidelity tests

## 6. Optimistic Locking Investigation

**Blocker from STATE.md:** "Optimistic locking version_id_col configuration needs inspection during Phase 7 planning."

**Finding:** Both `Product` and `SKU` ORM models have:
```python
__mapper_args__: ClassVar[dict[str, Any]] = {
    "version_id_col": version,
}
```

This tells SQLAlchemy to:
1. Auto-increment `version` on every flush
2. Include `WHERE version = :old_version` in UPDATE statements
3. Raise `StaleDataError` if the row was modified concurrently

**ProductRepository handling:**
- `add()`: catches `StaleDataError` -> raises `ConcurrencyError`
- `update()`: catches `StaleDataError` -> raises `ConcurrencyError`
- On create: `_to_orm` sets `version = entity.version` explicitly
- On update: `_to_orm` skips version assignment (lets SA manage)

**Concern:** The `_to_orm` method on create sets `orm.version = entity.version` (usually 1). After flush, SA increments it. The `add()` method returns the original `entity` (not re-read from ORM), so the returned entity has `version=1` while the DB now has `version=1` (SA sets it on INSERT via server_default, then the mapper manages it). This should be verified in the roundtrip test.

## 7. Test Infrastructure Needs

### Required Seed Data
- Currency "RUB" must exist in the currencies table for Product/SKU tests
- A Brand and Category must be pre-created for Product tests

### Recommended Test Patterns
1. **Roundtrip pattern:** `entity = create() -> add(entity) -> get(id) -> assert all fields match`
2. **Constraint violation pattern:** `try: add(invalid_data) -> expect IntegrityError or domain exception`
3. **Soft-delete filter pattern:** `add(active) + add(soft_deleted) -> get/list -> assert only active returned`
4. **N+1 detection pattern:** Use `assert_query_count()` for ProductRepository eager loading

### Currency Table Seeding
The test infrastructure uses `Base.metadata.create_all` which creates the schema but does NOT populate seed data. Need a fixture that inserts "RUB" into currencies before Product/SKU tests. This can be a session-scoped fixture.

## 8. Validation Architecture

### Test Types

| Requirement | Test Type | Automated | Estimated Tests |
|-------------|-----------|-----------|-----------------|
| REPO-01 | Integration (DB) | pytest + testcontainers | ~15 tests |
| REPO-02 | Integration (DB) | pytest + testcontainers | ~20 tests |
| REPO-03 | Integration (DB) | pytest + testcontainers | ~15 tests |
| REPO-04 | Integration (DB) | pytest + testcontainers | ~10 tests |
| REPO-05 | Integration (DB) | pytest + testcontainers | ~12 tests |

### Verification Commands

- Quick run: `cd backend && python -m pytest tests/integration/modules/catalog/infrastructure/repositories/ -x -q`
- Full suite: `cd backend && python -m pytest tests/integration/ -x -q --timeout=120`
- Single file: `cd backend && python -m pytest tests/integration/modules/catalog/infrastructure/repositories/test_product.py -v`

### Risk Areas

1. **Highest risk:** ProductRepository 3-level roundtrip -- complex Money decomposition, JSONB, nested collections
2. **Medium risk:** Soft-delete filtering on ProductRepository methods -- multiple methods to audit
3. **Medium risk:** Currency FK dependency -- test data setup needs "RUB" seed
4. **Lower risk:** Simple BaseRepository inheritors (Brand, AttributeGroup) -- generic CRUD is straightforward

---

## RESEARCH COMPLETE

Research covers all 5 requirements (REPO-01 through REPO-05). Key findings:
- 11 repositories total, 2 standalone (Product, MediaAsset), 9 BaseRepository inheritors
- Soft-delete is ONLY on Product/Variant/SKU -- other entities use hard-delete
- Product mapping is most complex: 3-level, Money VO, JSONB, optimistic locking
- Currency table "RUB" seed data needed for Product/SKU integration tests
- Optimistic locking correctly configured via `version_id_col` on Product and SKU
- BaseRepository.get() does NOT filter soft-deletes (correct -- non-Product entities have no deleted_at)
