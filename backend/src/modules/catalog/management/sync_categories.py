"""Idempotent sync of seed categories.

Uses ``INSERT ... ON CONFLICT`` on the unique constraint
``(parent_id, slug)`` so it is safe to run on every deploy.

Usage:
    # Standalone
    python -m src.modules.catalog.management.sync_categories

    # Called from application lifespan
    await sync_categories(session_factory)
"""

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = structlog.get_logger(__name__)

# Root categories: ON CONFLICT (parent_id, slug) where parent_id IS NULL
# Uses the partial unique index uix_categories_slug (postgresql_nulls_not_distinct)
_UPSERT_ROOT = text("""
    INSERT INTO categories (parent_id, name, slug, full_slug, level, sort_order)
    VALUES (NULL, :name, :slug, :full_slug, :level, :sort_order)
    ON CONFLICT (parent_id, slug) DO UPDATE SET
        name       = EXCLUDED.name,
        full_slug  = EXCLUDED.full_slug,
        sort_order = EXCLUDED.sort_order
    RETURNING id
""")

# Child categories: need parent_id resolved first
_UPSERT_CHILD = text("""
    INSERT INTO categories (parent_id, name, slug, full_slug, level, sort_order)
    VALUES (:parent_id, :name, :slug, :full_slug, :level, :sort_order)
    ON CONFLICT (parent_id, slug) DO UPDATE SET
        name       = EXCLUDED.name,
        full_slug  = EXCLUDED.full_slug,
        sort_order = EXCLUDED.sort_order
    RETURNING id
""")

_FIND_ROOT = text("""
    SELECT id FROM categories WHERE parent_id IS NULL AND slug = :slug
""")

# ---------------------------------------------------------------------------
# Seed data — no hardcoded UUIDs, resolved at insert time
# ---------------------------------------------------------------------------

SEED: list[dict] = [
    # ── Одежда ────────────────────────────────────────────────────────────
    {
        "slug": "clothing",
        "name": "Одежда",
        "children": [
            {"slug": "tees", "name": "Футболки"},
            {"slug": "hoodies", "name": "Худи"},
            {"slug": "zip-hoodies", "name": "Зип-худи"},
            {"slug": "jeans", "name": "Джинсы"},
            {"slug": "pants", "name": "Штаны"},
            {"slug": "shorts", "name": "Шорты"},
            {"slug": "tank-tops", "name": "Майки"},
            {"slug": "long-sleeves", "name": "Лонгсливы"},
            {"slug": "sweatshirts", "name": "Свитшоты"},
            {"slug": "sweaters", "name": "Свитеры"},
            {"slug": "shirts", "name": "Рубашки"},
            {"slug": "windbreakers", "name": "Ветровки"},
            {"slug": "bomber-jackets", "name": "Бомберы"},
            {"slug": "jackets", "name": "Куртки"},
            {"slug": "puffers", "name": "Пуховики"},
            {"slug": "vests", "name": "Жилеты"},
            {"slug": "socks", "name": "Носки"},
            {"slug": "underwear", "name": "Нижнее бельё"},
        ],
    },
    # ── Обувь ─────────────────────────────────────────────────────────────
    {
        "slug": "footwear",
        "name": "Обувь",
        "children": [
            {"slug": "sneakers", "name": "Кроссовки"},
            {"slug": "canvas-shoes", "name": "Кеды"},
            {"slug": "dress-shoes", "name": "Туфли"},
            {"slug": "slides", "name": "Шлепанцы"},
            {"slug": "boots", "name": "Ботинки"},
        ],
    },
    # ── Аксессуары ────────────────────────────────────────────────────────
    {
        "slug": "accessories",
        "name": "Аксессуары",
        "children": [
            {"slug": "bags", "name": "Сумки"},
            {"slug": "watches", "name": "Часы"},
            {"slug": "jewelry", "name": "Украшения"},
            {"slug": "backpacks", "name": "Рюкзаки"},
            {"slug": "belts", "name": "Ремни"},
            {"slug": "caps", "name": "Кепки"},
            {"slug": "beanies", "name": "Шапки"},
            {"slug": "eyewear", "name": "Очки"},
            {"slug": "wallets", "name": "Кошельки"},
        ],
    },
]


async def sync_categories(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Upsert all seed categories. Idempotent — safe to run on every deploy."""
    total = 0

    async with session_factory() as session, session.begin():
        for root_sort, root in enumerate(SEED, start=1):
            # Upsert root category
            result = await session.execute(
                _UPSERT_ROOT,
                {
                    "name": root["name"],
                    "slug": root["slug"],
                    "full_slug": root["slug"],
                    "level": 0,
                    "sort_order": root_sort,
                },
            )
            parent_id = result.scalar_one()
            total += 1

            # Upsert children
            for child_sort, child in enumerate(root.get("children", []), start=1):
                await session.execute(
                    _UPSERT_CHILD,
                    {
                        "parent_id": parent_id,
                        "name": child["name"],
                        "slug": child["slug"],
                        "full_slug": f"{root['slug']}/{child['slug']}",
                        "level": 1,
                        "sort_order": child_sort,
                    },
                )
                total += 1

    logger.info("categories.synced", count=total)


# ---------------------------------------------------------------------------
# Standalone: python -m src.modules.catalog.management.sync_categories
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.bootstrap.container import create_container
    from src.bootstrap.logger import setup_logging

    setup_logging()

    async def main() -> None:
        container = create_container()
        async with container() as app_scope:
            factory = await app_scope.get(async_sessionmaker[AsyncSession])
            await sync_categories(factory)
        await container.close()

    asyncio.run(main())
