"""Full aggregate tree Hypothesis strategies (Product -> Variant -> SKU).

Composes entity strategies into complete aggregate graphs for testing
complex domain invariants and EAV combinatorial scenarios.

Recommended settings for consumers::

    @settings(max_examples=50, deadline=timedelta(seconds=5))
"""

from __future__ import annotations

import uuid

from hypothesis import strategies as st

from src.modules.catalog.domain.entities import (
    Attribute,
    AttributeGroup,
    AttributeValue,
    Product,
)
from tests.factories.strategies.entity_strategies import (
    attribute_groups,
    attribute_values,
    attributes,
    products,
)
from tests.factories.strategies.primitives import (
    i18n_names,
    money,
    valid_codes,
    valid_slugs,
)


@st.composite
def product_trees(
    draw: st.DrawFn,
    max_variants: int = 3,
    max_skus_per_variant: int = 3,
) -> Product:
    """Generate a complete Product with variants and SKUs.

    Product.create() already creates 1 default variant. This strategy
    adds 0 to max_variants-1 additional variants, then adds SKUs to
    each variant with unique sku_codes.

    Args:
        max_variants: Maximum total variants (including the default one).
        max_skus_per_variant: Maximum SKUs per variant.

    Returns:
        Strategy producing Product instances with variants and SKUs.
    """
    product = draw(products())

    # Add 0 to max_variants-1 additional variants
    n_extra = draw(st.integers(min_value=0, max_value=max(0, max_variants - 1)))
    for i in range(n_extra):
        variant_name = draw(i18n_names())
        product.add_variant(name_i18n=variant_name, sort_order=i + 1)

    # Track used sku_codes to guarantee uniqueness within the product
    used_codes: set[str] = set()

    # Add SKUs to each variant
    for variant in product.variants:
        n_skus = draw(st.integers(min_value=0, max_value=max_skus_per_variant))
        for j in range(n_skus):
            # Generate unique sku_code by suffixing with variant+sku index
            base_code = draw(
                st.text(
                    min_size=3,
                    max_size=15,
                    alphabet=st.characters(whitelist_categories=("L", "N")),
                ).filter(lambda s: s.strip())
            )
            # Ensure uniqueness by appending index if needed
            sku_code = f"{base_code}-{variant.id.hex[:4]}-{j}"
            while sku_code in used_codes:
                sku_code = f"{sku_code}-{draw(st.integers(min_value=0, max_value=999))}"
            used_codes.add(sku_code)

            price = draw(money() | st.none())

            # Each SKU in the same variant needs unique variant_attributes
            # to avoid DuplicateVariantCombinationError. We use a synthetic
            # (attribute_id, attribute_value_id) pair unique per SKU index.
            variant_attrs: list[tuple[uuid.UUID, uuid.UUID]] = [
                (draw(st.uuids(version=4)), draw(st.uuids(version=4)))
            ]

            product.add_sku(
                variant.id,
                sku_code=sku_code,
                price=price,
                variant_attributes=variant_attrs,
            )

    return product


@st.composite
def attribute_sets(
    draw: st.DrawFn,
    min_attrs: int = 1,
    max_attrs: int = 5,
) -> tuple[AttributeGroup, list[Attribute], list[list[AttributeValue]]]:
    """Generate an attribute group with multiple attributes, each with multiple values.

    Useful for testing EAV combinatorial scenarios.

    Args:
        min_attrs: Minimum number of attributes in the group.
        max_attrs: Maximum number of attributes in the group.

    Returns:
        Tuple of (group, attributes_list, values_per_attribute).
    """
    group = draw(attribute_groups())

    n_attrs = draw(st.integers(min_value=min_attrs, max_value=max_attrs))
    attrs: list[Attribute] = []
    all_values: list[list[AttributeValue]] = []

    for _ in range(n_attrs):
        attr = draw(attributes(group_id=group.id))
        attrs.append(attr)

        # Generate 1-5 values per attribute
        n_values = draw(st.integers(min_value=1, max_value=5))
        values: list[AttributeValue] = []
        used_slugs: set[str] = set()
        used_codes: set[str] = set()

        for __ in range(n_values):
            # Ensure unique slugs and codes within an attribute
            slug = draw(valid_slugs())
            while slug in used_slugs:
                slug = draw(valid_slugs())
            used_slugs.add(slug)

            code = draw(valid_codes())
            while code in used_codes:
                code = draw(valid_codes())
            used_codes.add(code)

            val = AttributeValue.create(
                attribute_id=attr.id,
                code=code,
                slug=slug,
                value_i18n=draw(i18n_names()),
                sort_order=len(values),
            )
            values.append(val)

        all_values.append(values)

    return group, attrs, all_values
