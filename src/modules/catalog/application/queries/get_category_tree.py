# src/modules/catalog/application/queries/get_category_tree.py
import json
from typing import Any

from pydantic import TypeAdapter

from src.modules.catalog.domain.interfaces import ICategoryRepository
from src.modules.catalog.presentation.schemas import CategoryTreeResponse
from src.shared.interfaces.cache import ICacheService

CACHE_KEY = "catalog:category_tree"


TreeAdapter = TypeAdapter(list[CategoryTreeResponse])


class GetCategoryTreeHandler:
    def __init__(self, category_repo: ICategoryRepository, cache: ICacheService):
        self._category_repo = category_repo
        self._cache = cache

    async def handle(self) -> list[dict[str, Any]]:
        cached_data = await self._cache.get(CACHE_KEY)
        if cached_data:
            return json.loads(cached_data)

        categories = await self._category_repo.get_all_ordered()
        categories_map = {category.id: category for category in categories}

        for category in categories:
            category.__dict__["children"] = []

        roots = []
        for category in categories:
            if category.parent_id is None:
                roots.append(category)
            else:
                parent = categories_map.get(category.parent_id)
                if parent is not None:
                    parent.children.append(category)

        tree_dicts = TreeAdapter.dump_python(roots, mode="json")

        await self._cache.set(CACHE_KEY, json.dumps(tree_dicts))

        return tree_dicts
