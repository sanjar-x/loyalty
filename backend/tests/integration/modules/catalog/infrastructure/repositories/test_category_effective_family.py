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

    child = Category.create_child(
        name_i18n={"en": "Child"}, slug="child", parent=root, family_id=child_family
    )
    await repo.add(child)

    grandchild = Category.create_child(
        name_i18n={"en": "GC"}, slug="gc", parent=child
    )
    await repo.add(grandchild)

    affected = await repo.propagate_effective_family_id(root.id, root_family)

    # child has own family_id -> skipped; grandchild is under child -> also skipped
    assert len(affected) == 0

    reloaded_child = await repo.get(child.id)
    assert reloaded_child.effective_family_id == child_family  # unchanged


async def test_scenario_a_set_family_propagates(db_session: AsyncSession):
    """Scenario A: NULL -> family_id propagates to inheriting descendants."""
    repo = CategoryRepository(session=db_session)
    family_id = uuid.uuid4()

    root = Category.create_root(name_i18n={"en": "Root"}, slug="root")
    await repo.add(root)
    child = Category.create_child(name_i18n={"en": "Child"}, slug="child", parent=root)
    await repo.add(child)

    root.update(family_id=family_id)
    await repo.update(root)
    affected = await repo.propagate_effective_family_id(root.id, family_id)

    assert len(affected) == 1
    reloaded = await repo.get(child.id)
    assert reloaded.effective_family_id == family_id


async def test_scenario_b_change_family_propagates(db_session: AsyncSession):
    """Scenario B: family_X -> family_Y propagates new value."""
    repo = CategoryRepository(session=db_session)
    old_fid = uuid.uuid4()
    new_fid = uuid.uuid4()

    root = Category.create_root(
        name_i18n={"en": "Root"}, slug="root", family_id=old_fid
    )
    await repo.add(root)
    child = Category.create_child(name_i18n={"en": "Child"}, slug="child", parent=root)
    await repo.add(child)

    root.update(family_id=new_fid)
    await repo.update(root)
    await repo.propagate_effective_family_id(root.id, new_fid)

    reloaded = await repo.get(child.id)
    assert reloaded.effective_family_id == new_fid


async def test_scenario_c_clear_family_resets_children(db_session: AsyncSession):
    """Scenario C: family_id -> NULL re-inherits from parent (or clears for root)."""
    repo = CategoryRepository(session=db_session)
    fid = uuid.uuid4()

    root = Category.create_root(
        name_i18n={"en": "Root"}, slug="root", family_id=fid
    )
    await repo.add(root)
    child = Category.create_child(name_i18n={"en": "Child"}, slug="child", parent=root)
    await repo.add(child)

    # Clear family on root -> effective becomes None
    root.update(family_id=None)
    root.set_effective_family_id(None)
    await repo.update(root)
    await repo.propagate_effective_family_id(root.id, None)

    reloaded = await repo.get(child.id)
    assert reloaded.effective_family_id is None
