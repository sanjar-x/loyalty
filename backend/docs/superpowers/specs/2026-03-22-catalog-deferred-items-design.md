# Catalog Module — Deferred Items Design Spec

**Date:** 2026-03-22
**Status:** Approved
**Scope:** 6 deferred items from 10+ rounds of code review

---

## 1. BrandLogoUploadInitiatedEvent.event_type fix

**Problem:** Class is `BrandLogoUploadInitiatedEvent` but `event_type = "BrandCreatedEvent"` — a naming lie kept for backward compat. Project is not in production, so no backward compat needed.

**Fix:** Change `event_type` to `"BrandLogoUploadInitiatedEvent"`. Update Outbox routing in `outbox/tasks.py` and consumer in `storage/application/consumers/brand_events.py`. Update all tests asserting the old string.

**Files:**
- `src/modules/catalog/domain/events.py`
- `src/infrastructure/outbox/tasks.py`
- `src/modules/storage/application/consumers/brand_events.py`
- Related test files

---

## 2 + 6. Unified PATCH Semantics via `model_fields_set`

**Problem:** Three coexisting sentinel patterns (`...` Ellipsis, `_SENTINEL = object()`, `_UNSET = object()`) across domain entities, schemas, and routers. Complex, type-unsafe, and non-idiomatic for Pydantic v2.

**Solution:** Use Pydantic v2's `model_fields_set` to distinguish "not sent" from "explicitly null".

### Schemas
- All update request schemas: replace `field: Type = ...  # type: ignore` with `field: Type | None = None`
- `at_least_one_field` validators rewritten to check `if not (self.model_fields_set - {"version"}):`
- Remove all `# type: ignore[assignment]` comments

### Routers
- Remove `_UNSET = object()` from `router_products.py`
- Build `update_kwargs` from `request.model_fields_set`:
  ```python
  update_kwargs = {
      field: getattr(request, field)
      for field in request.model_fields_set
      if field != "version"
  }
  ```
- Pass only provided fields to command constructor or handler

### Domain Entities
- `.update()` methods keep current signatures with `None` defaults
- Remove `_SENTINEL = object()` from `entities.py`
- Remove all Ellipsis sentinels from `.update()` parameters
- All params use simple `param: Type | None = None` — caller passes only what was provided

### Application Commands
- Update command dataclasses: replace sentinel defaults with `None`
- Remove `_SENTINEL` imports and definitions from command files
- Handlers pass `update_kwargs` dict to entity `.update(**kwargs)`

### Affected Files

**Schemas:** `ProductUpdateRequest`, `SKUUpdateRequest`, `AttributeUpdateRequest`, `AttributeValueUpdateRequest`, `CategoryAttributeBindingUpdateRequest`

**Routers:** `router_products.py`, `router_skus.py`, `router_attributes.py`, `router_attribute_values.py`, `router_category_bindings.py`

**Commands:** `update_product.py`, `update_sku.py`, `update_attribute.py`, `update_attribute_value.py`, `update_category_attribute_binding.py`

**Domain:** `entities.py` (5 `.update()` methods)

---

## 3. meta_data Column Name — Keep As-Is

**Problem:** `meta_data` uses underscore, but standard English is `metadata`.

**Decision:** Keep `meta_data`. SQLAlchemy `Base` reserves `metadata` as a class attribute. This is a deliberate collision avoidance, not a mistake.

**Fix:** Add explanatory comment to ORM model (`models.py`) and domain entity (`entities.py`).

---

## 4. BaseRepository Adoption (6 Repos)

**Problem:** 8 of 9 repositories manually duplicate the same CRUD pattern. Only `CategoryRepository` extends `BaseRepository`.

**Fix:** Migrate 6 simple repositories to extend `BaseRepository`:
- `BrandRepository`
- `AttributeGroupRepository`
- `AttributeRepository`
- `AttributeValueRepository`
- `CategoryAttributeBindingRepository`
- `ProductAttributeValueRepository`

Each retains only its custom query methods (e.g., `check_slug_exists`, `get_for_update`, `bulk_update_sort_order`). Generic `add`/`get`/`update`/`delete` are inherited.

**Keep standalone:** `ProductRepository` (complex `_sync_skus`, optimistic locking) and `MediaAssetRepository` (custom return types, processing status mapping).

**Pre-requisite:** `BaseRepository` interface methods must align with what each repo needs. Verify `add()` returns domain entity, `update()` calls `flush()`, `delete()` uses SQL DELETE statement.

---

## 5. list_product_attributes Implementation

**Problem:** Query handler is a stub returning `[]`. The ORM model `ProductAttributeValue` exists and `assign`/`remove` commands work.

**Fix:** Implement the query handler following CQRS read-side pattern:
- Inject `AsyncSession`
- Query `ProductAttributeValue` ORM model joined with `Attribute` for attribute metadata
- Return `list[ProductAttributeReadModel]` (bare list, no pagination — products have ≤30 attributes)
- Remove stale MT-16 comments and commented-out code
- Define `ProductAttributeReadModel` in `read_models.py` if not present

---

## Implementation Order

1. **#1** (event_type fix) — independent, quick
2. **#3** (meta_data comment) — independent, trivial
3. **#5** (list_product_attributes) — independent, functional fix
4. **#4** (BaseRepository adoption) — independent, structural
5. **#2 + #6** (PATCH semantics) — largest, touches most files, do last
