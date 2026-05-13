"""Query: list orders for an identity, keyset paginated by created_at desc."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.order.application.queries.get_order import _to_customer_read_model
from src.modules.order.application.queries.read_models import CustomerOrderListPage
from src.modules.order.infrastructure.models import OrderModel


@dataclass(frozen=True)
class ListMyOrdersQuery:
    identity_id: uuid.UUID
    limit: int = 20
    cursor: datetime | None = None


class ListMyOrdersHandler:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: ListMyOrdersQuery) -> CustomerOrderListPage:
        limit = max(1, min(query.limit, 100))
        stmt = (
            select(OrderModel)
            .where(OrderModel.identity_id == query.identity_id)
            .options(selectinload(OrderModel.items))
            .order_by(OrderModel.created_at.desc(), OrderModel.id.desc())
            .limit(limit + 1)
        )
        if query.cursor is not None:
            stmt = stmt.where(OrderModel.created_at < query.cursor)
        rows = list((await self._session.execute(stmt)).scalars().all())
        has_more = len(rows) > limit
        rows = rows[:limit]
        items = [_to_customer_read_model(r) for r in rows]
        next_cursor = items[-1].created_at if has_more and items else None
        return CustomerOrderListPage(items=items, next_cursor=next_cursor)
