# AttributeFamily with Polymorphic Inheritance — Design Spec

**Date:** 2026-03-25
**Goal:** Replace direct category-attribute bindings with a standalone `AttributeFamily` entity that supports unlimited-depth polymorphic inheritance, per-level overrides, and attribute exclusions.

---

## Context

- **Current state:** Attributes are bound directly to categories via `category_attribute_rules`. No inheritance — child categories do not receive parent's attributes.
- **Problem:** Binding "size" to "Clothing" does not propagate to "T-shirts". Admins must duplicate bindings manually for every leaf category.
- **Target:** `AttributeFamily` hierarchy where child families inherit parent's attributes, can override settings, exclude inherited attributes, and add their own.

---

## Core Concepts

### AttributeFamily

A standalone entity defining a set of attributes for products. Families form their own tree hierarchy independent of categories.

**Example:**

```
Family "Clothing"
├── attrs: [size (optional), color (required)]
│
└── Family "T-shirts" (extends "Clothing")
    ├── inherited: [size (→ required override), color (required)]
    ├── own: [material (recommended)]
    │
    └── Family "Sports T-shirts" (extends "T-shirts")
        ├── inherited: [size (required), color (required), material (recommended)]
        ├── excluded: [color]
        ├── own: [moisture_wicking (required)]
        └── effective: [size, material, moisture_wicking]
```

### Relationship to Categories

- `Category.family_id` — optional FK to `AttributeFamily`
- Category without a family — products have no required attribute schema
- Multiple categories can share the same family
- Family assignment is independent of category hierarchy

### Effective Attribute Resolution

For any family, the effective (resolved) attribute set is computed by walking the ancestor chain:

1. Collect ancestor chain: `[root, ..., parent, self]`
2. Start with root family's own bindings
3. For each descendant in chain:
   - Add own bindings (new attributes)
   - Override: if child has binding for same `attribute_id` as ancestor → child replaces parent (overrides `requirement_level`, `sort_order`, `flag_overrides`, `filter_settings`)
   - Exclude: remove any attributes listed in child's exclusions
4. Result = effective attribute set

---

## Domain Entities

> **Implementation note:** All entities use `from attr import dataclass, field` (the `attrs` library), NOT `from dataclasses import dataclass`. This is load-bearing — `AggregateRoot` depends on `__attrs_post_init__` hooks for domain event initialization.

### AttributeFamily (Aggregate Root)

```python
from attr import dataclass, field

@dataclass
class AttributeFamily(AggregateRoot):
    id: uuid.UUID
    parent_id: uuid.UUID | None        # null = root family, IMMUTABLE after creation
    code: str                           # unique, immutable, ^[a-z0-9_]+$
    name_i18n: dict[str, str]           # at least 1 language
    description_i18n: dict[str, str]    # optional
    sort_order: int                     # display ordering among siblings
    level: int                          # depth in tree (0 = root), derived from parent
```

**Factory methods:**

- `create_root(code, name_i18n, ...)` → root family (level=0, parent_id=None)
- `create_child(parent, code, name_i18n, ...)` → child family (level=parent.level+1)

**Constraints:**

- `code` is unique globally and immutable after creation (enforced via `__setattr__` guard like `Category`)
- `parent_id` is immutable after creation (enforced via `__setattr__` guard)
- `level` is immutable after creation (derived from parent at creation time)
- Unlimited nesting depth (no MAX_DEPTH constant)
- Cannot delete a family that has children or is referenced by categories

**Updatable fields** (via `_UPDATABLE_FIELDS`):

- `name_i18n`, `description_i18n`, `sort_order`

**Guarded (immutable) fields** (via `_GUARDED_FIELDS`):

- `code`, `parent_id`, `level`

### FamilyAttributeBinding (Standalone Aggregate Root)

> **Design decision:** `FamilyAttributeBinding` is a standalone aggregate (not a child entity of `AttributeFamily`), matching the pattern established by `CategoryAttributeBinding` in the existing codebase. It has its own repository, emits its own domain events, and is registered with UnitOfWork independently.

```python
from attr import dataclass

@dataclass
class FamilyAttributeBinding(AggregateRoot):
    id: uuid.UUID
    family_id: uuid.UUID
    attribute_id: uuid.UUID
    sort_order: int
    requirement_level: RequirementLevel   # REQUIRED | RECOMMENDED | OPTIONAL
    flag_overrides: dict[str, Any] | None
    filter_settings: dict[str, Any] | None
```

**Constraints:**

- Unique pair `(family_id, attribute_id)` — one binding per attribute per family
- Mutable fields: `sort_order`, `requirement_level`, `flag_overrides`, `filter_settings`
- Immutable fields: `family_id`, `attribute_id`

### FamilyAttributeExclusion (Standalone Aggregate Root)

> **Design decision:** Standalone aggregate for the same reasons as `FamilyAttributeBinding`.

```python
from attr import dataclass

@dataclass
class FamilyAttributeExclusion(AggregateRoot):
    id: uuid.UUID
    family_id: uuid.UUID
    attribute_id: uuid.UUID    # inherited attribute to exclude
```

**Constraints:**

- Unique pair `(family_id, attribute_id)`
- Can only exclude attributes that are **inherited from ancestors** (present in ancestor's effective set)
- **Cannot exclude an attribute that the same family has in its own bindings** — raises `FamilyExclusionConflictsWithOwnBindingError`
- If `attribute_id` is not in any ancestor's effective set → raises `AttributeNotInheritedError`

### Category (Modified)

```python
# Added field:
family_id: uuid.UUID | None    # FK to AttributeFamily, nullable
```

Added to `_UPDATABLE_FIELDS` so it can be changed via `update()`.

---

## Database Schema

### New Tables

```sql
CREATE TABLE attribute_families (
    id UUID PRIMARY KEY,
    parent_id UUID REFERENCES attribute_families(id) ON DELETE RESTRICT,
    code VARCHAR(100) NOT NULL,
    name_i18n JSONB NOT NULL DEFAULT '{}'::jsonb,
    description_i18n JSONB NOT NULL DEFAULT '{}'::jsonb,
    sort_order INTEGER NOT NULL DEFAULT 0,
    level INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uix_attribute_families_code UNIQUE (code)
);

CREATE INDEX ix_attribute_families_parent ON attribute_families(parent_id);
CREATE INDEX ix_attribute_families_level_sort ON attribute_families(level, sort_order);

CREATE TABLE family_attribute_bindings (
    id UUID PRIMARY KEY,
    family_id UUID NOT NULL REFERENCES attribute_families(id) ON DELETE CASCADE,
    attribute_id UUID NOT NULL REFERENCES attributes(id) ON DELETE CASCADE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    requirement_level requirement_level_enum NOT NULL DEFAULT 'optional',
    flag_overrides JSONB,
    filter_settings JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uix_family_attr_binding UNIQUE (family_id, attribute_id)
);

CREATE INDEX ix_family_attr_bindings_family ON family_attribute_bindings(family_id);
CREATE INDEX ix_family_attr_bindings_attr ON family_attribute_bindings(attribute_id);

CREATE TABLE family_attribute_exclusions (
    id UUID PRIMARY KEY,
    family_id UUID NOT NULL REFERENCES attribute_families(id) ON DELETE CASCADE,
    attribute_id UUID NOT NULL REFERENCES attributes(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uix_family_attr_exclusion UNIQUE (family_id, attribute_id)
);

CREATE INDEX ix_family_attr_exclusions_family ON family_attribute_exclusions(family_id);
```

### Modified Tables

```sql
-- categories: add family_id
ALTER TABLE categories ADD COLUMN family_id UUID REFERENCES attribute_families(id) ON DELETE SET NULL;
CREATE INDEX ix_categories_family ON categories(family_id);
```

### Dropped Tables

```sql
DROP TABLE category_attribute_rules;
```

---

## Effective Attribute Resolution Algorithm

```python
async def resolve_effective_attributes(
    family_id: UUID,
) -> list[EffectiveAttribute]:
    """
    Walk ancestor chain from root to target family.
    Build merged attribute set with overrides and exclusions.
    """
    # 1. Load ancestor chain via recursive CTE (see repository section)
    chain: list[AttributeFamily] = await family_repo.get_ancestor_chain(family_id)
    # chain = [root, ..., grandparent, parent, self]

    # 2. Load all bindings and exclusions for all families in chain
    family_ids = [f.id for f in chain]
    all_bindings: dict[UUID, list[FamilyAttributeBinding]] = (
        await binding_repo.get_bindings_for_families(family_ids)
    )
    all_exclusions: dict[UUID, set[UUID]] = (
        await exclusion_repo.get_exclusions_for_families(family_ids)
    )

    # 3. Merge: iterate chain root → leaf
    effective: dict[UUID, EffectiveAttribute] = {}  # keyed by attribute_id

    for family in chain:
        # Apply exclusions first — remove inherited attrs
        for excluded_attr_id in all_exclusions.get(family.id, set()):
            effective.pop(excluded_attr_id, None)

        # Apply own bindings — add or override
        for binding in all_bindings.get(family.id, []):
            effective[binding.attribute_id] = EffectiveAttribute(
                attribute_id=binding.attribute_id,
                sort_order=binding.sort_order,
                requirement_level=binding.requirement_level,
                flag_overrides=binding.flag_overrides,
                filter_settings=binding.filter_settings,
                source_family_id=family.id,  # track origin
            )

    return sorted(effective.values(), key=lambda a: a.sort_order)
```

**Caching:** Effective attribute sets are cached in Redis per `family_id`. Cache invalidated when any family in the ancestor chain changes its bindings or exclusions. See Cache Strategy section for descendant enumeration.

---

## API Endpoints

### AttributeFamily CRUD

| Method | Path                               | Auth             | Description                  |
| ------ | ---------------------------------- | ---------------- | ---------------------------- |
| POST   | `/catalog/attribute-families`      | `catalog:manage` | Create family                |
| GET    | `/catalog/attribute-families`      | `catalog:read`   | List (paginated)             |
| GET    | `/catalog/attribute-families/tree` | `catalog:read`   | Full hierarchy               |
| GET    | `/catalog/attribute-families/{id}` | `catalog:read`   | Get by ID                    |
| PATCH  | `/catalog/attribute-families/{id}` | `catalog:manage` | Update                       |
| DELETE | `/catalog/attribute-families/{id}` | `catalog:manage` | Delete (if no children/refs) |

### Family Attribute Bindings

| Method | Path                                                      | Auth             | Description    |
| ------ | --------------------------------------------------------- | ---------------- | -------------- |
| POST   | `/catalog/attribute-families/{id}/attributes`             | `catalog:manage` | Bind attribute |
| GET    | `/catalog/attribute-families/{id}/attributes`             | `catalog:read`   | Own bindings   |
| GET    | `/catalog/attribute-families/{id}/attributes/effective`   | `catalog:read`   | Resolved set   |
| PATCH  | `/catalog/attribute-families/{id}/attributes/{bindingId}` | `catalog:manage` | Update binding |
| DELETE | `/catalog/attribute-families/{id}/attributes/{bindingId}` | `catalog:manage` | Unbind         |
| POST   | `/catalog/attribute-families/{id}/attributes/reorder`     | `catalog:manage` | Reorder        |

### Family Attribute Exclusions

| Method | Path                                                        | Auth             | Description            |
| ------ | ----------------------------------------------------------- | ---------------- | ---------------------- |
| POST   | `/catalog/attribute-families/{id}/exclusions`               | `catalog:manage` | Exclude inherited attr |
| GET    | `/catalog/attribute-families/{id}/exclusions`               | `catalog:read`   | List exclusions        |
| DELETE | `/catalog/attribute-families/{id}/exclusions/{exclusionId}` | `catalog:manage` | Remove exclusion       |

### Storefront (rewritten internals, same URLs)

| Method | Path                                                        | Auth             | Description           |
| ------ | ----------------------------------------------------------- | ---------------- | --------------------- |
| GET    | `/catalog/storefront/categories/{id}/form-attributes`       | `catalog:manage` | Full attribute form   |
| GET    | `/catalog/storefront/categories/{id}/filters`               | public           | Filterable attributes |
| GET    | `/catalog/storefront/categories/{id}/card-attributes`       | public           | Card display attrs    |
| GET    | `/catalog/storefront/categories/{id}/comparison-attributes` | public           | Comparison attrs      |

Storefront handlers now: `category → family_id → resolve effective → filter/group`.

---

## Request/Response Schemas

### Create Family

```json
// POST /catalog/attribute-families
{
  "code": "t_shirts",
  "parentId": "uuid-of-clothing-family | null",
  "nameI18n": { "en": "T-shirts", "ru": "Футболки" },
  "descriptionI18n": { "en": "..." },
  "sortOrder": 0
}
// Response 201: { "id": "uuid" }
```

### Bind Attribute to Family

```json
// POST /catalog/attribute-families/{id}/attributes
{
  "attributeId": "uuid",
  "sortOrder": 0,
  "requirementLevel": "required",
  "flagOverrides": { "isFilterable": true },
  "filterSettings": null
}
// Response 201: { "id": "uuid" }
```

### Exclude Inherited Attribute

```json
// POST /catalog/attribute-families/{id}/exclusions
{
  "attributeId": "uuid"
}
// Response 201: { "id": "uuid" }
```

### Effective Attributes Response

```json
// GET /catalog/attribute-families/{id}/attributes/effective
{
  "familyId": "uuid",
  "attributes": [
    {
      "attributeId": "uuid",
      "code": "size",
      "slug": "size",
      "nameI18n": { "en": "Size" },
      "descriptionI18n": {},
      "dataType": "string",
      "uiType": "text_button",
      "isDictionary": true,
      "level": "variant",
      "requirementLevel": "required",
      "validationRules": null,
      "flagOverrides": null,
      "filterSettings": null,
      "sourceFamilyId": "uuid-of-parent-family",
      "isOverridden": false,
      "values": [
        {
          "id": "uuid",
          "code": "s",
          "slug": "s",
          "valueI18n": { "en": "S" },
          "metaData": {},
          "valueGroup": null,
          "sortOrder": 0
        }
      ],
      "sortOrder": 0
    }
  ]
}
```

---

## Domain Events

All events follow the existing `CatalogEvent` base class protocol with `__init_subclass__` keyword arguments.

> **Important:** Events use `from dataclasses import dataclass` (stdlib), NOT `from attr import dataclass`. This is because `DomainEvent` is a non-frozen stdlib dataclass, and Python prohibits mixing `attrs` subclasses with stdlib dataclass parents. Domain entities use `attrs`; domain events use stdlib `dataclasses`.

```python
from dataclasses import dataclass

# --- AttributeFamily lifecycle ---

@dataclass
class AttributeFamilyCreatedEvent(
    CatalogEvent,
    required_fields=("family_id",),
    aggregate_id_field="family_id",
):
    family_id: uuid.UUID | None = None
    code: str = ""
    parent_id: uuid.UUID | None = None
    aggregate_type: str = "AttributeFamily"
    event_type: str = "AttributeFamilyCreatedEvent"

@dataclass
class AttributeFamilyUpdatedEvent(
    CatalogEvent,
    required_fields=("family_id",),
    aggregate_id_field="family_id",
):
    family_id: uuid.UUID | None = None
    aggregate_type: str = "AttributeFamily"
    event_type: str = "AttributeFamilyUpdatedEvent"

@dataclass
class AttributeFamilyDeletedEvent(
    CatalogEvent,
    required_fields=("family_id",),
    aggregate_id_field="family_id",
):
    family_id: uuid.UUID | None = None
    code: str = ""
    aggregate_type: str = "AttributeFamily"
    event_type: str = "AttributeFamilyDeletedEvent"

# --- FamilyAttributeBinding lifecycle ---

@dataclass
class FamilyAttributeBindingCreatedEvent(
    CatalogEvent,
    required_fields=("binding_id",),
    aggregate_id_field="binding_id",
):
    family_id: uuid.UUID | None = None
    attribute_id: uuid.UUID | None = None
    binding_id: uuid.UUID | None = None
    aggregate_type: str = "FamilyAttributeBinding"
    event_type: str = "FamilyAttributeBindingCreatedEvent"

@dataclass
class FamilyAttributeBindingUpdatedEvent(
    CatalogEvent,
    required_fields=("binding_id",),
    aggregate_id_field="binding_id",
):
    binding_id: uuid.UUID | None = None
    aggregate_type: str = "FamilyAttributeBinding"
    event_type: str = "FamilyAttributeBindingUpdatedEvent"

@dataclass
class FamilyAttributeBindingDeletedEvent(
    CatalogEvent,
    required_fields=("binding_id",),
    aggregate_id_field="binding_id",
):
    family_id: uuid.UUID | None = None
    attribute_id: uuid.UUID | None = None
    binding_id: uuid.UUID | None = None
    aggregate_type: str = "FamilyAttributeBinding"
    event_type: str = "FamilyAttributeBindingDeletedEvent"

# --- FamilyAttributeExclusion lifecycle ---

@dataclass
class FamilyAttributeExclusionAddedEvent(
    CatalogEvent,
    required_fields=("exclusion_id",),
    aggregate_id_field="exclusion_id",
):
    family_id: uuid.UUID | None = None
    attribute_id: uuid.UUID | None = None
    exclusion_id: uuid.UUID | None = None
    aggregate_type: str = "FamilyAttributeExclusion"
    event_type: str = "FamilyAttributeExclusionAddedEvent"

@dataclass
class FamilyAttributeExclusionRemovedEvent(
    CatalogEvent,
    required_fields=("exclusion_id",),
    aggregate_id_field="exclusion_id",
):
    family_id: uuid.UUID | None = None
    attribute_id: uuid.UUID | None = None
    exclusion_id: uuid.UUID | None = None
    aggregate_type: str = "FamilyAttributeExclusion"
    event_type: str = "FamilyAttributeExclusionRemovedEvent"
```

---

## Cache Strategy

- **Key pattern:** `family:{family_id}:effective_attrs`
- **TTL:** Same as `STOREFRONT_CACHE_TTL`
- **Descendant enumeration:** `IAttributeFamilyRepository.get_descendant_ids(family_id) -> list[UUID]` using a `WITH RECURSIVE` CTE on `attribute_families.parent_id`. Used for cache cascade invalidation.
- **Invalidation on binding/exclusion change:** When a family's bindings or exclusions change, call `get_descendant_ids(family_id)` and invalidate `family:{id}:effective_attrs` for the family itself AND all its descendants.
- **Invalidation on category family_id change:** When a category's `family_id` is updated, invalidate all storefront cache keys (`storefront:cat:{cat_id}:*`) for that category.
- **Storefront keys** (`storefront:cat:{cat_id}:*`) are also invalidated when the linked family's effective set changes (triggered by family binding/exclusion cache invalidation).

### Repository method for descendant enumeration

```python
class IAttributeFamilyRepository:
    @abstractmethod
    async def get_descendant_ids(self, family_id: uuid.UUID) -> list[uuid.UUID]:
        """Return all descendant family IDs using WITH RECURSIVE CTE."""
        pass

    @abstractmethod
    async def get_ancestor_chain(self, family_id: uuid.UUID) -> list[AttributeFamily]:
        """Return ancestor chain [root, ..., parent, self] using WITH RECURSIVE CTE."""
        pass
```

### SQL for descendant enumeration

```sql
WITH RECURSIVE descendants AS (
    SELECT id FROM attribute_families WHERE id = :family_id
    UNION ALL
    SELECT af.id FROM attribute_families af
    JOIN descendants d ON af.parent_id = d.id
)
SELECT id FROM descendants WHERE id != :family_id;
```

### SQL for ancestor chain

```sql
WITH RECURSIVE ancestors AS (
    SELECT id, parent_id, level FROM attribute_families WHERE id = :family_id
    UNION ALL
    SELECT af.id, af.parent_id, af.level FROM attribute_families af
    JOIN ancestors a ON a.parent_id = af.id
)
SELECT * FROM ancestors ORDER BY level ASC;
```

---

## Exception Classes

### New exceptions (add to `domain/exceptions.py`)

```python
# AttributeFamily
class AttributeFamilyNotFoundError(NotFoundError): ...
class AttributeFamilyCodeAlreadyExistsError(ConflictError): ...
class AttributeFamilyHasChildrenError(ConflictError): ...
class AttributeFamilyHasCategoryReferencesError(ConflictError): ...
class AttributeFamilyParentImmutableError(ValidationError): ...

# FamilyAttributeBinding
class FamilyAttributeBindingNotFoundError(NotFoundError): ...
class FamilyAttributeBindingAlreadyExistsError(ConflictError): ...

# FamilyAttributeExclusion
class FamilyAttributeExclusionNotFoundError(NotFoundError): ...
class AttributeNotInheritedError(ValidationError): ...
    """Raised when trying to exclude an attribute not present in ancestor's effective set."""
class FamilyExclusionConflictsWithOwnBindingError(ConflictError): ...
    """Raised when trying to exclude an attribute that has a direct binding on the same family."""
```

### Modified exceptions

```python
# REPLACE AttributeHasCategoryBindingsError with:
class AttributeHasFamilyBindingsError(ConflictError):
    """Raised when attempting to delete an attribute bound to families."""
```

The attribute delete handler must be updated to check `family_attribute_bindings` instead of `category_attribute_rules`.

---

## Files to DELETE

| File                                                                                                                                                                                                           | Reason                                                                         |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `domain/entities.py` → `CategoryAttributeBinding` class                                                                                                                                                        | Replaced by `FamilyAttributeBinding`                                           |
| `domain/interfaces.py` → `ICategoryAttributeBindingRepository`                                                                                                                                                 | Replaced by `IAttributeFamilyRepository` + `IFamilyAttributeBindingRepository` |
| `domain/events.py` → `CategoryAttributeBindingCreatedEvent`, `CategoryAttributeBindingUpdatedEvent`, `CategoryAttributeBindingDeletedEvent`, `CategoryBindingsReorderedEvent`, `RequirementLevelsUpdatedEvent` | Replaced by new Family events                                                  |
| `domain/exceptions.py` → `AttributeHasCategoryBindingsError`                                                                                                                                                   | Replaced by `AttributeHasFamilyBindingsError`                                  |
| `infrastructure/models.py` → `CategoryAttributeBinding` ORM                                                                                                                                                    | Replaced                                                                       |
| `infrastructure/repositories/category_attribute_binding.py`                                                                                                                                                    | Replaced                                                                       |
| `application/commands/bind_attribute_to_category.py`                                                                                                                                                           | Replaced                                                                       |
| `application/commands/unbind_attribute_from_category.py`                                                                                                                                                       | Replaced                                                                       |
| `application/commands/update_category_attribute_binding.py`                                                                                                                                                    | Replaced                                                                       |
| `application/commands/reorder_category_bindings.py`                                                                                                                                                            | Replaced                                                                       |
| `application/commands/bulk_update_requirement_levels.py`                                                                                                                                                       | Replaced                                                                       |
| `presentation/router_category_bindings.py`                                                                                                                                                                     | Replaced                                                                       |
| `presentation/schemas.py` → `BindAttributeToCategoryRequest`, `CategoryAttributeBindingResponse`, etc.                                                                                                         | Replaced                                                                       |
| Migration: drop table `category_attribute_rules`                                                                                                                                                               | In new migration                                                               |

## Files to CREATE

| File                                                                                                                              | Content                                                      |
| --------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| `domain/entities.py` → `AttributeFamily`, `FamilyAttributeBinding`, `FamilyAttributeExclusion`                                    | New aggregate roots (using `from attr import dataclass`)     |
| `domain/interfaces.py` → `IAttributeFamilyRepository`, `IFamilyAttributeBindingRepository`, `IFamilyAttributeExclusionRepository` | Repository contracts with CTE methods                        |
| `domain/events.py` → 8 new events (see Domain Events section)                                                                     | Full `CatalogEvent` subclasses                               |
| `domain/exceptions.py` → 8 new exception classes + `AttributeHasFamilyBindingsError`                                              | See Exception Classes section                                |
| `infrastructure/models.py` → `AttributeFamily`, `FamilyAttributeBinding`, `FamilyAttributeExclusion` ORM                          | ORM models                                                   |
| `infrastructure/repositories/attribute_family.py`                                                                                 | Repository with CTE queries                                  |
| `infrastructure/repositories/family_attribute_binding.py`                                                                         | Binding repository                                           |
| `infrastructure/repositories/family_attribute_exclusion.py`                                                                       | Exclusion repository                                         |
| `application/commands/create_attribute_family.py`                                                                                 | Handler (validates no cycle at creation)                     |
| `application/commands/update_attribute_family.py`                                                                                 | Handler (only `name_i18n`, `description_i18n`, `sort_order`) |
| `application/commands/delete_attribute_family.py`                                                                                 | Handler (checks children + category refs)                    |
| `application/commands/bind_attribute_to_family.py`                                                                                | Handler                                                      |
| `application/commands/unbind_attribute_from_family.py`                                                                            | Handler                                                      |
| `application/commands/update_family_attribute_binding.py`                                                                         | Handler                                                      |
| `application/commands/reorder_family_bindings.py`                                                                                 | Handler                                                      |
| `application/commands/add_family_exclusion.py`                                                                                    | Handler (validates inherited + no own binding conflict)      |
| `application/commands/remove_family_exclusion.py`                                                                                 | Handler                                                      |
| `application/queries/resolve_family_attributes.py`                                                                                | Effective resolution with caching                            |
| `application/queries/list_attribute_families.py`                                                                                  | List/tree queries                                            |
| `presentation/router_attribute_families.py`                                                                                       | REST endpoints                                               |
| `presentation/schemas.py` → new schemas                                                                                           | Request/Response                                             |
| Alembic migration                                                                                                                 | DDL changes                                                  |

## Files to MODIFY

| File                                                                         | Change                                                                  |
| ---------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| `domain/entities.py` → `Category`                                            | Add `family_id: uuid.UUID \| None` to entity + `_UPDATABLE_FIELDS`      |
| `infrastructure/models.py` → `Category` ORM                                  | Add `family_id` column + FK + relationship + index                      |
| `application/queries/storefront.py`                                          | Resolve through family instead of direct bindings                       |
| `application/commands/create_category.py`                                    | Accept optional `family_id`                                             |
| `application/commands/update_category.py`                                    | Accept optional `family_id`, invalidate storefront cache on change      |
| `application/commands/delete_attribute.py`                                   | Check `family_attribute_bindings` instead of `category_attribute_rules` |
| `presentation/schemas.py` → `CategoryCreateRequest`, `CategoryUpdateRequest` | Add `familyId` field                                                    |
| `presentation/router_products.py` → imports                                  | Remove old binding references if any                                    |
| DI Provider                                                                  | Register new repositories + handlers                                    |

---

## Validation Rules

1. **Family code:** `^[a-z0-9_]+$`, unique globally, immutable after creation
2. **Cannot delete family** with children or category references
3. **Exclusion validation:** Can only exclude attributes present in ancestor's effective set AND not in own bindings
4. **Binding uniqueness:** One binding per `(family_id, attribute_id)` pair
5. **No circular references:** `parent_id` chain cannot form a cycle. Since `parent_id` is immutable after creation and set only at creation time, the `create_attribute_family` handler validates the proposed `parent_id` exists and is not the family itself. No `FamilyCircularReferenceError` needed — cycles are structurally impossible because a family can only reference an already-existing parent.
6. **Family tree integrity:** `parent_id` and `level` are immutable after creation — enforced by `__setattr__` guard on the entity
7. **Update scope:** `UpdateAttributeFamilyCommand` accepts only `name_i18n`, `description_i18n`, `sort_order`. Fields `parent_id`, `level`, `code` are explicitly excluded.
8. **Attribute deletion guard:** Deleting an attribute checks `family_attribute_bindings` (replaces old `category_attribute_rules` check). Raises `AttributeHasFamilyBindingsError`.
