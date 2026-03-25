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

    def test_create_child_no_parent_family_no_inheritance(self):
        parent = Category.create_root(name_i18n={"en": "P"}, slug="p")
        child = Category.create_child(
            name_i18n={"en": "C"}, slug="c", parent=parent
        )
        assert child.effective_family_id is None

    def test_set_effective_family_id(self):
        cat = Category.create_root(name_i18n={"en": "R"}, slug="r")
        fid = uuid.uuid4()
        cat.set_effective_family_id(fid)
        assert cat.effective_family_id == fid

    def test_set_effective_family_id_to_none(self):
        fid = uuid.uuid4()
        cat = Category.create_root(name_i18n={"en": "R"}, slug="r", family_id=fid)
        cat.set_effective_family_id(None)
        assert cat.effective_family_id is None

    def test_update_family_id_recomputes_effective(self):
        cat = Category.create_root(name_i18n={"en": "R"}, slug="r")
        fid = uuid.uuid4()
        cat.update(family_id=fid)
        assert cat.effective_family_id == fid

    def test_update_clear_family_id_does_not_clear_effective(self):
        """When clearing family_id, handler must explicitly set effective."""
        fid = uuid.uuid4()
        cat = Category.create_root(name_i18n={"en": "R"}, slug="r", family_id=fid)
        cat.update(family_id=None)
        # effective is NOT cleared by update() — handler must call set_effective_family_id()
        assert cat.effective_family_id == fid
