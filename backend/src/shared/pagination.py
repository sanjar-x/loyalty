"""Generic pagination helper for CQRS query handlers.

Eliminates the count + offset + limit + map boilerplate that is
repeated across every list query handler.
"""

from collections.abc import Callable

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession


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
