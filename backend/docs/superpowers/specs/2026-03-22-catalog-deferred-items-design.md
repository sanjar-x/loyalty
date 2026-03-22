# Catalog Module — Deferred Items Design Spec

**Date:** 2026-03-22
**Status:** Approved
**Scope:** 6 deferred items from 10+ rounds of code review

---

## 1. BrandLogoUploadInitiatedEvent.event_type fix

**Problem:** Class is `BrandLogoUploadInitiatedEvent` but `event_type = "BrandCreatedEvent"` — a naming lie kept for backward compat. Project is not in production, so no backward compat needed.

**Fix:**

- `events.py`: Change `event_type` to `"BrandLogoUploadInitiatedEvent"`
- `outbox/tasks.py`: Change `register_event_handler("BrandCreatedEvent", _handle_brand_created)` to `register_event_handler("BrandLogoUploadInitiatedEvent", _handle_brand_logo_upload_initiated)`. Rename handler function accordingly.
- `storage/application/consumers/brand_events.py`: Rename `handle_brand_created_event` to `handle_brand_logo_upload_initiated_event`. Update docstring.
- Tests: Update all assertions checking `event_type == "BrandCreatedEvent"` to `"BrandLogoUploadInitiatedEvent"`. Update test class/function names referencing "BrandCreated".

**Files:**

- `src/modules/catalog/domain/events.py`
- `src/infrastructure/outbox/tasks.py`
- `src/modules/storage/application/consumers/brand_events.py`
- `tests/unit/modules/catalog/domain/test_events.py`
- `tests/unit/infrastructure/outbox/test_tasks.py`
- `tests/unit/modules/storage/application/consumers/test_brand_events.py`
- `tests/integration/modules/catalog/application/commands/test_create_brand.py`

---

## 2 + 6. Unified PATCH Semantics via `model_fields_set`

**Problem:** Three coexisting sentinel patterns (`...` Ellipsis, `_SENTINEL = object()`, `_UNSET = object()`) across domain entities, schemas, and routers. Complex, type-unsafe, and non-idiomatic for Pydantic v2.

**Solution:** Use Pydantic v2's `model_fields_set` to distinguish "not sent" from "explicitly null".

**Key design note:** `model_fields_set` contains **Python field names** (not aliases), so `supplier_id` will be in the set when client sends `{"supplierId": null}`. This was verified with CamelModel aliasing.

### Nullable field categories

Fields fall into two categories in update schemas:

1. **Truly nullable** (can be set to None): `supplier_id`, `country_of_origin`, `compare_at_price_amount`, `description_i18n`, `validation_rules`, `value_group`, `flag_overrides`, `filter_settings` — these use `field: Type | None = None`
2. **Required in business** (cannot be None but optional in PATCH): `brand_id`, `primary_category_id`, `title_i18n`, `name_i18n`, `slug` — these use `field: Type | None = None` in schema but **domain entity `.update()` rejects None** with ValueError

Domain validation is the enforcement layer — schemas are permissive, domain rejects invalid state. This is consistent with the existing Clean Architecture pattern where domain entities guard their own invariants.

### Schemas

All 7 update request schemas refactored:

- `ProductUpdateRequest`, `SKUUpdateRequest`, `AttributeUpdateRequest`, `AttributeValueUpdateRequest`, `CategoryAttributeBindingUpdateRequest`, `BrandUpdateRequest`, `CategoryUpdateRequest`
- Replace `field: Type = ...  # type: ignore` with `field: Type | None = None`
- Remove all `# type: ignore[assignment]` comments
- `at_least_one_field` validators rewritten:
  - Schemas WITH `version` field: `if not (self.model_fields_set - {"version"}):`
  - Schemas WITHOUT `version` field: `if not self.model_fields_set:`

### Routers

All 7 update routers refactored:

- `router_products.py`, `router_skus.py`, `router_attributes.py`, `router_attribute_values.py`, `router_category_bindings.py`, `router_brands.py`, `router_categories.py`
- Remove `_UNSET = object()` from `router_products.py`
- Build `update_kwargs` from `request.model_fields_set`:
  ```python
  update_kwargs = {
      field: getattr(request, field)
      for field in request.model_fields_set
      if field != "version"
  }
  ```
- Pass only provided fields to command/handler

### Domain Entities

5 `.update()` methods refactored in `entities.py`:

- `Product.update()`, `SKU.update()`, `Attribute.update()`, `AttributeValue.update()`, `CategoryAttributeBinding.update()`
- Remove `_SENTINEL = object()` module-level definition
- Remove all Ellipsis sentinels from parameters
- All params use `param: Type | None = None` — caller passes only what was provided
- Methods use `if param is not None:` for required fields, and check membership for truly nullable fields

### Application Commands

7 update command files refactored:

- `update_product.py`, `update_sku.py`, `update_attribute.py`, `update_attribute_value.py`, `update_category_attribute_binding.py`, `update_brand.py`, `update_category.py`
- Replace sentinel defaults with `None`
- Remove `_SENTINEL` definitions
- Handlers receive `**update_kwargs` from router and pass to entity `.update(**update_kwargs)`

### Implementation approach

Refactor one entity at a time (per-entity commits) to reduce blast radius:

1. Brand (simplest — no sentinels currently)
2. Category (no sentinels)
3. AttributeGroup (no sentinels, but include for consistency)
4. Attribute (has Ellipsis for `validation_rules` and `group_id`)
5. AttributeValue (has Ellipsis for `value_group`)
6. CategoryAttributeBinding (has Ellipsis for `flag_overrides`/`filter_settings`)
7. SKU (has `_SENTINEL` for `compare_at_price`)
8. Product (has `_SENTINEL` for `supplier_id`/`country_of_origin`, plus `_UNSET` in router)

---

## 3. meta_data Column Name — Keep As-Is

**Problem:** `meta_data` uses underscore, but standard English is `metadata`.

**Decision:** Keep `meta_data`. SQLAlchemy `DeclarativeBase` reserves `metadata` as a class attribute for the `MetaData` object. This is deliberate collision avoidance.

**Fix:** Add explanatory comment to ORM model (`models.py`) and domain entity (`entities.py`):

```python
# Named `meta_data` (not `metadata`) to avoid collision with SQLAlchemy Base.metadata
```

---

## 4. BaseRepository Adoption (6 Repos)

**Problem:** 6 of 8 non-Category repositories manually duplicate CRUD. `CategoryRepository` already extends `BaseRepository`. `ProductRepository` and `MediaAssetRepository` are kept standalone due to complex custom logic.

### Interface hierarchy

Each migrated repo inherits from BOTH `BaseRepository` AND its domain interface:

```python
class BrandRepository(
    BaseRepository[DomainBrand, OrmBrand],
    IBrandRepository,
    model_class=OrmBrand,
):
```

This works because:

- `BaseRepository` provides concrete `add`/`get`/`update`/`delete` implementations
- `IBrandRepository extends ICatalogRepository[DomainBrand]` which declares the same abstract methods
- Python MRO resolves `BaseRepository`'s implementations for the abstract methods
- Subclasses access `self._session` for custom query methods (inherited from `BaseRepository.__init__`)

This is the exact pattern already used by `CategoryRepository`.

### Repos to migrate:

- `BrandRepository`
- `AttributeGroupRepository`
- `AttributeRepository`
- `AttributeValueRepository`
- `CategoryAttributeBindingRepository`
- `ProductAttributeValueRepository`

Each retains only custom query methods. Generic CRUD is inherited.

### Keep standalone:

- `ProductRepository` (complex `_sync_skus`, optimistic locking, `StaleDataError` catch)
- `MediaAssetRepository` (custom `processing_status` mapping, `has_main_for_variant`)

---

## 5. list_product_attributes Implementation

**Problem:** Query handler is a stub returning `[]`. The ORM model `ProductAttributeValue` exists and assign/remove commands work.

### ProductAttributeReadModel fields

Define in `read_models.py`:

```python
class ProductAttributeReadModel(BaseModel):
    id: uuid.UUID                          # PAV row id
    product_id: uuid.UUID
    attribute_id: uuid.UUID
    attribute_value_id: uuid.UUID | None
    attribute_code: str                     # from joined Attribute
    attribute_name_i18n: dict[str, str]     # from joined Attribute
```

### Handler implementation

- Inject `AsyncSession`
- Query `ProductAttributeValue` JOIN `Attribute` for code + name
- Return `list[ProductAttributeReadModel]` (bare list, no pagination — ≤30 attrs per product)
- Remove stale MT-16 comments and commented-out code

### Affected files

- `src/modules/catalog/application/queries/read_models.py` — new `ProductAttributeReadModel`
- `src/modules/catalog/application/queries/list_product_attributes.py` — implement handler
- `src/modules/catalog/presentation/router_product_attributes.py` — update response mapping if needed
- `src/modules/catalog/presentation/dependencies.py` — verify DI provider for handler

---

## Test Strategy

- **All items:** Existing tests must pass after refactoring. Run full test suite after each item.
- **#1:** Update test assertions for event_type strings.
- **#2+6:** Per-entity commits. After each entity, verify its update endpoint works via existing integration tests.
- **#4:** Each migrated repo should pass its existing test suite unchanged (interface contract preserved).
- **#5:** Add unit test for the new query handler.

---

## Implementation Order

1. **#1** (event_type fix) — independent, quick
2. **#3** (meta_data comment) — independent, trivial
3. **#5** (list_product_attributes) — independent, functional fix
4. **#4** (BaseRepository adoption) — independent, structural
5. **#2 + #6** (PATCH semantics) — largest, per-entity commits, do last
