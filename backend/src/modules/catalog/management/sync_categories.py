"""Idempotent sync of seed categories.

Uses ``INSERT ... ON CONFLICT`` on the unique constraint
``(parent_id, slug)`` so it is safe to run on every deploy.

Usage:
    # Standalone
    python -m src.modules.catalog.management.sync_categories

    # Called from application lifespan
    await sync_categories(session_factory)
"""

import json

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = structlog.get_logger(__name__)

_UPSERT_ROOT = text("""
    INSERT INTO categories (parent_id, name_i18n, slug, full_slug, level, sort_order)
    VALUES (NULL, cast(:name_i18n AS jsonb), :slug, :full_slug, :level, :sort_order)
    ON CONFLICT (parent_id, slug) DO UPDATE SET
        name_i18n  = EXCLUDED.name_i18n,
        full_slug  = EXCLUDED.full_slug,
        sort_order = EXCLUDED.sort_order
    RETURNING id
""")

_UPSERT_CHILD = text("""
    INSERT INTO categories (parent_id, name_i18n, slug, full_slug, level, sort_order)
    VALUES (:parent_id, cast(:name_i18n AS jsonb), :slug, :full_slug, :level, :sort_order)
    ON CONFLICT (parent_id, slug) DO UPDATE SET
        name_i18n  = EXCLUDED.name_i18n,
        full_slug  = EXCLUDED.full_slug,
        sort_order = EXCLUDED.sort_order
    RETURNING id
""")

# ---------------------------------------------------------------------------
# Seed data — no hardcoded UUIDs, resolved at insert time
# ---------------------------------------------------------------------------

SEED: list[dict] = [
    # ── Одежда ────────────────────────────────────────────────────────────
    {
        "slug": "clothing",
        "name_i18n": {"ru": "Одежда", "en": "Clothing"},
        "children": [
            {"slug": "tees", "name_i18n": {"ru": "Футболки", "en": "T-Shirts"}},
            {"slug": "hoodies", "name_i18n": {"ru": "Худи", "en": "Hoodies"}},
            {"slug": "zip-hoodies", "name_i18n": {"ru": "Зип-худи", "en": "Zip Hoodies"}},
            {"slug": "jeans", "name_i18n": {"ru": "Джинсы", "en": "Jeans"}},
            {"slug": "pants", "name_i18n": {"ru": "Штаны", "en": "Pants"}},
            {"slug": "shorts", "name_i18n": {"ru": "Шорты", "en": "Shorts"}},
            {"slug": "tank-tops", "name_i18n": {"ru": "Майки", "en": "Tank Tops"}},
            {"slug": "long-sleeves", "name_i18n": {"ru": "Лонгсливы", "en": "Long Sleeves"}},
            {"slug": "sweatshirts", "name_i18n": {"ru": "Свитшоты", "en": "Sweatshirts"}},
            {"slug": "sweaters", "name_i18n": {"ru": "Свитеры", "en": "Sweaters"}},
            {"slug": "shirts", "name_i18n": {"ru": "Рубашки", "en": "Shirts"}},
            {"slug": "windbreakers", "name_i18n": {"ru": "Ветровки", "en": "Windbreakers"}},
            {"slug": "bomber-jackets", "name_i18n": {"ru": "Бомберы", "en": "Bomber Jackets"}},
            {"slug": "jackets", "name_i18n": {"ru": "Куртки", "en": "Jackets"}},
            {"slug": "puffers", "name_i18n": {"ru": "Пуховики", "en": "Puffer Jackets"}},
            {"slug": "vests", "name_i18n": {"ru": "Жилеты", "en": "Vests"}},
            {"slug": "socks", "name_i18n": {"ru": "Носки", "en": "Socks"}},
            {"slug": "underwear", "name_i18n": {"ru": "Нижнее бельё", "en": "Underwear"}},
        ],
    },
    # ── Обувь ─────────────────────────────────────────────────────────────
    {
        "slug": "footwear",
        "name_i18n": {"ru": "Обувь", "en": "Footwear"},
        "children": [
            {"slug": "sneakers", "name_i18n": {"ru": "Кроссовки", "en": "Sneakers"}},
            {"slug": "canvas-shoes", "name_i18n": {"ru": "Кеды", "en": "Canvas Shoes"}},
            {"slug": "dress-shoes", "name_i18n": {"ru": "Туфли", "en": "Dress Shoes"}},
            {"slug": "slides", "name_i18n": {"ru": "Шлепанцы", "en": "Slides"}},
            {"slug": "boots", "name_i18n": {"ru": "Ботинки", "en": "Boots"}},
        ],
    },
    # ── Аксессуары ────────────────────────────────────────────────────────
    {
        "slug": "accessories",
        "name_i18n": {"ru": "Аксессуары", "en": "Accessories"},
        "children": [
            {"slug": "bags", "name_i18n": {"ru": "Сумки", "en": "Bags"}},
            {"slug": "watches", "name_i18n": {"ru": "Часы", "en": "Watches"}},
            {"slug": "jewelry", "name_i18n": {"ru": "Украшения", "en": "Jewelry"}},
            {"slug": "backpacks", "name_i18n": {"ru": "Рюкзаки", "en": "Backpacks"}},
            {"slug": "belts", "name_i18n": {"ru": "Ремни", "en": "Belts"}},
            {"slug": "caps", "name_i18n": {"ru": "Кепки", "en": "Caps"}},
            {"slug": "beanies", "name_i18n": {"ru": "Шапки", "en": "Beanies"}},
            {"slug": "eyewear", "name_i18n": {"ru": "Очки", "en": "Eyewear"}},
            {"slug": "wallets", "name_i18n": {"ru": "Кошельки", "en": "Wallets"}},
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
            result = await session.execute(
                _UPSERT_ROOT,
                {
                    "name_i18n": json.dumps(root["name_i18n"], ensure_ascii=False),
                    "slug": root["slug"],
                    "full_slug": root["slug"],
                    "level": 0,
                    "sort_order": root_sort,
                },
            )
            parent_id = result.scalar_one()
            total += 1

            for child_sort, child in enumerate(root.get("children", []), start=1):
                await session.execute(
                    _UPSERT_CHILD,
                    {
                        "parent_id": parent_id,
                        "name_i18n": json.dumps(child["name_i18n"], ensure_ascii=False),
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
