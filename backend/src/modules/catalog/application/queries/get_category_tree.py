# src/modules/catalog/application/queries/get_category_tree.py
"""
Query handler: full category tree.

Strict CQRS read side — does not use IUnitOfWork, domain aggregates, or
repositories. Queries the ORM directly via AsyncSession, assembles the
tree in-memory, and caches the result in Redis for 5 minutes.
"""

import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.constants import (
    CATEGORY_TREE_CACHE_KEY,
    CATEGORY_TREE_CACHE_TTL_SECONDS,
)
from src.modules.catalog.application.queries.read_models import CategoryNode
from src.modules.catalog.infrastructure.models import Category as OrmCategory
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger


class GetCategoryTreeHandler:
    """Fetch the full category tree as nested CategoryNode objects."""

    def __init__(self, session: AsyncSession, cache: ICacheService, logger: ILogger):
        self._session = session
        self._cache = cache
        self._logger = logger.bind(handler="GetCategoryTreeHandler")

    async def handle(self, *, max_depth: int | None = None) -> list[CategoryNode]:
        """Retrieve the category tree, using Redis cache when available.

        Args:
            max_depth: If provided, prune the tree so that only nodes up to
                this depth are included.  A value of 1 returns only root
                categories, 2 returns roots and their direct children, etc.

        Returns:
            List of root ``CategoryNode`` objects with nested children.
        """
        cached_data = await self._cache.get(CATEGORY_TREE_CACHE_KEY)
        if cached_data:
            roots = [CategoryNode.model_validate(c) for c in json.loads(cached_data)]
            if max_depth is not None:
                _prune_tree(roots, current_depth=1, max_depth=max_depth)
            return roots

        stmt = select(OrmCategory).order_by(OrmCategory.level, OrmCategory.sort_order)
        result = await self._session.execute(stmt)
        rows = result.scalars().all()

        nodes_map: dict[uuid.UUID, CategoryNode] = {}
        for orm in rows:
            node = CategoryNode(
                id=orm.id,
                name=orm.name,
                slug=orm.slug,
                full_slug=orm.full_slug,
                level=orm.level,
                sort_order=orm.sort_order,
                parent_id=orm.parent_id,
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
        await self._cache.set(
            CATEGORY_TREE_CACHE_KEY,
            json.dumps(cache_payload),
            ttl=CATEGORY_TREE_CACHE_TTL_SECONDS,
        )

        if max_depth is not None:
            _prune_tree(roots, current_depth=1, max_depth=max_depth)

        return roots


def _prune_tree(nodes: list[CategoryNode], *, current_depth: int, max_depth: int) -> None:
    """Recursively delete children beyond *max_depth*.

    Depth 1 means only the nodes in *nodes* are kept (their children are
    cleared).  Depth 2 keeps one level of children, and so on.
    """
    if current_depth >= max_depth:
        for node in nodes:
            node.children = []
    else:
        for node in nodes:
            _prune_tree(node.children, current_depth=current_depth + 1, max_depth=max_depth)
