"""Test utilities for the catalog module.

Provides reusable test helpers including query counting for N+1 detection.
"""

from tests.utils.query_counter import assert_query_count

__all__ = ["assert_query_count"]
