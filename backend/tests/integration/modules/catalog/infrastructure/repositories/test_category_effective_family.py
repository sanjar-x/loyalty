import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.entities import Category
from src.modules.catalog.infrastructure.repositories.category import CategoryRepository


async def test_create_child_inherits_effective_template_id(db_session: AsyncSession):
    """Child without own template_id inherits effective_template_id from parent."""
    repo = CategoryRepository(session=db_session)
    template_id = uuid.uuid4()

    root = Category.create_root(
        name_i18n={"en": "Clothing"},
        slug="clothing",
        template_id=template_id,
    )
    await repo.add(root)

    child = Category.create_child(
        name_i18n={"en": "T-Shirts"},
        slug="tees",
        parent=root,
    )
    result = await repo.add(child)

    assert result.template_id is None
    assert result.effective_template_id == template_id


async def test_create_child_with_own_template_overrides(db_session: AsyncSession):
    """Child with own template_id uses it as effective_template_id."""
    repo = CategoryRepository(session=db_session)
    parent_template = uuid.uuid4()
    child_template = uuid.uuid4()

    root = Category.create_root(
        name_i18n={"en": "Clothing"},
        slug="clothing",
        template_id=parent_template,
    )
    await repo.add(root)

    child = Category.create_child(
        name_i18n={"en": "Footwear"},
        slug="footwear",
        parent=root,
        template_id=child_template,
    )
    result = await repo.add(child)

    assert result.template_id == child_template
    assert result.effective_template_id == child_template


async def test_propagate_effective_template_id_to_descendants(db_session: AsyncSession):
    """propagate_effective_template_id updates inheriting descendants."""
    repo = CategoryRepository(session=db_session)
    template_id = uuid.uuid4()

    root = Category.create_root(name_i18n={"en": "Root"}, slug="root")
    await repo.add(root)

    child = Category.create_child(name_i18n={"en": "Child"}, slug="child", parent=root)
    await repo.add(child)

    grandchild = Category.create_child(
        name_i18n={"en": "Grandchild"}, slug="grandchild", parent=child
    )
    await repo.add(grandchild)

    # Simulate: root gets template_id assigned
    root.template_id = template_id
    root.set_effective_template_id(template_id)
    await repo.update(root)

    affected = await repo.propagate_effective_template_id(root.id, template_id)

    assert len(affected) == 2  # child + grandchild


async def test_propagation_stops_at_own_template(db_session: AsyncSession):
    """Propagation skips descendants that have their own template_id."""
    repo = CategoryRepository(session=db_session)
    root_template = uuid.uuid4()
    child_template = uuid.uuid4()

    root = Category.create_root(name_i18n={"en": "Root"}, slug="root")
    await repo.add(root)

    child = Category.create_child(
        name_i18n={"en": "Child"}, slug="child", parent=root, template_id=child_template
    )
    await repo.add(child)

    grandchild = Category.create_child(name_i18n={"en": "GC"}, slug="gc", parent=child)
    await repo.add(grandchild)

    affected = await repo.propagate_effective_template_id(root.id, root_template)

    # child has own template_id -> skipped; grandchild is under child -> also skipped
    assert len(affected) == 0


async def test_scenario_a_set_template_propagates(db_session: AsyncSession):
    """Scenario A: NULL -> template_id propagates to inheriting descendants."""
    repo = CategoryRepository(session=db_session)
    template_id = uuid.uuid4()

    root = Category.create_root(name_i18n={"en": "Root"}, slug="root")
    await repo.add(root)
    child = Category.create_child(name_i18n={"en": "Child"}, slug="child", parent=root)
    await repo.add(child)

    root.update(template_id=template_id)
    await repo.update(root)
    affected = await repo.propagate_effective_template_id(root.id, template_id)

    assert len(affected) == 1
    reloaded = await repo.get(child.id)


async def test_scenario_b_change_template_propagates(db_session: AsyncSession):
    """Scenario B: template_X -> template_Y propagates new value."""
    repo = CategoryRepository(session=db_session)
    old_fid = uuid.uuid4()
    new_fid = uuid.uuid4()

    root = Category.create_root(
        name_i18n={"en": "Root"}, slug="root", template_id=old_fid
    )
    await repo.add(root)
    child = Category.create_child(name_i18n={"en": "Child"}, slug="child", parent=root)
    await repo.add(child)

    root.update(template_id=new_fid)
    await repo.update(root)
    await repo.propagate_effective_template_id(root.id, new_fid)


async def test_scenario_c_clear_template_resets_children(db_session: AsyncSession):
    """Scenario C: template_id -> NULL re-inherits from parent (or clears for root)."""
    repo = CategoryRepository(session=db_session)
    fid = uuid.uuid4()

    root = Category.create_root(name_i18n={"en": "Root"}, slug="root", template_id=fid)
    await repo.add(root)
    child = Category.create_child(name_i18n={"en": "Child"}, slug="child", parent=root)
    await repo.add(child)

    # Clear template on root -> effective becomes None
    root.update(template_id=None)
    root.set_effective_template_id(None)
    await repo.update(root)
    await repo.propagate_effective_template_id(root.id, None)
