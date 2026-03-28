"""Per-entity Hypothesis strategies for catalog domain models.

Each function returns a SearchStrategy that generates a valid domain
entity via @st.composite on the entity's create() factory method.
Imports leaf strategies from .primitives for composability.
"""

from __future__ import annotations

import uuid

from hypothesis import strategies as st

from src.modules.catalog.domain.entities import (
    Attribute,
    AttributeGroup,
    AttributeTemplate,
    AttributeValue,
    Brand,
    Category,
    MediaAsset,
    Product,
    TemplateAttributeBinding,
)
from src.modules.catalog.domain.value_objects import AttributeLevel
from tests.factories.strategies.primitives import (
    attribute_levels,
    behavior_flags,
    data_types,
    i18n_names,
    media_roles,
    media_types,
    requirement_levels,
    ui_types,
    uuids,
    valid_codes,
    valid_slugs,
)


@st.composite
def brands(draw: st.DrawFn) -> Brand:
    """Generate a valid Brand entity via Brand.create().

    Returns:
        Strategy producing Brand instances with valid names and slugs.
    """
    name = draw(
        st.text(
            min_size=1,
            max_size=100,
            alphabet=st.characters(
                whitelist_categories=("L", "N", "Zs"),
                min_codepoint=65,
                max_codepoint=1000,
            ),
        ).filter(lambda s: s.strip())
    )
    slug = draw(valid_slugs())
    return Brand.create(name=name, slug=slug)


@st.composite
def attribute_groups(draw: st.DrawFn) -> AttributeGroup:
    """Generate a valid AttributeGroup entity via AttributeGroup.create().

    Returns:
        Strategy producing AttributeGroup instances.
    """
    return AttributeGroup.create(
        code=draw(valid_codes()),
        name_i18n=draw(i18n_names()),
        sort_order=draw(st.integers(min_value=0, max_value=100)),
    )


@st.composite
def attributes(
    draw: st.DrawFn,
    group_id: uuid.UUID | None = None,
) -> Attribute:
    """Generate a valid Attribute entity via Attribute.create().

    Args:
        group_id: Optional fixed group_id. If None, generates a random UUID.

    Returns:
        Strategy producing Attribute instances.
    """
    gid = group_id if group_id is not None else draw(uuids())
    bhv = draw(behavior_flags() | st.none())
    return Attribute.create(
        code=draw(valid_codes()),
        slug=draw(valid_slugs()),
        name_i18n=draw(i18n_names()),
        data_type=draw(data_types()),
        ui_type=draw(ui_types()),
        is_dictionary=draw(st.booleans()),
        group_id=gid,
        description_i18n=draw(i18n_names() | st.none()),
        level=draw(attribute_levels()),
        behavior=bhv,
        validation_rules=None,
    )


@st.composite
def attribute_values(
    draw: st.DrawFn,
    attribute_id: uuid.UUID | None = None,
) -> AttributeValue:
    """Generate a valid AttributeValue entity via AttributeValue.create().

    Args:
        attribute_id: Optional fixed attribute_id. If None, generates a random UUID.

    Returns:
        Strategy producing AttributeValue instances.
    """
    attr_id = attribute_id if attribute_id is not None else draw(uuids())
    return AttributeValue.create(
        attribute_id=attr_id,
        code=draw(valid_codes()),
        slug=draw(valid_slugs()),
        value_i18n=draw(i18n_names()),
        sort_order=draw(st.integers(min_value=0, max_value=100)),
    )


@st.composite
def root_categories(draw: st.DrawFn) -> Category:
    """Generate a valid root Category entity via Category.create_root().

    Returns:
        Strategy producing root Category instances (level=0, no parent).
    """
    return Category.create_root(
        name_i18n=draw(i18n_names()),
        slug=draw(valid_slugs()),
        sort_order=draw(st.integers(min_value=0, max_value=100)),
    )


@st.composite
def attribute_templates(draw: st.DrawFn) -> AttributeTemplate:
    """Generate a valid AttributeTemplate entity via AttributeTemplate.create().

    Returns:
        Strategy producing AttributeTemplate instances.
    """
    return AttributeTemplate.create(
        code=draw(valid_codes()),
        name_i18n=draw(i18n_names()),
        sort_order=draw(st.integers(min_value=0, max_value=100)),
    )


@st.composite
def template_bindings(
    draw: st.DrawFn,
    template_id: uuid.UUID | None = None,
    attribute_id: uuid.UUID | None = None,
) -> TemplateAttributeBinding:
    """Generate a valid TemplateAttributeBinding entity.

    Args:
        template_id: Optional fixed template_id.
        attribute_id: Optional fixed attribute_id.

    Returns:
        Strategy producing TemplateAttributeBinding instances.
    """
    tid = template_id if template_id is not None else draw(uuids())
    aid = attribute_id if attribute_id is not None else draw(uuids())
    return TemplateAttributeBinding.create(
        template_id=tid,
        attribute_id=aid,
        sort_order=draw(st.integers(min_value=0, max_value=100)),
        requirement_level=draw(requirement_levels()),
    )


@st.composite
def products(
    draw: st.DrawFn,
    brand_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
) -> Product:
    """Generate a valid Product entity via Product.create().

    Creates a Product in DRAFT status with one default variant.

    Args:
        brand_id: Optional fixed brand_id.
        category_id: Optional fixed category_id.

    Returns:
        Strategy producing Product instances.
    """
    bid = brand_id if brand_id is not None else draw(uuids())
    cid = category_id if category_id is not None else draw(uuids())
    return Product.create(
        slug=draw(valid_slugs()),
        title_i18n=draw(i18n_names()),
        brand_id=bid,
        primary_category_id=cid,
    )


@st.composite
def media_assets(
    draw: st.DrawFn,
    product_id: uuid.UUID | None = None,
) -> MediaAsset:
    """Generate a valid MediaAsset entity via MediaAsset.create().

    Args:
        product_id: Optional fixed product_id.

    Returns:
        Strategy producing MediaAsset instances.
    """
    pid = product_id if product_id is not None else draw(uuids())
    return MediaAsset.create(
        product_id=pid,
        media_type=draw(media_types()),
        role=draw(media_roles()),
        sort_order=draw(st.integers(min_value=0, max_value=100)),
    )
