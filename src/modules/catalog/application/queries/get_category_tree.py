# src/modules/catalog/application/queries/get_category_tree.py
"""
Query handler: full category tree.

Strict CQRS read side — does not use IUnitOfWork, domain aggregates, or
repositories. Queries the database directly via AsyncSession + raw SQL,
assembles the tree in-memory, and caches the result in Redis for 5 minutes.
"""

import json
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.constants import CATEGORY_TREE_CACHE_KEY
from src.modules.catalog.application.queries.read_models import CategoryNode
from src.shared.interfaces.cache import ICacheService

_CATEGORY_TREE_SQL = text(
    "SELECT id, name, slug, full_slug, level, sort_order, parent_id "
    "FROM categories "
    "ORDER BY level, sort_order"
)


class GetCategoryTreeHandler:
    """Fetch the full category tree as nested CategoryNode objects."""

    def __init__(self, session: AsyncSession, cache: ICacheService):
        self._session = session
        self._cache = cache

    async def handle(self) -> list[CategoryNode]:
        """Retrieve the category tree, using Redis cache when available.

        Returns:
            List of root ``CategoryNode`` objects with nested children.
        """
        cached_data = await self._cache.get(CATEGORY_TREE_CACHE_KEY)
        if cached_data:
            return [CategoryNode.model_validate(c) for c in json.loads(cached_data)]

        result = await self._session.execute(_CATEGORY_TREE_SQL)
        rows = result.mappings().all()

        nodes_map: dict[uuid.UUID, CategoryNode] = {}
        for row in rows:
            node = CategoryNode(
                id=row["id"],
                name=row["name"],
                slug=row["slug"],
                full_slug=row["full_slug"],
                level=row["level"],
                sort_order=row["sort_order"],
                parent_id=row["parent_id"],
            )
            nodes_map[node.id] = node

        roots: list[CategoryNode] = []
        for node in nodes_map.values():
            if node.parent_id is None:
                roots.append(node)
            else:
                parent = nodes_map.get(node.parent_id)
                if parent is not None:
                    parent.children.append(node)

        cache_payload = [n.model_dump(mode="json") for n in roots]
        await self._cache.set(CATEGORY_TREE_CACHE_KEY, json.dumps(cache_payload), ttl=300)

        return roots
