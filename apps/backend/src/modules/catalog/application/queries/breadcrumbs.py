"""
Breadcrumb builder for storefront category navigation.

Traverses the cached category tree to build a root→leaf breadcrumb
chain for a given category.  Reuses the Redis-cached tree from
:class:`GetCategoryTreeHandler` so no additional DB round-trip is needed.
"""

from __future__ import annotations

import uuid

from src.modules.catalog.application.queries.get_category_tree import (
    GetCategoryTreeHandler,
)
from src.modules.catalog.application.queries.read_models import (
    BreadcrumbItemReadModel,
    CategoryNode,
)
from src.shared.interfaces.logger import ILogger


class BreadcrumbsBuilder:
    """Build a breadcrumb trail for a category using the cached tree."""

    def __init__(self, tree_handler: GetCategoryTreeHandler, logger: ILogger) -> None:
        self._tree_handler = tree_handler
        self._logger = logger.bind(handler="BreadcrumbsBuilder")

    async def build(self, category_id: uuid.UUID) -> list[BreadcrumbItemReadModel]:
        """Return breadcrumbs from root to the target category (inclusive).

        If the category is not found in the tree, returns an empty list.
        """
        roots = await self._tree_handler.handle()
        path: list[CategoryNode] = []
        if not _find_path(roots, category_id, path):
            self._logger.warning(
                "category_not_found_in_tree",
                category_id=str(category_id),
            )
            return []

        return [
            BreadcrumbItemReadModel(
                label_i18n=node.name_i18n,
                slug=node.slug,
                full_slug=node.full_slug,
            )
            for node in path
        ]


def _find_path(
    nodes: list[CategoryNode],
    target_id: uuid.UUID,
    path: list[CategoryNode],
) -> bool:
    """DFS to find the target category and record the ancestor path."""
    for node in nodes:
        path.append(node)
        if node.id == target_id:
            return True
        if _find_path(node.children, target_id, path):
            return True
        path.pop()
    return False
