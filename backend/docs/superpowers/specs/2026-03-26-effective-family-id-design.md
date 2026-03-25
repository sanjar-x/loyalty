# Effective Family ID: Write-Time Denormalization for Category Attribute Inheritance

**Date:** 2026-03-26
**Status:** Approved
**Module:** Catalog (src/modules/catalog)

## Problem

Child categories (e.g. "Футболки", "Худи") do not inherit `family_id` from their parent ("Одежда"). The storefront resolver (`_resolve_effective_for_category`) returns an empty attribute set for any category with `family_id IS NULL`:

```python
if cat.family_id is None:
    return []  # child categories always hit this
```

At scale (millions of storefront read requests vs. rare writes by PMs/parsers), runtime tree traversal is wasteful — every read would pay for a parent lookup that yields the same answer until the next write.

## Prerequisites

**Repository mapper bug:** The category repository (`infrastructure/repositories/category.py`) currently does NOT map `family_id` in `_to_domain()` or `_to_orm()`. Both methods omit the field entirely. The storefront resolver only works today because it reads from the ORM model directly via `session.get()`, bypassing the repository. This must be fixed as part of this change — both `family_id` and `effective_family_id` must be added to `_to_domain()` and `_to_orm()`.

## Design

### Approach: Write-Time Denormalization

Add a computed column `effective_family_id` to `categories`. It holds the resolved family — either the category's own `family_id` or the nearest ancestor's. Updated on every write that changes the family assignment.

**Why two columns:**

| Column | Purpose | Set by |
|---|---|---|
| `family_id` | Explicitly assigned family (source of truth) | PM / admin |
| `effective_family_id` | Computed: own or inherited from parent | Propagation logic |

A child with `family_id = NULL` inherits; a child with its own `family_id` overrides.

### Read Path (hot, millions RPS)

```
GET /storefront/categories/{id}/filters
  → Redis GET catalog:storefront:filters:{category_id}
  → HIT (99.9%): return JSON
  → MISS: read effective_family_id → resolve family attrs → cache → return
```

One Redis GET. No SQL. No tree traversal.

### Write Path (rare, tens/day)

When `family_id` changes on a category:

1. Compute own `effective_family_id` = new `family_id` ?? parent's `effective_family_id`
2. Recursive CTE UPDATE: propagate to descendants where `family_id IS NULL`
3. Invalidate Redis L2 caches for all affected categories

### Changes

#### 1. Domain Entity (`domain/entities.py`)

Add `effective_family_id: uuid.UUID | None = None` field to `Category`.

**Factory methods compute it automatically:**
- `create_root(family_id=X)`: `effective_family_id = family_id` (root has no parent)
- `create_child(family_id=X, parent=P)`: `effective_family_id = family_id or parent.effective_family_id`

**`effective_family_id` is a derived field — NOT in `_UPDATABLE_FIELDS`.** It is set only:
- At construction (factory methods)
- By dedicated domain method `set_effective_family_id()` for propagation
- Never through the general `update(**kwargs)` API

#### 2. ORM Model (`infrastructure/models.py`)

```python
effective_family_id: Mapped[uuid.UUID | None] = mapped_column(
    ForeignKey("attribute_families.id", ondelete="SET NULL"),
    index=True,
)
```

#### 3. Repository Data Mapper Fix + Propagation

**Fix `_to_domain` and `_to_orm`** to include both `family_id` and `effective_family_id`.

**New interface method on `ICategoryRepository`:**

```python
@abstractmethod
async def propagate_effective_family_id(
    self, category_id: uuid.UUID, effective_family_id: uuid.UUID | None
) -> list[uuid.UUID]:
    """Propagate effective_family_id to inheriting descendants.

    Only updates children (and their descendants) where family_id IS NULL,
    meaning they inherit from their parent rather than having their own.
    Stops at nodes that have their own family_id (they are propagation roots
    for their own subtrees).

    Returns all affected category IDs (excluding the root itself) for cache invalidation.
    """
```

Implementation uses a single recursive CTE:

```sql
WITH RECURSIVE subtree AS (
    SELECT id FROM categories
    WHERE parent_id = :root_id AND family_id IS NULL
    UNION ALL
    SELECT c.id FROM categories c
    JOIN subtree s ON c.parent_id = s.id
    WHERE c.family_id IS NULL
)
UPDATE categories SET effective_family_id = :eff_fid
WHERE id IN (SELECT id FROM subtree)
RETURNING id
```

Single SQL round-trip. `MAX_CATEGORY_DEPTH = 3` means max 2 recursion levels.

#### 4. Command Handlers

**`create_category`:**
- Root: `effective_family_id = family_id`
- Child: `effective_family_id = family_id or parent.effective_family_id`
- Parent entity is already loaded in the handler (line 125), so `parent.effective_family_id` is available at zero cost.

**`update_category`** — three scenarios when `family_id` changes:

**Scenario A: Set family_id (NULL → X)**
```
effective_family_id = X
propagate X to inheriting descendants
```

**Scenario B: Change family_id (X → Y)**
```
effective_family_id = Y
propagate Y to inheriting descendants
```

**Scenario C: Clear family_id (X → NULL)**
```
# Must look up parent's effective_family_id to re-inherit
if parent_id is not None:
    parent = await category_repo.get(parent_id)
    effective_family_id = parent.effective_family_id
else:
    effective_family_id = None  # root with no family
propagate effective_family_id to inheriting descendants
```

After propagation: invalidate storefront L2 caches for all affected category IDs (root + returned descendants).

**`delete_category`**: No change needed (children already protected by `validate_deletable`).

#### 5. Storefront Resolver (`storefront.py`)

One-line change:

```python
# Before
if cat.family_id is None:
    return []

# After
if cat.effective_family_id is None:
    return []
result = await resolver.handle(cat.effective_family_id)
```

#### 6. Cache Invalidation for `get_category_ids_by_family_ids`

`IAttributeFamilyRepository.get_category_ids_by_family_ids()` must query against `effective_family_id` (not just `family_id`) so that when a family's bindings change, cache invalidation covers ALL categories that inherited the family — not just those with an explicit assignment.

#### 7. Seed Script (`sync_attributes.py`)

After assigning family to root category "clothing", propagate to all children using `full_slug LIKE` (safe because slugs are validated to lowercase alphanumeric + hyphens, no LIKE metacharacters):

```sql
UPDATE categories
SET effective_family_id = :family_id
WHERE (slug = :slug AND parent_id IS NULL)
   OR full_slug LIKE :root_slug || '/%'
```

This sets `effective_family_id` on both the root "clothing" and all its children (tees, hoodies, jeans, etc.) in one statement.

#### 8. Alembic Migration

- Add `effective_family_id` column (nullable, FK to `attribute_families.id`, indexed, `SET NULL` on delete)
- Data migration: backfill existing categories — copy `family_id` to `effective_family_id` for roots, propagate down the tree for children

### Two-Tier Redis Cache (existing, unchanged)

```
L1: catalog:family:{family_id}:effective_attrs     — shared across categories
L2: catalog:storefront:{view}:{category_id}        — per category per view
    TTL: 0 (invalidation-based, already implemented)
```

L1 is shared: 50 categories with the same effective family → 1 L1 entry.
L2 is per-category: filters/card/comparison/form projections.

### Cache Invalidation Matrix

| Event | Redis action |
|---|---|
| PM sets/changes/clears `family_id` on category | Propagate effective → batch-invalidate L2 for affected categories |
| PM changes binding/exclusion on family | Invalidate L1 for family + descendants → L2 for all categories with that `effective_family_id` (already implemented, needs query fix per Section 6) |
| PM changes attribute metadata | Invalidate L1 for families binding that attribute → L2 for related categories |
| Parser creates/updates product | No Redis invalidation (schema unchanged) |

**Cache invalidation reliability:** All L2 keys for affected categories are collected into a single `delete_many()` call within one try/except block. If it fails, the warning is logged — subsequent requests will rebuild from DB on cache miss. This matches the existing pattern in the codebase.

### Elasticsearch Integration (future)

This change lays the foundation for ES:

- Product ES document includes `effective_family_id` from its category
- `effective_family_id` determines which attribute fields exist in the ES mapping
- Redis serves the filter schema (names, UI types, sort order)
- ES serves the data (product hits + aggregation counts per filter value)

ES integration is out of scope for this change.

### Files to Modify

| File | Change |
|---|---|
| `src/modules/catalog/domain/entities.py` | Add `effective_family_id` field + `set_effective_family_id()` method to Category |
| `src/modules/catalog/infrastructure/models.py` | Add `effective_family_id` column + index |
| `src/modules/catalog/domain/interfaces.py` | Add `propagate_effective_family_id` to ICategoryRepository |
| `src/modules/catalog/infrastructure/repositories/category.py` | Fix `_to_domain`/`_to_orm` for `family_id` + `effective_family_id`; implement propagation CTE |
| `src/modules/catalog/infrastructure/repositories/attribute_family.py` | Fix `get_category_ids_by_family_ids` to query `effective_family_id` |
| `src/modules/catalog/application/commands/create_category.py` | Compute `effective_family_id` from parent |
| `src/modules/catalog/application/commands/update_category.py` | Propagate on `family_id` change (3 scenarios) + batch cache invalidation |
| `src/modules/catalog/application/queries/storefront.py` | `family_id` → `effective_family_id` (1 line) |
| `src/modules/catalog/management/sync_attributes.py` | Propagate `effective_family_id` after seed |
| `alembic/versions/2026/03/...` | Migration: add column + backfill |
| `tests/` | Unit + integration tests for propagation |

### Non-Goals

- Elasticsearch integration (separate feature)
- Storefront aggregation counts (ES responsibility)
- Multi-family inheritance (one category = one effective family)
- TTL-based cache expiration (keep current invalidation-based approach)
