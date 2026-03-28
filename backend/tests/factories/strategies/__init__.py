"""Composable Hypothesis strategies for catalog domain models.

Three-layer hierarchy:
  - primitives: Leaf strategies for value objects (Money, slugs, i18n, enums)
  - entity_strategies: Per-entity strategies (Brand, Product, Attribute, etc.)
  - aggregate_strategies: Full aggregate trees (Product -> Variant -> SKU)
"""

from tests.factories.strategies.primitives import (
    behavior_flags,
    data_types,
    i18n_names,
    money,
    tags,
    ui_types,
    uuids,
    valid_codes,
    valid_slugs,
)
from tests.factories.strategies.entity_strategies import (
    attribute_groups,
    attribute_templates,
    attribute_values,
    attributes,
    brands,
    media_assets,
    products,
    root_categories,
    template_bindings,
)
from tests.factories.strategies.aggregate_strategies import (
    attribute_sets,
    product_trees,
)

__all__ = [
    # Primitives
    "behavior_flags",
    "data_types",
    "i18n_names",
    "money",
    "tags",
    "ui_types",
    "uuids",
    "valid_codes",
    "valid_slugs",
    # Entities
    "attribute_groups",
    "attribute_templates",
    "attribute_values",
    "attributes",
    "brands",
    "media_assets",
    "products",
    "root_categories",
    "template_bindings",
    # Aggregates
    "attribute_sets",
    "product_trees",
]
