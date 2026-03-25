# Effective Family ID Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Child categories inherit `effective_family_id` from their parent at write time so the storefront read path requires zero tree traversal.

**Architecture:** Add a denormalized `effective_family_id` column to categories. Propagate via recursive CTE on every write that changes `family_id`. Fix the existing repo mapper bug that omits `family_id` from `_to_domain`/`_to_orm`.

**Tech Stack:** SQLAlchemy 2.1 async, PostgreSQL recursive CTE, Alembic, attrs domain entities, pytest-asyncio

**Spec:** `docs/superpowers/specs/2026-03-26-effective-family-id-design.md`

---

### Task 1: Domain Entity — Add `effective_family_id` to Category

**Files:**
- Modify: `src/modules/catalog/domain/entities.py:247-405` (Category class)

- [ ] **Step 1: Add field and update factory methods**

In `Category` dataclass, add `effective_family_id` field after `family_id`:

```python
family_id: uuid.UUID | None = None
effective_family_id: uuid.UUID | None = None
```

Update `create_root`:
```python
@classmethod
def create_root(
    cls,
    name_i18n: dict[str, str],
    slug: str,
    sort_order: int = 0,
    family_id: uuid.UUID | None = None,
) -> Category:
    _validate_slug(slug, "Category")
    return cls(
        id=_generate_id(),
        parent_id=None,
        name_i18n=name_i18n,
        slug=slug,
        full_slug=slug,
        level=0,
        sort_order=sort_order,
        family_id=family_id,
        effective_family_id=family_id,  # root: own or None
    )
```

Update `create_child`:
```python
@classmethod
def create_child(
    cls,
    name_i18n: dict[str, str],
    slug: str,
    parent: Category,
    sort_order: int = 0,
    family_id: uuid.UUID | None = None,
) -> Category:
    _validate_slug(slug, "Category")
    if parent.level >= MAX_CATEGORY_DEPTH:
        raise CategoryMaxDepthError(
            max_depth=MAX_CATEGORY_DEPTH, current_level=parent.level
        )
    return cls(
        id=_generate_id(),
        parent_id=parent.id,
        name_i18n=name_i18n,
        slug=slug,
        full_slug=f"{parent.full_slug}/{slug}",
        level=parent.level + 1,
        sort_order=sort_order,
        family_id=family_id,
        effective_family_id=family_id or parent.effective_family_id,  # own or inherit
    )
```

- [ ] **Step 2: Add `set_effective_family_id` method**

Add after the `update()` method on Category (NOT in `_UPDATABLE_FIELDS`):

```python
def set_effective_family_id(self, value: uuid.UUID | None) -> None:
    """Set the computed effective_family_id (used by propagation logic)."""
    self.effective_family_id = value
```

- [ ] **Step 3: Update `update()` to recompute effective on family_id change**

Inside `Category.update()`, after the `family_id` assignment (the `if family_id is not ...` block), add recomputation. Replace the existing family_id handling:

```python
if family_id is not ...:
    self.family_id = family_id
    # Recompute effective: if own family is set, use it;
    # otherwise effective must be set externally by the handler
    # (requires parent lookup which domain entity cannot do)
    if family_id is not None:
        self.effective_family_id = family_id
```

- [ ] **Step 4: Commit**

```
git add src/modules/catalog/domain/entities.py
git commit -m "feat(catalog): add effective_family_id field to Category entity"
```

---

### Task 2: ORM Model — Add `effective_family_id` column

**Files:**
- Modify: `src/modules/catalog/infrastructure/models.py:99-161` (Category ORM class)

- [ ] **Step 1: Add column**

After the existing `family_id` column (line ~137), add:

```python
effective_family_id: Mapped[uuid.UUID | None] = mapped_column(
    ForeignKey("attribute_families.id", ondelete="SET NULL"),
    index=True,
    default=None,
    comment="Computed: own family_id or inherited from nearest ancestor",
)
```

- [ ] **Step 2: Commit**

```
git add src/modules/catalog/infrastructure/models.py
git commit -m "feat(catalog): add effective_family_id column to categories ORM model"
```

---

### Task 3: Fix Repository Data Mapper + Add Propagation

**Files:**
- Modify: `src/modules/catalog/domain/interfaces.py:99-139` (ICategoryRepository)
- Modify: `src/modules/catalog/infrastructure/repositories/category.py`

- [ ] **Step 1: Add interface method to ICategoryRepository**

In `src/modules/catalog/domain/interfaces.py`, add to `ICategoryRepository`:

```python
@abstractmethod
async def propagate_effective_family_id(
    self, category_id: uuid.UUID, effective_family_id: uuid.UUID | None
) -> list[uuid.UUID]:
    """Propagate effective_family_id to inheriting descendants via recursive CTE.

    Only updates children (and their descendants) where family_id IS NULL.
    Stops at nodes that have their own family_id.
    Returns affected category IDs (excluding root) for cache invalidation.
    """
    pass
```

- [ ] **Step 2: Fix `_to_domain` in CategoryRepository**

In `src/modules/catalog/infrastructure/repositories/category.py`, update `_to_domain` (line 31-41):

```python
def _to_domain(self, orm: OrmCategory) -> DomainCategory:
    return DomainCategory(
        id=orm.id,
        parent_id=orm.parent_id,
        name_i18n=orm.name_i18n or {},
        slug=orm.slug,
        full_slug=orm.full_slug,
        level=orm.level,
        sort_order=orm.sort_order,
        family_id=orm.family_id,
        effective_family_id=orm.effective_family_id,
    )
```

- [ ] **Step 3: Fix `_to_orm` in CategoryRepository**

Update `_to_orm` (line 43-56):

```python
def _to_orm(
    self, entity: DomainCategory, orm: OrmCategory | None = None
) -> OrmCategory:
    if orm is None:
        orm = OrmCategory()
    orm.id = entity.id
    orm.parent_id = entity.parent_id
    orm.name_i18n = entity.name_i18n
    orm.slug = entity.slug
    orm.full_slug = entity.full_slug
    orm.level = entity.level
    orm.sort_order = entity.sort_order
    orm.family_id = entity.family_id
    orm.effective_family_id = entity.effective_family_id
    return orm
```

- [ ] **Step 4: Implement `propagate_effective_family_id`**

Add to `CategoryRepository`, importing `text` from sqlalchemy:

```python
async def propagate_effective_family_id(
    self, category_id: uuid.UUID, effective_family_id: uuid.UUID | None
) -> list[uuid.UUID]:
    cte_sql = text("""
        WITH RECURSIVE subtree AS (
            SELECT id
            FROM categories
            WHERE parent_id = :root_id AND family_id IS NULL
            UNION ALL
            SELECT c.id
            FROM categories c
            JOIN subtree s ON c.parent_id = s.id
            WHERE c.family_id IS NULL
        )
        UPDATE categories
        SET effective_family_id = :eff_fid
        WHERE id IN (SELECT id FROM subtree)
        RETURNING id
    """)
    result = await self._session.execute(
        cte_sql,
        {
            "root_id": category_id,
            "eff_fid": effective_family_id,
        },
    )
    return [row[0] for row in result.all()]
```

- [ ] **Step 5: Commit**

```
git add src/modules/catalog/domain/interfaces.py src/modules/catalog/infrastructure/repositories/category.py
git commit -m "feat(catalog): fix repo mapper for family_id + add propagate_effective_family_id CTE"
```

---

### Task 4: Fix `get_category_ids_by_family_ids` to use `effective_family_id`

**Files:**
- Modify: `src/modules/catalog/infrastructure/repositories/attribute_family.py:143-151`

- [ ] **Step 1: Update query**

Change the `get_category_ids_by_family_ids` method to query `effective_family_id`:

```python
async def get_category_ids_by_family_ids(
    self, family_ids: list[uuid.UUID]
) -> list[uuid.UUID]:
    if not family_ids:
        return []
    stmt = select(OrmCategory.id).where(
        OrmCategory.effective_family_id.in_(family_ids)
    )
    result = await self._session.execute(stmt)
    return [row[0] for row in result.all()]
```

- [ ] **Step 2: Commit**

```
git add src/modules/catalog/infrastructure/repositories/attribute_family.py
git commit -m "fix(catalog): query effective_family_id in get_category_ids_by_family_ids"
```

---

### Task 5: Update Command Handlers

**Files:**
- Modify: `src/modules/catalog/application/commands/create_category.py`
- Modify: `src/modules/catalog/application/commands/update_category.py`

- [ ] **Step 1: Update create_category handler**

No code changes needed in the handler itself — the domain entity's `create_root` and `create_child` factory methods now compute `effective_family_id` automatically. The parent entity is already loaded at line 125 with `effective_family_id` mapped.

Verify that `CreateCategoryResult` includes `effective_family_id` — add it if missing:

In `CreateCategoryResult`, add:
```python
effective_family_id: uuid.UUID | None = None
```

And in the return statement at the end of `handle()`:
```python
return CreateCategoryResult(
    ...
    family_id=category.family_id,
    effective_family_id=category.effective_family_id,
)
```

- [ ] **Step 2: Update update_category handler — propagation logic**

In `src/modules/catalog/application/commands/update_category.py`:

**Imports:** Replace the `invalidate_storefront_cache` import (line 14-16) with cache key functions. Add the four `storefront_*_cache_key` imports to the existing `CATEGORY_TREE_CACHE_KEY` import:

```python
from src.modules.catalog.application.constants import (
    CATEGORY_TREE_CACHE_KEY,
    storefront_card_cache_key,
    storefront_comparison_cache_key,
    storefront_filters_cache_key,
    storefront_form_cache_key,
)
```

Remove the `from ...storefront import invalidate_storefront_cache` import (now unused).

**Propagation logic:** Insert Scenario C parent lookup BEFORE the existing `self._category_repo.update(category)` call (line 152), so there's only one DB write per entity. Restructure the UoW block:

```python
            # Handle Scenario C: clear family_id → re-inherit from parent
            if family_id_changed and command.family_id is None:
                if category.parent_id is not None:
                    parent = await self._category_repo.get(category.parent_id)
                    new_effective = parent.effective_family_id if parent else None
                else:
                    new_effective = None
                category.set_effective_family_id(new_effective)

            await self._category_repo.update(category)
            self._uow.register_aggregate(category)

            # Propagate effective_family_id to descendants
            affected_category_ids: list[uuid.UUID] = []
            if family_id_changed:
                descendant_ids = await self._category_repo.propagate_effective_family_id(
                    category.id, category.effective_family_id
                )
                affected_category_ids = [category.id, *descendant_ids]

            if old_full_slug is not None:
                await self._category_repo.update_descendants_full_slug(
                    old_prefix=old_full_slug,
                    new_prefix=category.full_slug,
                )

            await self._uow.commit()
```

Replace the existing storefront cache invalidation block (lines 170-177) with batch invalidation:

```python
        if affected_category_ids:
            try:
                keys = []
                for cat_id in affected_category_ids:
                    keys.append(storefront_filters_cache_key(cat_id))
                    keys.append(storefront_card_cache_key(cat_id))
                    keys.append(storefront_comparison_cache_key(cat_id))
                    keys.append(storefront_form_cache_key(cat_id))
                await self._cache.delete_many(keys)
            except Exception as e:
                self._logger.warning(
                    "Failed to invalidate storefront caches after family_id change",
                    error=str(e),
                    affected_count=len(affected_category_ids),
                )
```

Also add `effective_family_id` to `UpdateCategoryResult` and the return statement.

- [ ] **Step 3: Commit**

```
git add src/modules/catalog/application/commands/create_category.py src/modules/catalog/application/commands/update_category.py
git commit -m "feat(catalog): compute and propagate effective_family_id in create/update handlers"
```

---

### Task 6: Storefront Resolver — One-Line Fix

**Files:**
- Modify: `src/modules/catalog/application/queries/storefront.py:88-102`

- [ ] **Step 1: Change `family_id` to `effective_family_id`**

Replace lines 99-101:

```python
    if cat.effective_family_id is None:
        return []
    result = await resolver.handle(cat.effective_family_id)
```

- [ ] **Step 2: Commit**

```
git add src/modules/catalog/application/queries/storefront.py
git commit -m "feat(catalog): use effective_family_id in storefront resolver"
```

---

### Task 7: Update Seed Script

**Files:**
- Modify: `src/modules/catalog/management/sync_attributes.py`

- [ ] **Step 1: Add effective_family_id propagation SQL**

After `_ASSIGN_FAMILY_TO_CATEGORY`, add a new SQL statement:

```python
_PROPAGATE_EFFECTIVE_FAMILY = text("""
    UPDATE categories
    SET effective_family_id = :family_id
    WHERE (slug = :slug AND parent_id IS NULL)
       OR full_slug LIKE :slug || '/%'
""")
```

- [ ] **Step 2: Call propagation after family assignment**

In the `sync_attributes` function, after the `_ASSIGN_FAMILY_TO_CATEGORY` execution (inside the same `if` block around line 308-317), add:

```python
                await session.execute(
                    _PROPAGATE_EFFECTIVE_FAMILY,
                    {"family_id": str(fam_id), "slug": fam["assign_to_category_slug"]},
                )
                logger.info(
                    "effective_family_id.propagated",
                    category=fam["assign_to_category_slug"],
                    family=fam["code"],
                )
```

- [ ] **Step 3: Commit**

```
git add src/modules/catalog/management/sync_attributes.py
git commit -m "feat(catalog): propagate effective_family_id in seed script"
```

---

### Task 8: Alembic Migration

**Files:**
- Create: `alembic/versions/2026/03/26_XXXX_XX_<rev>_add_effective_family_id.py`

- [ ] **Step 1: Generate migration**

```bash
cd C:/Users/Sanjar/Desktop/loyality/backend
uv run alembic revision --autogenerate -m "add effective_family_id to categories"
```

- [ ] **Step 2: Add data backfill to upgrade()**

After the column addition in `upgrade()`, add a backfill operation:

```python
    # Backfill: copy family_id to effective_family_id for all categories
    # that have an explicit family_id (roots and any explicitly assigned)
    op.execute(sa.text("""
        UPDATE categories
        SET effective_family_id = family_id
        WHERE family_id IS NOT NULL
    """))

    # Propagate: for each category with effective_family_id set,
    # cascade to children that don't have their own family_id
    op.execute(sa.text("""
        UPDATE categories child
        SET effective_family_id = parent.effective_family_id
        FROM categories parent
        WHERE child.parent_id = parent.id
          AND child.family_id IS NULL
          AND parent.effective_family_id IS NOT NULL
          AND child.effective_family_id IS NULL
    """))

    # Level 2 children (max depth = 3, so one more pass covers everything)
    op.execute(sa.text("""
        UPDATE categories grandchild
        SET effective_family_id = parent.effective_family_id
        FROM categories parent
        WHERE grandchild.parent_id = parent.id
          AND grandchild.family_id IS NULL
          AND parent.effective_family_id IS NOT NULL
          AND grandchild.effective_family_id IS NULL
    """))
```

- [ ] **Step 3: Add column removal to downgrade()**

```python
    op.drop_column('categories', 'effective_family_id')
```

- [ ] **Step 4: Run migration**

```bash
uv run alembic upgrade head
```

- [ ] **Step 5: Commit**

```
git add alembic/
git commit -m "feat(catalog): migration — add effective_family_id column with backfill"
```

---

### Task 9: Integration Tests — Propagation

**Files:**
- Create: `tests/integration/modules/catalog/infrastructure/repositories/test_category_effective_family.py`

- [ ] **Step 1: Write test for propagation on create_child**

```python
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.entities import Category
from src.modules.catalog.infrastructure.repositories.category import CategoryRepository


async def test_create_child_inherits_effective_family_id(db_session: AsyncSession):
    """Child without own family_id inherits effective_family_id from parent."""
    repo = CategoryRepository(session=db_session)
    family_id = uuid.uuid4()

    root = Category.create_root(
        name_i18n={"en": "Clothing"},
        slug="clothing",
        family_id=family_id,
    )
    await repo.add(root)

    child = Category.create_child(
        name_i18n={"en": "T-Shirts"},
        slug="tees",
        parent=root,
    )
    result = await repo.add(child)

    assert result.family_id is None
    assert result.effective_family_id == family_id


async def test_create_child_with_own_family_overrides(db_session: AsyncSession):
    """Child with own family_id uses it as effective_family_id."""
    repo = CategoryRepository(session=db_session)
    parent_family = uuid.uuid4()
    child_family = uuid.uuid4()

    root = Category.create_root(
        name_i18n={"en": "Clothing"},
        slug="clothing",
        family_id=parent_family,
    )
    await repo.add(root)

    child = Category.create_child(
        name_i18n={"en": "Footwear"},
        slug="footwear",
        parent=root,
        family_id=child_family,
    )
    result = await repo.add(child)

    assert result.family_id == child_family
    assert result.effective_family_id == child_family
```

- [ ] **Step 2: Write test for recursive propagation**

```python
async def test_propagate_effective_family_id_to_descendants(db_session: AsyncSession):
    """propagate_effective_family_id updates inheriting descendants."""
    repo = CategoryRepository(session=db_session)
    family_id = uuid.uuid4()

    root = Category.create_root(name_i18n={"en": "Root"}, slug="root")
    await repo.add(root)

    child = Category.create_child(name_i18n={"en": "Child"}, slug="child", parent=root)
    await repo.add(child)

    grandchild = Category.create_child(
        name_i18n={"en": "Grandchild"}, slug="grandchild", parent=child
    )
    await repo.add(grandchild)

    # Simulate: root gets family_id assigned
    root.family_id = family_id
    root.set_effective_family_id(family_id)
    await repo.update(root)

    affected = await repo.propagate_effective_family_id(root.id, family_id)

    assert len(affected) == 2  # child + grandchild

    reloaded_child = await repo.get(child.id)
    reloaded_grandchild = await repo.get(grandchild.id)
    assert reloaded_child.effective_family_id == family_id
    assert reloaded_grandchild.effective_family_id == family_id


async def test_propagation_stops_at_own_family(db_session: AsyncSession):
    """Propagation skips descendants that have their own family_id."""
    repo = CategoryRepository(session=db_session)
    root_family = uuid.uuid4()
    child_family = uuid.uuid4()

    root = Category.create_root(name_i18n={"en": "Root"}, slug="root")
    await repo.add(root)

    # child has OWN family
    child = Category.create_child(
        name_i18n={"en": "Child"}, slug="child", parent=root, family_id=child_family
    )
    await repo.add(child)

    # grandchild inherits from child
    grandchild = Category.create_child(
        name_i18n={"en": "GC"}, slug="gc", parent=child
    )
    await repo.add(grandchild)

    affected = await repo.propagate_effective_family_id(root.id, root_family)

    # child has own family_id → skipped; grandchild is under child → also skipped
    assert len(affected) == 0

    reloaded_child = await repo.get(child.id)
    assert reloaded_child.effective_family_id == child_family  # unchanged
```

- [ ] **Step 3: Write tests for update_category Scenarios A/B/C**

These test the handler-level orchestration of the three family_id change scenarios:

```python
async def test_scenario_a_set_family_propagates(db_session: AsyncSession):
    """Scenario A: NULL → family_id propagates to inheriting descendants."""
    repo = CategoryRepository(session=db_session)
    family_id = uuid.uuid4()

    root = Category.create_root(name_i18n={"en": "Root"}, slug="root")
    await repo.add(root)
    child = Category.create_child(name_i18n={"en": "Child"}, slug="child", parent=root)
    await repo.add(child)

    # Simulate handler: set family on root
    root.update(family_id=family_id)
    # effective_family_id is set by update() when family_id is not None
    await repo.update(root)
    affected = await repo.propagate_effective_family_id(root.id, family_id)

    assert len(affected) == 1
    reloaded = await repo.get(child.id)
    assert reloaded.effective_family_id == family_id


async def test_scenario_b_change_family_propagates(db_session: AsyncSession):
    """Scenario B: family_X → family_Y propagates new value."""
    repo = CategoryRepository(session=db_session)
    old_fid = uuid.uuid4()
    new_fid = uuid.uuid4()

    root = Category.create_root(
        name_i18n={"en": "Root"}, slug="root", family_id=old_fid
    )
    await repo.add(root)
    child = Category.create_child(name_i18n={"en": "Child"}, slug="child", parent=root)
    await repo.add(child)

    # Change family
    root.update(family_id=new_fid)
    await repo.update(root)
    await repo.propagate_effective_family_id(root.id, new_fid)

    reloaded = await repo.get(child.id)
    assert reloaded.effective_family_id == new_fid


async def test_scenario_c_clear_family_resets_children(db_session: AsyncSession):
    """Scenario C: family_id → NULL re-inherits from parent (or clears for root)."""
    repo = CategoryRepository(session=db_session)
    fid = uuid.uuid4()

    root = Category.create_root(
        name_i18n={"en": "Root"}, slug="root", family_id=fid
    )
    await repo.add(root)
    child = Category.create_child(name_i18n={"en": "Child"}, slug="child", parent=root)
    await repo.add(child)

    # Clear family on root → effective becomes None
    root.update(family_id=None)
    root.set_effective_family_id(None)  # handler does this after parent lookup
    await repo.update(root)
    await repo.propagate_effective_family_id(root.id, None)

    reloaded = await repo.get(child.id)
    assert reloaded.effective_family_id is None
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/integration/modules/catalog/infrastructure/repositories/test_category_effective_family.py -v
```

- [ ] **Step 5: Commit**

```
git add tests/integration/modules/catalog/infrastructure/repositories/test_category_effective_family.py
git commit -m "test(catalog): integration tests for effective_family_id propagation and scenarios A/B/C"
```

---

### Task 10: Unit Tests — Domain Entity

**Files:**
- Create: `tests/unit/modules/catalog/domain/test_category_effective_family.py`

- [ ] **Step 1: Write unit tests**

```python
import uuid

from src.modules.catalog.domain.entities import Category


class TestCategoryEffectiveFamilyId:
    def test_create_root_with_family(self):
        fid = uuid.uuid4()
        cat = Category.create_root(
            name_i18n={"en": "Root"}, slug="root", family_id=fid
        )
        assert cat.effective_family_id == fid

    def test_create_root_without_family(self):
        cat = Category.create_root(name_i18n={"en": "Root"}, slug="root")
        assert cat.effective_family_id is None

    def test_create_child_inherits_from_parent(self):
        fid = uuid.uuid4()
        parent = Category.create_root(
            name_i18n={"en": "Parent"}, slug="parent", family_id=fid
        )
        child = Category.create_child(
            name_i18n={"en": "Child"}, slug="child", parent=parent
        )
        assert child.family_id is None
        assert child.effective_family_id == fid

    def test_create_child_own_family_overrides_parent(self):
        parent_fid = uuid.uuid4()
        child_fid = uuid.uuid4()
        parent = Category.create_root(
            name_i18n={"en": "P"}, slug="p", family_id=parent_fid
        )
        child = Category.create_child(
            name_i18n={"en": "C"}, slug="c", parent=parent, family_id=child_fid
        )
        assert child.effective_family_id == child_fid

    def test_set_effective_family_id(self):
        cat = Category.create_root(name_i18n={"en": "R"}, slug="r")
        fid = uuid.uuid4()
        cat.set_effective_family_id(fid)
        assert cat.effective_family_id == fid

    def test_update_family_id_recomputes_effective(self):
        cat = Category.create_root(name_i18n={"en": "R"}, slug="r")
        fid = uuid.uuid4()
        cat.update(family_id=fid)
        assert cat.effective_family_id == fid
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest tests/unit/modules/catalog/domain/test_category_effective_family.py -v
```

- [ ] **Step 3: Commit**

```
git add tests/unit/modules/catalog/domain/test_category_effective_family.py
git commit -m "test(catalog): unit tests for Category effective_family_id domain logic"
```

---

### Task 11: Verify End-to-End

- [ ] **Step 1: Run full test suite**

```bash
uv run pytest tests/unit/ tests/integration/ tests/architecture/ -v --tb=short
```

Expect all tests to pass, including the existing category tests (which now get `family_id` and `effective_family_id` mapped through the repo).

- [ ] **Step 2: Run architecture tests specifically**

```bash
uv run pytest tests/architecture/ -v
```

Ensure domain entity changes don't violate layer boundaries.

- [ ] **Step 3: Run linting and type checks**

```bash
uv run ruff check src/modules/catalog/ && uv run ruff format --check src/modules/catalog/
```

- [ ] **Step 4: Final commit if any fixes needed**

```
git add -A
git commit -m "chore: fix lint/type issues from effective_family_id implementation"
```
