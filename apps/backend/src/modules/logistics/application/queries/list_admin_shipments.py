"""Admin query: list shipments with filters + cursor pagination (LOG-003).

CQRS read-side — reads ``shipments`` ORM directly without traversing
the domain repository (whitelisted by ``test_boundaries`` Rule 3 for
``*.application.queries.*``). Mirrors the cursor pagination pattern
used by ``AdminListOrdersHandler``: order by ``created_at DESC, id DESC``,
fetch ``limit + 1`` rows to detect ``next_cursor``.

Filters are all optional and combinable (AND semantics). The handler
itself enforces the page-size cap; ``ProviderCode`` /
``ShipmentStatus`` validation lives in the presentation layer (Pydantic
enums) so an invalid value surfaces as 422 instead of an empty result.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.logistics.application.queries.read_models import (
    AdminShipmentListPage,
    AdminShipmentSummary,
)
from src.modules.logistics.domain.value_objects import (
    ProviderCode,
    ShipmentStatus,
)
from src.modules.logistics.infrastructure.models import ShipmentModel

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200
_MIN_LIMIT = 1


@dataclass(frozen=True)
class ListAdminShipmentsQuery:
    """Filter set for the admin shipments list.

    Attributes:
        provider: Restrict to a single provider, e.g. ``"cdek"``.
        status: Restrict to a single FSM state.
        order_id: Restrict to a specific order's shipments.
        created_after: Inclusive lower bound on ``created_at``.
        created_before: Exclusive upper bound on ``created_at``
            (``< created_before``) so it composes cleanly with the
            cursor predicate.
        tracking_number_contains: Substring match (case-insensitive
            ILIKE) over ``tracking_number``. Empty string is treated
            as ``None`` to avoid full-table scans.
        limit: Page size, clamped to ``[1, 200]``; default 50.
        cursor: ``created_at`` of the last item from the previous page;
            ``None`` for the first page.
    """

    provider: ProviderCode | None = None
    status: ShipmentStatus | None = None
    order_id: uuid.UUID | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    tracking_number_contains: str | None = None
    limit: int = _DEFAULT_LIMIT
    cursor: datetime | None = None


def _to_summary(row: ShipmentModel) -> AdminShipmentSummary:
    """Map an ORM row to the read-model projection.

    ``destination_city`` is extracted from the JSONB blob — we don't
    need the full address for the list view, but the city is the
    minimal context an operator needs to scan the table. If the JSON
    payload is malformed (legacy rows seeded before ``city`` was
    required) we fall back to the empty string so the list still renders.
    """
    destination_city = ""
    raw_destination = row.destination_json
    if isinstance(raw_destination, dict):
        candidate = raw_destination.get("city")
        if isinstance(candidate, str):
            destination_city = candidate

    latest_tracking_status: str | None = None
    if row.latest_tracking_status is not None:
        # ORM column is an enum; coerce to its string value so the
        # read model stays infrastructure-agnostic. Wraps in
        # ``getattr(..., "value", ...)`` so a row that already came back
        # as a plain string (some flush paths surface enum columns this
        # way) is handled identically.
        raw_tracking: object = row.latest_tracking_status
        latest_tracking_status = str(getattr(raw_tracking, "value", raw_tracking))

    raw_status: object = row.status
    status_value: str = str(getattr(raw_status, "value", raw_status))
    raw_delivery_type: object = row.delivery_type
    delivery_type_value: str = str(
        getattr(raw_delivery_type, "value", raw_delivery_type)
    )

    return AdminShipmentSummary(
        id=row.id,
        provider_code=str(row.provider_code),
        status=status_value,
        tracking_number=row.tracking_number,
        order_id=row.order_id,
        delivery_type=delivery_type_value,
        destination_city=destination_city,
        quoted_cost_amount=row.quoted_cost_amount,
        quoted_cost_currency=row.quoted_cost_currency,
        latest_tracking_status=latest_tracking_status,
        created_at=row.created_at,
        updated_at=row.updated_at,
        booked_at=row.booked_at,
    )


class ListAdminShipmentsHandler:
    """Admin shipments list query handler.

    CQRS read-side: reads ``shipments`` directly without instantiating
    domain ``Shipment`` aggregates. Returns a page of compact
    :class:`AdminShipmentSummary` rows ordered by ``created_at DESC``.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: ListAdminShipmentsQuery) -> AdminShipmentListPage:
        limit = max(_MIN_LIMIT, min(query.limit, _MAX_LIMIT))

        stmt = (
            select(ShipmentModel)
            .order_by(ShipmentModel.created_at.desc(), ShipmentModel.id.desc())
            .limit(limit + 1)
        )

        if query.provider is not None:
            stmt = stmt.where(ShipmentModel.provider_code == query.provider)
        if query.status is not None:
            stmt = stmt.where(ShipmentModel.status == query.status.value)
        if query.order_id is not None:
            stmt = stmt.where(ShipmentModel.order_id == query.order_id)
        if query.created_after is not None:
            stmt = stmt.where(ShipmentModel.created_at >= query.created_after)
        if query.created_before is not None:
            stmt = stmt.where(ShipmentModel.created_at < query.created_before)
        if (
            query.tracking_number_contains is not None
            and query.tracking_number_contains.strip() != ""
        ):
            needle = query.tracking_number_contains.strip()
            # ILIKE-substring match. ``escape`` sanitises ``%``/``_``
            # so a customer-facing wildcard cannot smuggle a fully open
            # match through the operator console.
            escaped = (
                needle.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            )
            stmt = stmt.where(
                ShipmentModel.tracking_number.ilike(f"%{escaped}%", escape="\\")
            )
        if query.cursor is not None:
            stmt = stmt.where(ShipmentModel.created_at < query.cursor)

        result = await self._session.execute(stmt)
        rows = list(result.scalars().all())
        has_more = len(rows) > limit
        page_rows = rows[:limit]

        items = [_to_summary(cast(ShipmentModel, r)) for r in page_rows]
        next_cursor = items[-1].created_at if has_more and items else None
        return AdminShipmentListPage(items=items, next_cursor=next_cursor)
