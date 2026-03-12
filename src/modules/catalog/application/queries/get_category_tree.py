# src/modules/catalog/application/queries/get_category_tree.py
import json
from typing import Any

from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.infrastructure.models import Category
from src.modules.catalog.presentation.schemas import CategoryTreeResponse
from src.shared.interfaces.cache import ICacheService

CACHE_KEY = "catalog:category_tree"


TreeAdapter = TypeAdapter(list[CategoryTreeResponse])


class GetCategoryTreeHandler:
    def __init__(self, session: AsyncSession, cache: ICacheService):
        self._session = session
        self._cache = cache

    async def handle(self) -> list[dict[str, Any]]:
        cached_data = await self._cache.get(CACHE_KEY)
        if cached_data:
            return json.loads(cached_data)

        stmt = select(
            Category.id,
            Category.name,
            Category.slug,
            Category.full_slug,
            Category.level,
            Category.sort_order,
            Category.parent_id,
        ).order_by(Category.level, Category.sort_order)

        result = await self._session.execute(stmt)
        rows = result.mappings().all()

        categories_map = {}
        for row in rows:
            cat_dict = dict(row)
            cat_dict["children"] = []
            categories_map[cat_dict["id"]] = cat_dict

        roots = []
        for cat_dict in categories_map.values():
            if cat_dict["parent_id"] is None:
                roots.append(cat_dict)
            else:
                parent = categories_map.get(cat_dict["parent_id"])
                if parent is not None:
                    parent["children"].append(cat_dict)

        tree_dicts = TreeAdapter.dump_python(roots, mode="json")

        await self._cache.set(CACHE_KEY, json.dumps(tree_dicts))

        return tree_dicts
