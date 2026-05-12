"""Generic pagination helpers for CQRS query handlers.

Provides two pagination strategies:

* :func:`paginate` — classic offset/limit with total count (admin lists).
* :func:`cursor_paginate` — keyset (cursor) pagination for infinite-scroll
  storefront listings.  Encodes the cursor as a base64-JSON token so clients
  never manipulate raw DB values.
"""

from __future__ import annotations

import base64
import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Offset pagination (existing)
# ---------------------------------------------------------------------------


async def paginate[T, R](
    session: AsyncSession,
    base_query: Select,
    *,
    offset: int,
    limit: int,
    mapper: Callable[[T], R],
) -> tuple[list[R], int]:
    """Execute a paginated query and return (items, total).

    Args:
        session: SQLAlchemy async session.
        base_query: Base SELECT statement (with filters and order_by applied,
            WITHOUT offset/limit).
        offset: Number of records to skip.
        limit: Maximum number of records to return.
        mapper: Function to convert each ORM row to a read model.

    Returns:
        Tuple of (mapped items, total count).
    """
    count_stmt = select(func.count()).select_from(base_query.subquery())
    total: int = (await session.execute(count_stmt)).scalar_one()

    items_stmt = base_query.offset(offset).limit(limit)
    rows = (await session.execute(items_stmt)).scalars().all()

    items = [mapper(row) for row in rows]
    return items, total


# ---------------------------------------------------------------------------
# Cursor (keyset) pagination
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CursorPage[T]:
    """Result of a cursor-paginated query."""

    items: list[T]
    has_next: bool
    next_cursor: str | None = None
    total: int | None = None


def encode_cursor(sort_value: Any, row_id: uuid.UUID) -> str:
    """Encode a keyset position as an opaque base64 token."""
    payload = {"s": _serialize_value(sort_value), "i": str(row_id)}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def decode_cursor(cursor: str) -> tuple[Any, uuid.UUID]:
    """Decode an opaque cursor token back to (sort_value, row_id).

    Raises:
        ValueError: If the cursor is malformed or tampered with.
    """
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        return payload["s"], uuid.UUID(payload["i"])
    except Exception as exc:
        msg = "Invalid cursor token"
        raise ValueError(msg) from exc


def _serialize_value(val: Any) -> Any:
    """Convert non-JSON-native types for cursor serialization."""
    if isinstance(val, uuid.UUID):
        return str(val)
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return val


@dataclass
class CursorPaginationSpec:
    """Defines how to cursor-paginate a query.

    Attributes:
        sort_columns: List of (column, descending) tuples defining the
            multi-column sort.  The *last* entry MUST be a unique tiebreaker
            (typically the primary key).
        limit: Maximum items per page.
        cursor: Opaque cursor from a previous page (None for the first page).
        include_total: Whether to execute a COUNT query for the total.
    """

    sort_columns: list[tuple[Any, bool]] = field(default_factory=list)
    limit: int = 24
    cursor: str | None = None
    include_total: bool = False


async def cursor_paginate[T, R](
    session: AsyncSession,
    base_query: Select,
    *,
    spec: CursorPaginationSpec,
    mapper: Callable[[T], R],
    sort_value_getter: Callable[[T], Any],
    id_getter: Callable[[T], uuid.UUID],
    scalar: bool = True,
) -> CursorPage[R]:
    """Execute a cursor-paginated query and return a :class:`CursorPage`.

    The function fetches ``limit + 1`` rows to detect whether a next page
    exists, returning at most ``limit`` mapped items.

    ``base_query`` MUST already have ``ORDER BY`` applied matching
    ``spec.sort_columns``.  This function only adds the keyset WHERE
    clause and LIMIT.

    Args:
        session: SQLAlchemy async session.
        base_query: SELECT with filters and ORDER BY, without LIMIT.
        spec: Cursor pagination parameters.
        mapper: Converts a row to a read model.
        sort_value_getter: Extracts the primary sort value from a row
            (used to encode the next cursor).
        id_getter: Extracts the unique ID from a row (cursor tiebreaker).
        scalar: If True, use ``.scalars()`` (single-entity select).
            If False, use ``.all()`` (multi-column composite select).

    Returns:
        A :class:`CursorPage` with mapped items and navigation metadata.
    """
    stmt = base_query

    # Apply keyset WHERE clause if a cursor was provided.
    if spec.cursor:
        cursor_sort_val, cursor_id = decode_cursor(spec.cursor)
        sort_col, desc = spec.sort_columns[0]
        pk_col = spec.sort_columns[-1][0]

        if desc:
            stmt = stmt.where(
                (sort_col < cursor_sort_val)
                | ((sort_col == cursor_sort_val) & (pk_col < cursor_id))
            )
        else:
            stmt = stmt.where(
                (sort_col > cursor_sort_val)
                | ((sort_col == cursor_sort_val) & (pk_col > cursor_id))
            )

    # Fetch limit + 1 to detect has_next.
    stmt = stmt.limit(spec.limit + 1)
    result = await session.execute(stmt)
    rows = list(result.scalars().all()) if scalar else list(result.all())

    has_next = len(rows) > spec.limit
    rows = rows[: spec.limit]

    items = [mapper(row) for row in rows]

    next_cursor: str | None = None
    if has_next and rows:
        last = rows[-1]
        next_cursor = encode_cursor(sort_value_getter(last), id_getter(last))

    total: int | None = None
    if spec.include_total:
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total = (await session.execute(count_stmt)).scalar_one()

    return CursorPage(
        items=items,
        has_next=has_next,
        next_cursor=next_cursor,
        total=total,
    )
