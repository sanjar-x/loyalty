"""Idempotent sync of seed attribute data.

Seeds attribute groups, attributes (with dictionary values), attribute
templates for every root category, and template-attribute bindings so the
storefront endpoints return meaningful filters/card/comparison data.

Uses ``INSERT ... ON CONFLICT`` so it is safe to run on every deploy.

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
        is_comparable, is_visible_on_card,
        validation_rules
    )
    VALUES (
        :id, :code, :slug, :group_id, cast(:name_i18n AS jsonb), cast(:description_i18n AS jsonb),
        :data_type, :ui_type, :is_dictionary, :level,
        :is_filterable, :is_searchable, :search_weight,
        :is_comparable, :is_visible_on_card,
        cast(:validation_rules AS jsonb)
    )
    ON CONFLICT (code) DO UPDATE SET
        slug               = EXCLUDED.slug,
        group_id           = EXCLUDED.group_id,
        name_i18n          = EXCLUDED.name_i18n,
        description_i18n   = EXCLUDED.description_i18n,
        data_type          = EXCLUDED.data_type,
        ui_type            = EXCLUDED.ui_type,
        is_dictionary      = EXCLUDED.is_dictionary,
        level              = EXCLUDED.level,
        is_filterable      = EXCLUDED.is_filterable,
        is_searchable      = EXCLUDED.is_searchable,
        search_weight      = EXCLUDED.search_weight,
        is_comparable      = EXCLUDED.is_comparable,
        is_visible_on_card = EXCLUDED.is_visible_on_card,
        validation_rules   = EXCLUDED.validation_rules
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

_UPSERT_TEMPLATE = text("""
    INSERT INTO attribute_templates (id, code, name_i18n, description_i18n, sort_order)
    VALUES (:id, :code, cast(:name_i18n AS jsonb), cast(:description_i18n AS jsonb), :sort_order)
    ON CONFLICT (code) DO UPDATE SET
        name_i18n        = EXCLUDED.name_i18n,
        description_i18n = EXCLUDED.description_i18n,
        sort_order       = EXCLUDED.sort_order
    RETURNING id
""")

_UPSERT_TEMPLATE_BINDING = text("""
    INSERT INTO template_attribute_bindings (id, template_id, attribute_id, sort_order, requirement_level)
    VALUES (:id, :template_id, :attribute_id, :sort_order, :requirement_level)
    ON CONFLICT (template_id, attribute_id) DO UPDATE SET
        sort_order        = EXCLUDED.sort_order,
        requirement_level = EXCLUDED.requirement_level
""")

_ASSIGN_TEMPLATE_TO_CATEGORY = text("""
    UPDATE categories SET template_id = :template_id WHERE slug = :slug AND parent_id IS NULL
""")

_PROPAGATE_EFFECTIVE_TEMPLATE = text("""
    UPDATE categories
    SET effective_template_id = :template_id
    WHERE (slug = :slug AND parent_id IS NULL)
       OR full_slug LIKE :slug || '/%'
""")

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

SEED_GROUPS: list[dict] = [
    {
        "code": "physical",
        "name_i18n": {
            "ru": "Физические характеристики",
            "en": "Physical Characteristics",
        },
        "sort_order": 1,
    },
    {
        "code": "appearance",
        "name_i18n": {"ru": "Внешний вид", "en": "Appearance"},
        "sort_order": 2,
    },
    {
        "code": "general",
        "name_i18n": {"ru": "Общие", "en": "General"},
        "sort_order": 3,
    },
]

SEED_ATTRIBUTES: list[dict] = [
    # ── Physical ───────────────────────────────────────────────────────────
    {
        "code": "clothing_size",
        "slug": "clothing-size",
        "group_code": "physical",
        "name_i18n": {"ru": "Размер одежды", "en": "Clothing Size"},
        "description_i18n": {
            "ru": "Буквенный размер одежды",
            "en": "Letter-based clothing size",
        },
        "data_type": "STRING",
        "ui_type": "TEXT_BUTTON",
        "is_dictionary": True,
        "level": "VARIANT",
        "is_filterable": True,
        "is_searchable": False,
        "search_weight": 5,
        "is_comparable": False,
        "is_visible_on_card": True,
        "validation_rules": None,
        "values": [
            {"code": "xxs", "slug": "xxs", "value_i18n": {"ru": "XXS", "en": "XXS"}},
            {"code": "xs", "slug": "xs", "value_i18n": {"ru": "XS", "en": "XS"}},
            {"code": "s", "slug": "s", "value_i18n": {"ru": "S", "en": "S"}},
            {"code": "m", "slug": "m", "value_i18n": {"ru": "M", "en": "M"}},
            {"code": "l", "slug": "l", "value_i18n": {"ru": "L", "en": "L"}},
            {"code": "xl", "slug": "xl", "value_i18n": {"ru": "XL", "en": "XL"}},
            {"code": "xxl", "slug": "xxl", "value_i18n": {"ru": "XXL", "en": "XXL"}},
            {"code": "3xl", "slug": "3xl", "value_i18n": {"ru": "3XL", "en": "3XL"}},
            {"code": "4xl", "slug": "4xl", "value_i18n": {"ru": "4XL", "en": "4XL"}},
            {"code": "5xl", "slug": "5xl", "value_i18n": {"ru": "5XL", "en": "5XL"}},
        ],
    },
    {
        "code": "shoe_size",
        "slug": "shoe-size",
        "group_code": "physical",
        "name_i18n": {"ru": "Размер обуви", "en": "Shoe Size"},
        "description_i18n": {
            "ru": "Размер обуви (EU)",
            "en": "Shoe size (EU)",
        },
        "data_type": "FLOAT",
        "ui_type": "TEXT_BUTTON",
        "is_dictionary": True,
        "level": "VARIANT",
        "is_filterable": True,
        "is_searchable": False,
        "search_weight": 5,
        "is_comparable": False,
        "is_visible_on_card": True,
        "validation_rules": None,
        "values": [
            {
                "code": f"eu{s}",
                "slug": f"eu{s}",
                "value_i18n": {"ru": f"EU {s}", "en": f"EU {s}"},
            }
            for s in [
                "35",
                "35.5",
                "36",
                "36.5",
                "37",
                "37.5",
                "38",
                "38.5",
                "39",
                "40",
                "40.5",
                "41",
                "42",
                "42.5",
                "43",
                "44",
                "44.5",
                "45",
                "46",
                "47",
                "48",
            ]
        ],
    },
    # ── Appearance ─────────────────────────────────────────────────────────
    {
        "code": "color",
        "slug": "color",
        "group_code": "appearance",
        "name_i18n": {"ru": "Цвет", "en": "Color"},
        "description_i18n": {
            "ru": "Основной цвет товара",
            "en": "Primary product color",
        },
        "data_type": "STRING",
        "ui_type": "COLOR_SWATCH",
        "is_dictionary": True,
        "level": "VARIANT",
        "is_filterable": True,
        "is_searchable": True,
        "search_weight": 3,
        "is_comparable": False,
        "is_visible_on_card": True,
        "validation_rules": None,
        "values": [
            {
                "code": "black",
                "slug": "black",
                "value_i18n": {"ru": "Чёрный", "en": "Black"},
                "meta_data": {"hex": "#000000"},
            },
            {
                "code": "white",
                "slug": "white",
                "value_i18n": {"ru": "Белый", "en": "White"},
                "meta_data": {"hex": "#FFFFFF"},
            },
            {
                "code": "gray",
                "slug": "gray",
                "value_i18n": {"ru": "Серый", "en": "Gray"},
                "meta_data": {"hex": "#808080"},
            },
            {
                "code": "red",
                "slug": "red",
                "value_i18n": {"ru": "Красный", "en": "Red"},
                "meta_data": {"hex": "#FF0000"},
            },
            {
                "code": "blue",
                "slug": "blue",
                "value_i18n": {"ru": "Синий", "en": "Blue"},
                "meta_data": {"hex": "#0000FF"},
            },
            {
                "code": "navy",
                "slug": "navy",
                "value_i18n": {"ru": "Тёмно-синий", "en": "Navy"},
                "meta_data": {"hex": "#000080"},
            },
            {
                "code": "green",
                "slug": "green",
                "value_i18n": {"ru": "Зелёный", "en": "Green"},
                "meta_data": {"hex": "#008000"},
            },
            {
                "code": "beige",
                "slug": "beige",
                "value_i18n": {"ru": "Бежевый", "en": "Beige"},
                "meta_data": {"hex": "#F5F5DC"},
            },
            {
                "code": "brown",
                "slug": "brown",
                "value_i18n": {"ru": "Коричневый", "en": "Brown"},
                "meta_data": {"hex": "#8B4513"},
            },
            {
                "code": "pink",
                "slug": "pink",
                "value_i18n": {"ru": "Розовый", "en": "Pink"},
                "meta_data": {"hex": "#FFC0CB"},
            },
            {
                "code": "orange",
                "slug": "orange",
                "value_i18n": {"ru": "Оранжевый", "en": "Orange"},
                "meta_data": {"hex": "#FF8C00"},
            },
            {
                "code": "yellow",
                "slug": "yellow",
                "value_i18n": {"ru": "Жёлтый", "en": "Yellow"},
                "meta_data": {"hex": "#FFD700"},
            },
            {
                "code": "purple",
                "slug": "purple",
                "value_i18n": {"ru": "Фиолетовый", "en": "Purple"},
                "meta_data": {"hex": "#800080"},
            },
            {
                "code": "multicolor",
                "slug": "multicolor",
                "value_i18n": {"ru": "Мульти", "en": "Multicolor"},
            },
        ],
    },
    {
        "code": "material",
        "slug": "material",
        "group_code": "appearance",
        "name_i18n": {"ru": "Материал", "en": "Material"},
        "description_i18n": {
            "ru": "Основной материал изделия",
            "en": "Primary material",
        },
        "data_type": "STRING",
        "ui_type": "CHECKBOX",
        "is_dictionary": True,
        "level": "PRODUCT",
        "is_filterable": True,
        "is_searchable": True,
        "search_weight": 2,
        "is_comparable": True,
        "is_visible_on_card": False,
        "validation_rules": None,
        "values": [
            {
                "code": "cotton",
                "slug": "cotton",
                "value_i18n": {"ru": "Хлопок", "en": "Cotton"},
            },
            {
                "code": "polyester",
                "slug": "polyester",
                "value_i18n": {"ru": "Полиэстер", "en": "Polyester"},
            },
            {
                "code": "nylon",
                "slug": "nylon",
                "value_i18n": {"ru": "Нейлон", "en": "Nylon"},
            },
            {
                "code": "leather",
                "slug": "leather",
                "value_i18n": {"ru": "Кожа", "en": "Leather"},
            },
            {
                "code": "suede",
                "slug": "suede",
                "value_i18n": {"ru": "Замша", "en": "Suede"},
            },
            {
                "code": "canvas",
                "slug": "canvas",
                "value_i18n": {"ru": "Канвас", "en": "Canvas"},
            },
            {
                "code": "denim",
                "slug": "denim",
                "value_i18n": {"ru": "Деним", "en": "Denim"},
            },
            {
                "code": "wool",
                "slug": "wool",
                "value_i18n": {"ru": "Шерсть", "en": "Wool"},
            },
            {
                "code": "fleece",
                "slug": "fleece",
                "value_i18n": {"ru": "Флис", "en": "Fleece"},
            },
            {
                "code": "silk",
                "slug": "silk",
                "value_i18n": {"ru": "Шёлк", "en": "Silk"},
            },
            {
                "code": "mesh",
                "slug": "mesh",
                "value_i18n": {"ru": "Сетка", "en": "Mesh"},
            },
            {
                "code": "rubber",
                "slug": "rubber",
                "value_i18n": {"ru": "Резина", "en": "Rubber"},
            },
            {
                "code": "metal",
                "slug": "metal",
                "value_i18n": {"ru": "Металл", "en": "Metal"},
            },
        ],
    },
    # ── General ────────────────────────────────────────────────────────────
    {
        "code": "gender",
        "slug": "gender",
        "group_code": "general",
        "name_i18n": {"ru": "Пол", "en": "Gender"},
        "description_i18n": {
            "ru": "Целевой пол",
            "en": "Target gender",
        },
        "data_type": "STRING",
        "ui_type": "TEXT_BUTTON",
        "is_dictionary": True,
        "level": "PRODUCT",
        "is_filterable": True,
        "is_searchable": False,
        "search_weight": 1,
        "is_comparable": False,
        "is_visible_on_card": True,
        "validation_rules": None,
        "values": [
            {
                "code": "male",
                "slug": "male",
                "value_i18n": {"ru": "Мужской", "en": "Male"},
            },
            {
                "code": "female",
                "slug": "female",
                "value_i18n": {"ru": "Женский", "en": "Female"},
            },
            {
                "code": "unisex",
                "slug": "unisex",
                "value_i18n": {"ru": "Унисекс", "en": "Unisex"},
            },
        ],
    },
    {
        "code": "season",
        "slug": "season",
        "group_code": "general",
        "name_i18n": {"ru": "Сезон", "en": "Season"},
        "description_i18n": {
            "ru": "Сезонность товара",
            "en": "Product seasonality",
        },
        "data_type": "STRING",
        "ui_type": "CHECKBOX",
        "is_dictionary": True,
        "level": "PRODUCT",
        "is_filterable": True,
        "is_searchable": False,
        "search_weight": 1,
        "is_comparable": True,
        "is_visible_on_card": True,
        "validation_rules": None,
        "values": [
            {
                "code": "spring-summer",
                "slug": "spring-summer",
                "value_i18n": {"ru": "Весна-Лето", "en": "Spring-Summer"},
            },
            {
                "code": "fall-winter",
                "slug": "fall-winter",
                "value_i18n": {"ru": "Осень-Зима", "en": "Fall-Winter"},
            },
            {
                "code": "all-season",
                "slug": "all-season",
                "value_i18n": {"ru": "Всесезонный", "en": "All Season"},
            },
            {
                "code": "demi-season",
                "slug": "demi-season",
                "value_i18n": {"ru": "Демисезон", "en": "Demi-Season"},
            },
        ],
    },
]

SEED_FAMILIES: list[dict] = [
    # ── Clothing ───────────────────────────────────────────────────────────
    {
        "code": "clothing",
        "name_i18n": {"ru": "Одежда", "en": "Clothing"},
        "description_i18n": {
            "ru": "Семья атрибутов для одежды",
            "en": "Attribute template for clothing",
        },
        "sort_order": 1,
        "bindings": [
            {
                "attribute_code": "clothing_size",
                "sort_order": 1,
                "requirement_level": "REQUIRED",
            },
            {
                "attribute_code": "color",
                "sort_order": 2,
                "requirement_level": "REQUIRED",
            },
            {
                "attribute_code": "material",
                "sort_order": 3,
                "requirement_level": "RECOMMENDED",
            },
            {
                "attribute_code": "gender",
                "sort_order": 4,
                "requirement_level": "RECOMMENDED",
            },
            {
                "attribute_code": "season",
                "sort_order": 5,
                "requirement_level": "OPTIONAL",
            },
        ],
        "assign_to_category_slug": "clothing",
    },
    # ── Footwear ───────────────────────────────────────────────────────────
    {
        "code": "footwear",
        "name_i18n": {"ru": "Обувь", "en": "Footwear"},
        "description_i18n": {
            "ru": "Семья атрибутов для обуви",
            "en": "Attribute template for footwear",
        },
        "sort_order": 2,
        "bindings": [
            {
                "attribute_code": "shoe_size",
                "sort_order": 1,
                "requirement_level": "REQUIRED",
            },
            {
                "attribute_code": "color",
                "sort_order": 2,
                "requirement_level": "REQUIRED",
            },
            {
                "attribute_code": "material",
                "sort_order": 3,
                "requirement_level": "RECOMMENDED",
            },
            {
                "attribute_code": "gender",
                "sort_order": 4,
                "requirement_level": "RECOMMENDED",
            },
            {
                "attribute_code": "season",
                "sort_order": 5,
                "requirement_level": "OPTIONAL",
            },
        ],
        "assign_to_category_slug": "footwear",
    },
    # ── Accessories ────────────────────────────────────────────────────────
    {
        "code": "accessories",
        "name_i18n": {"ru": "Аксессуары", "en": "Accessories"},
        "description_i18n": {
            "ru": "Семья атрибутов для аксессуаров",
            "en": "Attribute template for accessories",
        },
        "sort_order": 3,
        "bindings": [
            {
                "attribute_code": "color",
                "sort_order": 1,
                "requirement_level": "RECOMMENDED",
            },
            {
                "attribute_code": "material",
                "sort_order": 2,
                "requirement_level": "OPTIONAL",
            },
            {
                "attribute_code": "gender",
                "sort_order": 3,
                "requirement_level": "OPTIONAL",
            },
        ],
        "assign_to_category_slug": "accessories",
    },
]


# ---------------------------------------------------------------------------
# Sync logic
# ---------------------------------------------------------------------------


async def sync_attributes(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Upsert seed attribute groups, attributes, templates, and bindings.

    Idempotent — safe to run on every deploy.
    """
    async with session_factory() as session, session.begin():
        # 1. Upsert attribute groups
        group_ids: dict[str, str] = {}  # code → db id

        for grp in SEED_GROUPS:
            result = await session.execute(
                _UPSERT_GROUP,
                {
                    "id": str(uuid.uuid7()),
                    "code": grp["code"],
                    "name_i18n": json.dumps(grp["name_i18n"], ensure_ascii=False),
                    "sort_order": grp["sort_order"],
                },
            )
            group_ids[grp["code"]] = str(result.scalar_one())
            logger.info("attribute_group.synced", code=grp["code"])

        # 2. Upsert attributes and their values
        attr_ids: dict[str, str] = {}  # code → db id
        total_vals = 0

        for attr in SEED_ATTRIBUTES:
            result = await session.execute(
                _UPSERT_ATTRIBUTE,
                {
                    "id": str(uuid.uuid7()),
                    "code": attr["code"],
                    "slug": attr["slug"],
                    "group_id": group_ids[attr["group_code"]],
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
                    "validation_rules": None,
                },
            )
            attr_id = result.scalar_one()
            attr_ids[attr["code"]] = str(attr_id)
            logger.info("attribute.synced", code=attr["code"])

            for sort_idx, val in enumerate(attr.get("values", []), start=1):
                await session.execute(
                    _UPSERT_VALUE,
                    {
                        "id": str(uuid.uuid7()),
                        "attribute_id": str(attr_id),
                        "code": val["code"],
                        "slug": val["slug"],
                        "value_i18n": json.dumps(val["value_i18n"], ensure_ascii=False),
                        "search_aliases": val.get("search_aliases", []),
                        "meta_data": json.dumps(
                            val.get("meta_data", {}), ensure_ascii=False
                        ),
                        "value_group": val.get("value_group"),
                        "sort_order": sort_idx,
                    },
                )
                total_vals += 1

        logger.info("attribute_values.synced", count=total_vals)

        # 3. Upsert templates and bind attributes
        template_ids: dict[str, str] = {}  # code → db id

        for temp in SEED_FAMILIES:
            result = await session.execute(
                _UPSERT_TEMPLATE,
                {
                    "id": str(uuid.uuid7()),
                    "code": temp["code"],
                    "name_i18n": json.dumps(temp["name_i18n"], ensure_ascii=False),
                    "description_i18n": json.dumps(
                        temp["description_i18n"], ensure_ascii=False
                    ),
                    "sort_order": temp["sort_order"],
                },
            )
            temp_id = result.scalar_one()
            template_ids[temp["code"]] = str(temp_id)
            logger.info("attribute_template.synced", code=temp["code"])

            # Bind attributes to template
            for binding in temp.get("bindings", []):
                attr_db_id = attr_ids[binding["attribute_code"]]
                await session.execute(
                    _UPSERT_TEMPLATE_BINDING,
                    {
                        "id": str(uuid.uuid7()),
                        "template_id": str(temp_id),
                        "attribute_id": attr_db_id,
                        "sort_order": binding["sort_order"],
                        "requirement_level": binding["requirement_level"],
                    },
                )
            logger.info(
                "template_bindings.synced",
                template=temp["code"],
                count=len(temp.get("bindings", [])),
            )

            # Assign template to category
            if temp.get("assign_to_category_slug"):
                await session.execute(
                    _ASSIGN_TEMPLATE_TO_CATEGORY,
                    {
                        "template_id": str(temp_id),
                        "slug": temp["assign_to_category_slug"],
                    },
                )
                logger.info(
                    "category_template.assigned",
                    category=temp["assign_to_category_slug"],
                    template=temp["code"],
                )
                await session.execute(
                    _PROPAGATE_EFFECTIVE_TEMPLATE,
                    {
                        "template_id": str(temp_id),
                        "slug": temp["assign_to_category_slug"],
                    },
                )
                logger.info(
                    "effective_template_id.propagated",
                    category=temp["assign_to_category_slug"],
                    template=temp["code"],
                )

    logger.info(
        "attributes.synced",
        groups=len(SEED_GROUPS),
        attributes=len(SEED_ATTRIBUTES),
        values=total_vals,
        templates=len(SEED_FAMILIES),
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
