"""N+1 query detection async context manager.

Hooks into SQLAlchemy's after_cursor_execute event on the underlying
sync connection to count application-level SQL queries. Filters out
SAVEPOINT/RELEASE SAVEPOINT/ROLLBACK TO SAVEPOINT statements that are
artifacts of the nested-transaction test isolation pattern.

Usage::

    async with assert_query_count(db_session, expected=1, label="list_brands"):
        result = await brand_repo.list_all()
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def assert_query_count(
    session: AsyncSession,
    expected: int,
    *,
    label: str = "",
) -> AsyncIterator[None]:
    """Async context manager that counts SQL queries and asserts exact count.

    Hooks into SQLAlchemy's after_cursor_execute event on the underlying
    sync connection. Filters out SAVEPOINT, RELEASE SAVEPOINT, and
    ROLLBACK TO SAVEPOINT statements since those are artifacts of the
    nested-transaction test isolation pattern.

    Args:
        session: The async session to monitor.
        expected: Expected number of application-level SQL queries.
        label: Optional label for the assertion error message.

    Raises:
        AssertionError: If the actual query count does not match expected.

    Usage::

        async with assert_query_count(db_session, expected=1, label="list_brands"):
            result = await brand_repo.list_all()
    """
    counter: dict[str, int] = {"count": 0}

    def _count_queries(
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        """SQLAlchemy after_cursor_execute event listener.

        Increments counter for application queries, skipping SAVEPOINT-related
        statements that are test isolation artifacts.
        """
        stmt_upper = statement.strip().upper()
        if stmt_upper.startswith(
            ("SAVEPOINT", "RELEASE SAVEPOINT", "ROLLBACK TO SAVEPOINT")
        ):
            return
        counter["count"] += 1

    # Get the underlying sync connection for event attachment
    async_conn = await session.connection()
    raw_conn = async_conn.sync_connection

    event.listen(raw_conn, "after_cursor_execute", _count_queries)
    try:
        yield
    finally:
        event.remove(raw_conn, "after_cursor_execute", _count_queries)

    label_str = f" ({label})" if label else ""
    assert counter["count"] == expected, (
        f"Expected {expected} queries{label_str}, got {counter['count']}"
    )
