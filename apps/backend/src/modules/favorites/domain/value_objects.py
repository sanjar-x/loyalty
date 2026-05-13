"""
Favorites domain value objects.

Part of the domain layer -- zero infrastructure imports.
"""

import enum


class FavoriteTargetType(enum.StrEnum):
    """Kinds of entities a user can mark as favorite.

    The set is closed at the domain level — adding a new target type
    requires updating the catalog ACL validator and the storefront
    enrichment query.
    """

    PRODUCT = "product"
    BRAND = "brand"
