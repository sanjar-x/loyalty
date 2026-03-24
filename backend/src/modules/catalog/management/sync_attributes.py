"""Idempotent sync of seed attribute groups, attributes, and attribute values.

Uses ``INSERT ... ON CONFLICT DO UPDATE`` so it is safe to run
on every deploy.  Seed data is tailored for a streetwear / fashion catalog.

Usage:
    # Standalone
    python -m src.modules.catalog.management.sync_attributes

    # Called from application lifespan
    await sync_attributes(session_factory)
"""

import json
import uuid

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# SQL statements
# ---------------------------------------------------------------------------

_UPSERT_GROUP = text("""
    INSERT INTO attribute_groups (id, code, name_i18n, sort_order)
    VALUES (:id, :code, cast(:name_i18n AS jsonb), :sort_order)
    ON CONFLICT (code) DO UPDATE SET
        name_i18n  = EXCLUDED.name_i18n,
        sort_order = EXCLUDED.sort_order
    RETURNING id
""")

_UPSERT_ATTRIBUTE = text("""
    INSERT INTO attributes (
        id, code, slug, group_id, name_i18n, description_i18n,
        data_type, ui_type, is_dictionary, level,
        is_filterable, is_searchable, search_weight,
        is_comparable, is_visible_on_card, is_visible_in_catalog,
        validation_rules
    )
    VALUES (
        :id, :code, :slug, :group_id, cast(:name_i18n AS jsonb), cast(:description_i18n AS jsonb),
        :data_type, :ui_type, :is_dictionary, :level,
        :is_filterable, :is_searchable, :search_weight,
        :is_comparable, :is_visible_on_card, :is_visible_in_catalog,
        cast(:validation_rules AS jsonb)
    )
    ON CONFLICT (code) DO UPDATE SET
        slug                  = EXCLUDED.slug,
        group_id              = EXCLUDED.group_id,
        name_i18n             = EXCLUDED.name_i18n,
        description_i18n      = EXCLUDED.description_i18n,
        data_type             = EXCLUDED.data_type,
        ui_type               = EXCLUDED.ui_type,
        is_dictionary         = EXCLUDED.is_dictionary,
        level                 = EXCLUDED.level,
        is_filterable         = EXCLUDED.is_filterable,
        is_searchable         = EXCLUDED.is_searchable,
        search_weight         = EXCLUDED.search_weight,
        is_comparable         = EXCLUDED.is_comparable,
        is_visible_on_card    = EXCLUDED.is_visible_on_card,
        is_visible_in_catalog = EXCLUDED.is_visible_in_catalog,
        validation_rules      = EXCLUDED.validation_rules
    RETURNING id
""")

_UPSERT_VALUE = text("""
    INSERT INTO attribute_values (
        id, attribute_id, code, slug, value_i18n, search_aliases,
        meta_data, value_group, sort_order
    )
    VALUES (
        :id, :attribute_id, :code, :slug, cast(:value_i18n AS jsonb), :search_aliases,
        cast(:meta_data AS jsonb), :value_group, :sort_order
    )
    ON CONFLICT (attribute_id, code) DO UPDATE SET
        slug           = EXCLUDED.slug,
        value_i18n     = EXCLUDED.value_i18n,
        search_aliases = EXCLUDED.search_aliases,
        meta_data      = EXCLUDED.meta_data,
        value_group    = EXCLUDED.value_group,
        sort_order     = EXCLUDED.sort_order
""")

# ---------------------------------------------------------------------------
# Seed data — streetwear / fashion starter set
# ---------------------------------------------------------------------------

SEED_GROUPS: list[dict] = [
    {
        "code": "general",
        "name_i18n": {"ru": "Основные", "en": "General"},
        "sort_order": 1,
    },
    {
        "code": "physical",
        "name_i18n": {
            "ru": "Физические характеристики",
            "en": "Physical Characteristics",
        },
        "sort_order": 2,
    },
    {
        "code": "style",
        "name_i18n": {"ru": "Стиль", "en": "Style"},
        "sort_order": 3,
    },
]

SEED_ATTRIBUTES: list[dict] = [
    # ── Variant-level (differ per SKU) ────────────────────────────────────
    {
        "code": "color",
        "slug": "color",
        "group": "physical",
        "name_i18n": {"ru": "Цвет", "en": "Color"},
        "description_i18n": {
            "ru": "Основной цвет изделия",
            "en": "Primary product color",
        },
        "data_type": "STRING",
        "ui_type": "COLOR_SWATCH",
        "is_dictionary": True,
        "level": "VARIANT",
        "is_filterable": True,
        "is_searchable": True,
        "search_weight": 7,
        "is_comparable": True,
        "is_visible_on_card": True,
        "is_visible_in_catalog": True,
        "validation_rules": None,
        "values": [
            {
                "code": "black",
                "slug": "black",
                "value_i18n": {"ru": "Чёрный", "en": "Black"},
                "search_aliases": ["чёрный", "черный"],
                "meta_data": {"hex": "#000000"},
                "value_group": "dark",
            },
            {
                "code": "white",
                "slug": "white",
                "value_i18n": {"ru": "Белый", "en": "White"},
                "search_aliases": ["белый"],
                "meta_data": {"hex": "#FFFFFF"},
                "value_group": "light",
            },
            {
                "code": "grey",
                "slug": "grey",
                "value_i18n": {"ru": "Серый", "en": "Grey"},
                "search_aliases": ["серый", "gray"],
                "meta_data": {"hex": "#808080"},
                "value_group": "neutral",
            },
            {
                "code": "navy",
                "slug": "navy",
                "value_i18n": {"ru": "Тёмно-синий", "en": "Navy"},
                "search_aliases": ["тёмно-синий", "нэви"],
                "meta_data": {"hex": "#000080"},
                "value_group": "dark",
            },
            {
                "code": "blue",
                "slug": "blue",
                "value_i18n": {"ru": "Синий", "en": "Blue"},
                "search_aliases": ["синий", "голубой"],
                "meta_data": {"hex": "#0000FF"},
                "value_group": "cool",
            },
            {
                "code": "red",
                "slug": "red",
                "value_i18n": {"ru": "Красный", "en": "Red"},
                "search_aliases": ["красный"],
                "meta_data": {"hex": "#FF0000"},
                "value_group": "warm",
            },
            {
                "code": "green",
                "slug": "green",
                "value_i18n": {"ru": "Зелёный", "en": "Green"},
                "search_aliases": ["зелёный", "зеленый"],
                "meta_data": {"hex": "#008000"},
                "value_group": "cool",
            },
            {
                "code": "beige",
                "slug": "beige",
                "value_i18n": {"ru": "Бежевый", "en": "Beige"},
                "search_aliases": ["бежевый", "беж"],
                "meta_data": {"hex": "#F5F5DC"},
                "value_group": "neutral",
            },
            {
                "code": "brown",
                "slug": "brown",
                "value_i18n": {"ru": "Коричневый", "en": "Brown"},
                "search_aliases": ["коричневый"],
                "meta_data": {"hex": "#8B4513"},
                "value_group": "neutral",
            },
            {
                "code": "pink",
                "slug": "pink",
                "value_i18n": {"ru": "Розовый", "en": "Pink"},
                "search_aliases": ["розовый"],
                "meta_data": {"hex": "#FFC0CB"},
                "value_group": "warm",
            },
            {
                "code": "orange",
                "slug": "orange",
                "value_i18n": {"ru": "Оранжевый", "en": "Orange"},
                "search_aliases": ["оранжевый"],
                "meta_data": {"hex": "#FFA500"},
                "value_group": "warm",
            },
            {
                "code": "yellow",
                "slug": "yellow",
                "value_i18n": {"ru": "Жёлтый", "en": "Yellow"},
                "search_aliases": ["жёлтый", "желтый"],
                "meta_data": {"hex": "#FFD700"},
                "value_group": "warm",
            },
            {
                "code": "purple",
                "slug": "purple",
                "value_i18n": {"ru": "Фиолетовый", "en": "Purple"},
                "search_aliases": ["фиолетовый"],
                "meta_data": {"hex": "#800080"},
                "value_group": "cool",
            },
            {
                "code": "olive",
                "slug": "olive",
                "value_i18n": {"ru": "Оливковый", "en": "Olive"},
                "search_aliases": ["оливковый", "хаки"],
                "meta_data": {"hex": "#808000"},
                "value_group": "neutral",
            },
            {
                "code": "burgundy",
                "slug": "burgundy",
                "value_i18n": {"ru": "Бордовый", "en": "Burgundy"},
                "search_aliases": ["бордовый", "бордо"],
                "meta_data": {"hex": "#800020"},
                "value_group": "dark",
            },
            {
                "code": "multicolor",
                "slug": "multicolor",
                "value_i18n": {"ru": "Мультиколор", "en": "Multicolor"},
                "search_aliases": ["мультиколор", "разноцветный"],
                "meta_data": {},
                "value_group": None,
            },
        ],
    },
    {
        "code": "size",
        "slug": "size",
        "group": "physical",
        "name_i18n": {"ru": "Размер", "en": "Size"},
        "description_i18n": {"ru": "Размер изделия", "en": "Product size"},
        "data_type": "STRING",
        "ui_type": "TEXT_BUTTON",
        "is_dictionary": True,
        "level": "VARIANT",
        "is_filterable": True,
        "is_searchable": False,
        "search_weight": 5,
        "is_comparable": False,
        "is_visible_on_card": True,
        "is_visible_in_catalog": False,
        "validation_rules": None,
        "values": [
            # Clothing sizes
            {
                "code": "xxs",
                "slug": "xxs",
                "value_i18n": {"ru": "XXS", "en": "XXS"},
                "search_aliases": [],
                "meta_data": {},
                "value_group": "clothing",
            },
            {
                "code": "xs",
                "slug": "xs",
                "value_i18n": {"ru": "XS", "en": "XS"},
                "search_aliases": [],
                "meta_data": {},
                "value_group": "clothing",
            },
            {
                "code": "s",
                "slug": "s",
                "value_i18n": {"ru": "S", "en": "S"},
                "search_aliases": [],
                "meta_data": {},
                "value_group": "clothing",
            },
            {
                "code": "m",
                "slug": "m",
                "value_i18n": {"ru": "M", "en": "M"},
                "search_aliases": [],
                "meta_data": {},
                "value_group": "clothing",
            },
            {
                "code": "l",
                "slug": "l",
                "value_i18n": {"ru": "L", "en": "L"},
                "search_aliases": [],
                "meta_data": {},
                "value_group": "clothing",
            },
            {
                "code": "xl",
                "slug": "xl",
                "value_i18n": {"ru": "XL", "en": "XL"},
                "search_aliases": [],
                "meta_data": {},
                "value_group": "clothing",
            },
            {
                "code": "xxl",
                "slug": "xxl",
                "value_i18n": {"ru": "XXL", "en": "XXL"},
                "search_aliases": [],
                "meta_data": {},
                "value_group": "clothing",
            },
            # Shoe sizes (EU)
            {
                "code": "eu-36",
                "slug": "eu-36",
                "value_i18n": {"ru": "36", "en": "36"},
                "search_aliases": ["36"],
                "meta_data": {"system": "EU"},
                "value_group": "footwear",
            },
            {
                "code": "eu-37",
                "slug": "eu-37",
                "value_i18n": {"ru": "37", "en": "37"},
                "search_aliases": ["37"],
                "meta_data": {"system": "EU"},
                "value_group": "footwear",
            },
            {
                "code": "eu-38",
                "slug": "eu-38",
                "value_i18n": {"ru": "38", "en": "38"},
                "search_aliases": ["38"],
                "meta_data": {"system": "EU"},
                "value_group": "footwear",
            },
            {
                "code": "eu-39",
                "slug": "eu-39",
                "value_i18n": {"ru": "39", "en": "39"},
                "search_aliases": ["39"],
                "meta_data": {"system": "EU"},
                "value_group": "footwear",
            },
            {
                "code": "eu-40",
                "slug": "eu-40",
                "value_i18n": {"ru": "40", "en": "40"},
                "search_aliases": ["40"],
                "meta_data": {"system": "EU"},
                "value_group": "footwear",
            },
            {
                "code": "eu-41",
                "slug": "eu-41",
                "value_i18n": {"ru": "41", "en": "41"},
                "search_aliases": ["41"],
                "meta_data": {"system": "EU"},
                "value_group": "footwear",
            },
            {
                "code": "eu-42",
                "slug": "eu-42",
                "value_i18n": {"ru": "42", "en": "42"},
                "search_aliases": ["42"],
                "meta_data": {"system": "EU"},
                "value_group": "footwear",
            },
            {
                "code": "eu-43",
                "slug": "eu-43",
                "value_i18n": {"ru": "43", "en": "43"},
                "search_aliases": ["43"],
                "meta_data": {"system": "EU"},
                "value_group": "footwear",
            },
            {
                "code": "eu-44",
                "slug": "eu-44",
                "value_i18n": {"ru": "44", "en": "44"},
                "search_aliases": ["44"],
                "meta_data": {"system": "EU"},
                "value_group": "footwear",
            },
            {
                "code": "eu-45",
                "slug": "eu-45",
                "value_i18n": {"ru": "45", "en": "45"},
                "search_aliases": ["45"],
                "meta_data": {"system": "EU"},
                "value_group": "footwear",
            },
            {
                "code": "eu-46",
                "slug": "eu-46",
                "value_i18n": {"ru": "46", "en": "46"},
                "search_aliases": ["46"],
                "meta_data": {"system": "EU"},
                "value_group": "footwear",
            },
        ],
    },
    # ── Product-level (same for all SKUs) ─────────────────────────────────
    {
        "code": "material",
        "slug": "material",
        "group": "physical",
        "name_i18n": {"ru": "Материал", "en": "Material"},
        "description_i18n": {
            "ru": "Основной материал изделия",
            "en": "Primary product material",
        },
        "data_type": "STRING",
        "ui_type": "CHECKBOX",
        "is_dictionary": True,
        "level": "PRODUCT",
        "is_filterable": True,
        "is_searchable": True,
        "search_weight": 5,
        "is_comparable": True,
        "is_visible_on_card": True,
        "is_visible_in_catalog": False,
        "validation_rules": None,
        "values": [
            {
                "code": "cotton",
                "slug": "cotton",
                "value_i18n": {"ru": "Хлопок", "en": "Cotton"},
                "search_aliases": ["хлопок", "100% хлопок"],
                "meta_data": {},
                "value_group": "natural",
            },
            {
                "code": "polyester",
                "slug": "polyester",
                "value_i18n": {"ru": "Полиэстер", "en": "Polyester"},
                "search_aliases": ["полиэстер"],
                "meta_data": {},
                "value_group": "synthetic",
            },
            {
                "code": "nylon",
                "slug": "nylon",
                "value_i18n": {"ru": "Нейлон", "en": "Nylon"},
                "search_aliases": ["нейлон"],
                "meta_data": {},
                "value_group": "synthetic",
            },
            {
                "code": "denim",
                "slug": "denim",
                "value_i18n": {"ru": "Деним", "en": "Denim"},
                "search_aliases": ["деним", "джинса"],
                "meta_data": {},
                "value_group": "natural",
            },
            {
                "code": "leather",
                "slug": "leather",
                "value_i18n": {"ru": "Кожа", "en": "Leather"},
                "search_aliases": ["кожа", "натуральная кожа"],
                "meta_data": {},
                "value_group": "natural",
            },
            {
                "code": "suede",
                "slug": "suede",
                "value_i18n": {"ru": "Замша", "en": "Suede"},
                "search_aliases": ["замша"],
                "meta_data": {},
                "value_group": "natural",
            },
            {
                "code": "fleece",
                "slug": "fleece",
                "value_i18n": {"ru": "Флис", "en": "Fleece"},
                "search_aliases": ["флис"],
                "meta_data": {},
                "value_group": "synthetic",
            },
            {
                "code": "wool",
                "slug": "wool",
                "value_i18n": {"ru": "Шерсть", "en": "Wool"},
                "search_aliases": ["шерсть"],
                "meta_data": {},
                "value_group": "natural",
            },
            {
                "code": "mesh",
                "slug": "mesh",
                "value_i18n": {"ru": "Сетка", "en": "Mesh"},
                "search_aliases": ["сетка", "меш"],
                "meta_data": {},
                "value_group": "synthetic",
            },
            {
                "code": "canvas",
                "slug": "canvas",
                "value_i18n": {"ru": "Канвас", "en": "Canvas"},
                "search_aliases": ["канвас", "парусина"],
                "meta_data": {},
                "value_group": "natural",
            },
            {
                "code": "rubber",
                "slug": "rubber",
                "value_i18n": {"ru": "Резина", "en": "Rubber"},
                "search_aliases": ["резина"],
                "meta_data": {},
                "value_group": "synthetic",
            },
        ],
    },
    {
        "code": "gender",
        "slug": "gender",
        "group": "general",
        "name_i18n": {"ru": "Пол", "en": "Gender"},
        "description_i18n": {"ru": "Целевой пол", "en": "Target gender"},
        "data_type": "STRING",
        "ui_type": "TEXT_BUTTON",
        "is_dictionary": True,
        "level": "PRODUCT",
        "is_filterable": True,
        "is_searchable": False,
        "search_weight": 5,
        "is_comparable": False,
        "is_visible_on_card": True,
        "is_visible_in_catalog": True,
        "validation_rules": None,
        "values": [
            {
                "code": "male",
                "slug": "male",
                "value_i18n": {"ru": "Мужской", "en": "Male"},
                "search_aliases": ["мужской", "муж"],
                "meta_data": {},
                "value_group": None,
            },
            {
                "code": "female",
                "slug": "female",
                "value_i18n": {"ru": "Женский", "en": "Female"},
                "search_aliases": ["женский", "жен"],
                "meta_data": {},
                "value_group": None,
            },
            {
                "code": "unisex",
                "slug": "unisex",
                "value_i18n": {"ru": "Унисекс", "en": "Unisex"},
                "search_aliases": ["унисекс"],
                "meta_data": {},
                "value_group": None,
            },
        ],
    },
    {
        "code": "season",
        "slug": "season",
        "group": "style",
        "name_i18n": {"ru": "Сезон", "en": "Season"},
        "description_i18n": {"ru": "Сезонность изделия", "en": "Product seasonality"},
        "data_type": "STRING",
        "ui_type": "CHECKBOX",
        "is_dictionary": True,
        "level": "PRODUCT",
        "is_filterable": True,
        "is_searchable": False,
        "search_weight": 5,
        "is_comparable": True,
        "is_visible_on_card": True,
        "is_visible_in_catalog": False,
        "validation_rules": None,
        "values": [
            {
                "code": "spring-summer",
                "slug": "spring-summer",
                "value_i18n": {"ru": "Весна-Лето", "en": "Spring-Summer"},
                "search_aliases": ["весна", "лето", "SS"],
                "meta_data": {},
                "value_group": None,
            },
            {
                "code": "fall-winter",
                "slug": "fall-winter",
                "value_i18n": {"ru": "Осень-Зима", "en": "Fall-Winter"},
                "search_aliases": ["осень", "зима", "FW"],
                "meta_data": {},
                "value_group": None,
            },
            {
                "code": "all-season",
                "slug": "all-season",
                "value_i18n": {"ru": "Всесезонный", "en": "All Season"},
                "search_aliases": ["всесезонный", "демисезонный"],
                "meta_data": {},
                "value_group": None,
            },
        ],
    },
    {
        "code": "style",
        "slug": "style",
        "group": "style",
        "name_i18n": {"ru": "Стиль", "en": "Style"},
        "description_i18n": {"ru": "Стилистическое направление", "en": "Fashion style"},
        "data_type": "STRING",
        "ui_type": "CHECKBOX",
        "is_dictionary": True,
        "level": "PRODUCT",
        "is_filterable": True,
        "is_searchable": True,
        "search_weight": 4,
        "is_comparable": False,
        "is_visible_on_card": True,
        "is_visible_in_catalog": False,
        "validation_rules": None,
        "values": [
            {
                "code": "streetwear",
                "slug": "streetwear",
                "value_i18n": {"ru": "Стритвир", "en": "Streetwear"},
                "search_aliases": ["стритвир", "уличный стиль"],
                "meta_data": {},
                "value_group": None,
            },
            {
                "code": "casual",
                "slug": "casual",
                "value_i18n": {"ru": "Кэжуал", "en": "Casual"},
                "search_aliases": ["кэжуал", "повседневный"],
                "meta_data": {},
                "value_group": None,
            },
            {
                "code": "sport",
                "slug": "sport",
                "value_i18n": {"ru": "Спорт", "en": "Sport"},
                "search_aliases": ["спорт", "спортивный"],
                "meta_data": {},
                "value_group": None,
            },
            {
                "code": "classic",
                "slug": "classic",
                "value_i18n": {"ru": "Классика", "en": "Classic"},
                "search_aliases": ["классика", "классический"],
                "meta_data": {},
                "value_group": None,
            },
            {
                "code": "outdoor",
                "slug": "outdoor",
                "value_i18n": {"ru": "Аутдор", "en": "Outdoor"},
                "search_aliases": ["аутдор", "для улицы", "outdoor"],
                "meta_data": {},
                "value_group": None,
            },
        ],
    },
]


# ---------------------------------------------------------------------------
# Sync logic
# ---------------------------------------------------------------------------


async def sync_attributes(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Upsert all seed attribute groups, attributes, and values.

    Idempotent — safe to run on every deploy.
    """
    group_count = 0
    attr_count = 0
    val_count = 0

    async with session_factory() as session, session.begin():
        # 1. Upsert groups and collect code -> id mapping
        group_ids: dict[str, str] = {}
        for group in SEED_GROUPS:
            result = await session.execute(
                _UPSERT_GROUP,
                {
                    "id": str(uuid.uuid7()),
                    "code": group["code"],
                    "name_i18n": json.dumps(group["name_i18n"], ensure_ascii=False),
                    "sort_order": group["sort_order"],
                },
            )
            group_ids[group["code"]] = result.scalar_one()
            group_count += 1

        # 2. Upsert attributes and their values
        for attr in SEED_ATTRIBUTES:
            result = await session.execute(
                _UPSERT_ATTRIBUTE,
                {
                    "id": str(uuid.uuid7()),
                    "code": attr["code"],
                    "slug": attr["slug"],
                    "group_id": str(group_ids[attr["group"]]),
                    "name_i18n": json.dumps(attr["name_i18n"], ensure_ascii=False),
                    "description_i18n": json.dumps(
                        attr["description_i18n"], ensure_ascii=False
                    ),
                    "data_type": attr["data_type"],
                    "ui_type": attr["ui_type"],
                    "is_dictionary": attr["is_dictionary"],
                    "level": attr["level"],
                    "is_filterable": attr["is_filterable"],
                    "is_searchable": attr["is_searchable"],
                    "search_weight": attr["search_weight"],
                    "is_comparable": attr["is_comparable"],
                    "is_visible_on_card": attr["is_visible_on_card"],
                    "is_visible_in_catalog": attr["is_visible_in_catalog"],
                    "validation_rules": json.dumps(attr["validation_rules"])
                    if attr["validation_rules"]
                    else None,
                },
            )
            attr_id = result.scalar_one()
            attr_count += 1

            # 3. Upsert attribute values
            for sort_idx, val in enumerate(attr.get("values", []), start=1):
                await session.execute(
                    _UPSERT_VALUE,
                    {
                        "id": str(uuid.uuid7()),
                        "attribute_id": str(attr_id),
                        "code": val["code"],
                        "slug": val["slug"],
                        "value_i18n": json.dumps(val["value_i18n"], ensure_ascii=False),
                        "search_aliases": val["search_aliases"],
                        "meta_data": json.dumps(val["meta_data"], ensure_ascii=False),
                        "value_group": val["value_group"],
                        "sort_order": sort_idx,
                    },
                )
                val_count += 1

    logger.info(
        "attributes.synced",
        groups=group_count,
        attributes=attr_count,
        values=val_count,
    )


# ---------------------------------------------------------------------------
# Standalone: python -m src.modules.catalog.management.sync_attributes
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
            await sync_attributes(factory)
        await container.close()

    asyncio.run(main())
