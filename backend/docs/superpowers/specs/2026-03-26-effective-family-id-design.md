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

1. Set own `effective_family_id`
2. Recursive CTE UPDATE: propagate to descendants where `family_id IS NULL`
3. Invalidate Redis L1 + L2 caches for affected categories

### Changes

#### 1. Domain Entity (`domain/entities.py`)

Add `effective_family_id: uuid.UUID | None = None` field to `Category`. Include in `_UPDATABLE_FIELDS`. Add to `create_root` and `create_child` factory methods (computed from parent or self).

#### 2. ORM Model (`infrastructure/models.py`)

```python
effective_family_id: Mapped[uuid.UUID | None] = mapped_column(
    ForeignKey("attribute_families.id", ondelete="SET NULL"),
    index=True,
)
```

#### 3. Repository: Cascade Propagation (`ICategoryRepository` + implementation)

New interface method:

```python
@abstractmethod
async def propagate_effective_family_id(
    self, category_id: uuid.UUID, effective_family_id: uuid.UUID | None
) -> list[uuid.UUID]:
    """Propagate effective_family_id to inheriting descendants.
    Returns all affected category IDs for cache invalidation."""
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

**`create_category`**: Set `effective_family_id` = own `family_id` or parent's `effective_family_id`.

**`update_category`**: When `family_id` changes:
1. Set own `effective_family_id` = new `family_id` or parent's `effective_family_id`
2. Call `propagate_effective_family_id()` for descendants
3. Invalidate storefront Redis caches for all affected category IDs

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

#### 6. Seed Script (`sync_attributes.py`)

After assigning family to root category, propagate to children:

```sql
UPDATE categories
SET effective_family_id = :family_id
WHERE effective_family_id IS NULL
  AND (id = :cat_id OR full_slug LIKE :root_slug || '/%')
```

#### 7. Alembic Migration

- Add `effective_family_id` column (nullable, FK, indexed)
- Data migration: backfill from parent chain for existing categories

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
| PM sets `family_id` on category | Propagate effective → invalidate L2 for affected categories |
| PM changes binding/exclusion on family | Invalidate L1 for family + descendants → L2 for all categories with that effective_family_id (already implemented) |
| PM changes attribute metadata | Invalidate L1 for families binding that attribute → L2 for related categories |
| Parser creates/updates product | No Redis invalidation (schema unchanged) |

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
| `src/modules/catalog/domain/entities.py` | Add `effective_family_id` field to Category |
| `src/modules/catalog/infrastructure/models.py` | Add column + index |
| `src/modules/catalog/domain/interfaces.py` | Add `propagate_effective_family_id` to ICategoryRepository |
| `src/modules/catalog/infrastructure/repositories/category.py` | Implement propagation with recursive CTE |
| `src/modules/catalog/application/commands/create_category.py` | Compute effective_family_id |
| `src/modules/catalog/application/commands/update_category.py` | Propagate on family_id change + cache invalidation |
| `src/modules/catalog/application/queries/storefront.py` | `family_id` → `effective_family_id` (1 line) |
| `src/modules/catalog/management/sync_attributes.py` | Propagate after seed |
| `alembic/versions/2026/03/...` | Migration: add column + backfill |
| `tests/` | Unit + integration tests for propagation |

### Non-Goals

- Elasticsearch integration (separate feature)
- Storefront aggregation counts (ES responsibility)
- Multi-family inheritance (one category = one effective family)
- TTL-based cache expiration (keep current invalidation-based approach)
