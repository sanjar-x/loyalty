import uuid

from src.modules.catalog.domain.entities import Category


def _i18n(en: str) -> dict[str, str]:
    """Build a valid i18n dict with both required locales."""
    return {"en": en, "ru": en}


class TestCategoryEffectiveTemplateId:
    def test_create_root_with_template(self):
        fid = uuid.uuid4()
        cat = Category.create_root(
            name_i18n=_i18n("Root"), slug="root", template_id=fid
        )
        assert cat.effective_template_id == fid

    def test_create_root_without_template(self):
        cat = Category.create_root(name_i18n=_i18n("Root"), slug="root")
        assert cat.effective_template_id is None

    def test_create_child_inherits_from_parent(self):
        fid = uuid.uuid4()
        parent = Category.create_root(
            name_i18n=_i18n("Parent"), slug="parent", template_id=fid
        )
        child = Category.create_child(
            name_i18n=_i18n("Child"), slug="child", parent=parent
        )
        assert child.template_id is None
        assert child.effective_template_id == fid

    def test_create_child_own_template_overrides_parent(self):
        parent_fid = uuid.uuid4()
        child_fid = uuid.uuid4()
        parent = Category.create_root(
            name_i18n=_i18n("P"), slug="p", template_id=parent_fid
        )
        child = Category.create_child(
            name_i18n=_i18n("C"), slug="c", parent=parent, template_id=child_fid
        )
        assert child.effective_template_id == child_fid

    def test_create_child_no_parent_template_no_inheritance(self):
        parent = Category.create_root(name_i18n=_i18n("P"), slug="p")
        child = Category.create_child(name_i18n=_i18n("C"), slug="c", parent=parent)
        assert child.effective_template_id is None

    def test_set_effective_template_id(self):
        cat = Category.create_root(name_i18n=_i18n("R"), slug="r")
        fid = uuid.uuid4()
        cat.set_effective_template_id(fid)
        assert cat.effective_template_id == fid

    def test_set_effective_template_id_to_none(self):
        fid = uuid.uuid4()
        cat = Category.create_root(name_i18n=_i18n("R"), slug="r", template_id=fid)
        cat.set_effective_template_id(None)
        assert cat.effective_template_id is None

    def test_update_template_id_recomputes_effective(self):
        cat = Category.create_root(name_i18n=_i18n("R"), slug="r")
        fid = uuid.uuid4()
        cat.update(template_id=fid)
        assert cat.effective_template_id == fid

    def test_update_clear_template_id_does_not_clear_effective(self):
        """When clearing template_id, handler must explicitly set effective."""
        fid = uuid.uuid4()
        cat = Category.create_root(name_i18n=_i18n("R"), slug="r", template_id=fid)
        cat.update(template_id=None)
        # effective is NOT cleared by update() — handler must call set_effective_template_id()
        assert cat.effective_template_id == fid
