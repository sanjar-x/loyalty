"""Smoke tests for the N+1 query detection async context manager.

Validates that assert_query_count correctly counts application-level SQL
queries, ignores SAVEPOINT statements from test isolation, and raises
AssertionError on count mismatches.

Requires database: docker compose up -d
"""

import pytest
from sqlalchemy import text

from tests.utils.query_counter import assert_query_count


@pytest.mark.integration
class TestQueryCounter:
    """Integration tests for the async query counter context manager."""

    async def test_counts_single_query(self, db_session):
        """Verify counter detects exactly 1 query."""
        async with assert_query_count(db_session, expected=1, label="single_select"):
            await db_session.execute(text("SELECT 1"))

    async def test_counts_multiple_queries(self, db_session):
        """Verify counter detects exactly N queries."""
        async with assert_query_count(db_session, expected=3, label="three_selects"):
            await db_session.execute(text("SELECT 1"))
            await db_session.execute(text("SELECT 2"))
            await db_session.execute(text("SELECT 3"))

    async def test_fails_on_wrong_count(self, db_session):
        """Verify counter raises AssertionError on mismatch."""
        with pytest.raises(AssertionError, match="Expected 5 queries"):
            async with assert_query_count(db_session, expected=5):
                await db_session.execute(text("SELECT 1"))

    async def test_excludes_savepoint_statements(self, db_session):
        """Verify SAVEPOINT/RELEASE are not counted.

        The db_session fixture already uses begin_nested() which creates
        savepoints. This test verifies those don't inflate the count.
        """
        async with assert_query_count(
            db_session, expected=1, label="savepoint_exclusion"
        ):
            await db_session.execute(text("SELECT 1"))
