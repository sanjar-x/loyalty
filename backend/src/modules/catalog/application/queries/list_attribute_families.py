"""
Query handler: paginated attribute family listing.

Strict CQRS read side -- does not use IUnitOfWork, domain aggregates, or
repositories. Queries the ORM directly via AsyncSession and returns
Pydantic read models.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.queries.read_models import (
    AttributeFamilyListReadModel,
    AttributeFamilyReadModel,
    AttributeFamilyTreeNode,
)
from src.modules.catalog.domain.exceptions import AttributeFamilyNotFoundError
from src.modules.catalog.infrastructure.models import (
    AttributeFamily as OrmAttributeFamily,
)
from src.shared.interfaces.logger import ILogger
from src.shared.pagination import paginate

# ---------------------------------------------------------------------------
# ORM -> Read Model converter
# ---------------------------------------------------------------------------


def family_orm_to_read_model(orm: OrmAttributeFamily) -> AttributeFamilyReadModel:
    """Convert an ORM AttributeFamily to an AttributeFamilyReadModel."""
    return AttributeFamilyReadModel(
        id=orm.id,
        parent_id=orm.parent_id,
        code=orm.code,
        name_i18n=orm.name_i18n or {},
        description_i18n=orm.description_i18n or {},
        sort_order=orm.sort_order,
        level=orm.level,
    )


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ListAttributeFamiliesQuery:
    """Pagination parameters for attribute family listing.

    Attributes:
        offset: Number of records to skip.
        limit: Maximum number of records to return.
    """

    offset: int = 0
    limit: int = 50


@dataclass(frozen=True)
class GetAttributeFamilyQuery:
    """Query to retrieve a single attribute family by ID.

    Attributes:
        family_id: UUID of the family to retrieve.
    """

    family_id: uuid.UUID


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


class ListAttributeFamiliesHandler:
    """Fetch a paginated list of attribute families."""

    def __init__(self, session: AsyncSession, logger: ILogger):
        self._session = session
        self._logger = logger.bind(handler="ListAttributeFamiliesHandler")

    async def handle(
        self, query: ListAttributeFamiliesQuery
    ) -> AttributeFamilyListReadModel:
        """Retrieve a paginated attribute family list.

        Args:
            query: Pagination parameters.

        Returns:
            Paginated list read model with items and total count.
        """
        base = select(OrmAttributeFamily).order_by(
            OrmAttributeFamily.level,
            OrmAttributeFamily.sort_order,
            OrmAttributeFamily.code,
        )

        items, total = await paginate(
            self._session,
            base,
            offset=query.offset,
            limit=query.limit,
            mapper=family_orm_to_read_model,
        )

        return AttributeFamilyListReadModel(
            items=items,
            total=total,
            offset=query.offset,
            limit=query.limit,
        )


class GetAttributeFamilyHandler:
    """Fetch a single attribute family by its UUID."""

    def __init__(self, session: AsyncSession, logger: ILogger):
        self._session = session
        self._logger = logger.bind(handler="GetAttributeFamilyHandler")

    async def handle(self, query: GetAttributeFamilyQuery) -> AttributeFamilyReadModel:
        """Retrieve an attribute family read model.

        Args:
            query: Contains the UUID of the family to retrieve.

        Returns:
            Attribute family read model with current state.

        Raises:
            AttributeFamilyNotFoundError: If no family with this ID exists.
        """
        stmt = select(OrmAttributeFamily).where(
            OrmAttributeFamily.id == query.family_id
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None:
            raise AttributeFamilyNotFoundError(family_id=query.family_id)

        return family_orm_to_read_model(orm)


class GetAttributeFamilyTreeHandler:
    """Fetch the full attribute family tree as nested tree nodes."""

    def __init__(self, session: AsyncSession, logger: ILogger):
        self._session = session
        self._logger = logger.bind(handler="GetAttributeFamilyTreeHandler")

    async def handle(self) -> list[AttributeFamilyTreeNode]:
        """Retrieve the attribute family tree.

        Loads all families ordered by level and sort_order, then assembles
        the tree in-memory. Because rows are ordered by level ASC, every
        parent is guaranteed to appear before its children.

        Returns:
            List of root ``AttributeFamilyTreeNode`` objects with nested children.
        """
        stmt = select(OrmAttributeFamily).order_by(
            OrmAttributeFamily.level, OrmAttributeFamily.sort_order
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        nodes_map: dict[uuid.UUID, AttributeFamilyTreeNode] = {}
        roots: list[AttributeFamilyTreeNode] = []

        for orm in rows:
            node = AttributeFamilyTreeNode(
                id=orm.id,
                code=orm.code,
                name_i18n=orm.name_i18n or {},
                level=orm.level,
                sort_order=orm.sort_order,
            )
            nodes_map[node.id] = node

            if orm.parent_id is None:
                roots.append(node)
            else:
                parent = nodes_map.get(orm.parent_id)
                if parent is not None:
                    parent.children.append(node)

        return roots
