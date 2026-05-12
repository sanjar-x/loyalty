"""Expected query counts for common catalog repository operations.

These baselines are established during Phase 7 and used in regression tests.
Values marked as None will be filled in when integration tests are written.
"""

from __future__ import annotations

EXPECTED_COUNTS: dict[str, int | None] = {
    # Brand operations
    "brand.list_all": None,  # TBD Phase 7
    "brand.get_by_id": 1,  # Single SELECT
    "brand.create": None,  # TBD Phase 7
    # Category operations
    "category.get_all_ordered": None,  # TBD Phase 7
    "category.get_by_id": 1,
    # Product operations (most complex due to eager loading)
    "product.get_with_variants": None,  # TBD Phase 7 (expect 1-3 with joinedload)
    "product.list_products": None,  # TBD Phase 7
    # Storefront queries
    "storefront.product_listing": None,  # TBD Phase 8
    "storefront.product_detail": None,  # TBD Phase 8
}


def get_expected_count(operation: str) -> int:
    """Look up the expected query count baseline for a catalog operation.

    Args:
        operation: The operation key (e.g. "brand.get_by_id").

    Returns:
        The expected query count.

    Raises:
        ValueError: If the baseline is not yet established (None) or unknown.
    """
    count = EXPECTED_COUNTS.get(operation)
    if count is None:
        raise ValueError(
            f"Query count baseline for '{operation}' not yet established. "
            f"Run the operation manually and set the baseline in "
            f"catalog_query_baselines.py"
        )
    return count
