"""Idempotent sync of seed attribute data.

Seeds only essential data:
- Attribute group: "Physical Characteristics"
- Attribute: "Size" with clothing + footwear values
- AttributeFamily: "Clothing" with size bound
- Assigns family to "Одежда" category

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

_UPSERT_FAMILY = text("""
    INSERT INTO attribute_families (id, parent_id, code, name_i18n, description_i18n, sort_order, level)
    VALUES (:id, :parent_id, :code, cast(:name_i18n AS jsonb), cast(:description_i18n AS jsonb), :sort_order, :level)
    ON CONFLICT (code) DO UPDATE SET
        name_i18n        = EXCLUDED.name_i18n,
        description_i18n = EXCLUDED.description_i18n,
        sort_order       = EXCLUDED.sort_order
    RETURNING id
""")

_UPSERT_FAMILY_BINDING = text("""
    INSERT INTO family_attribute_bindings (id, family_id, attribute_id, sort_order, requirement_level)
    VALUES (:id, :family_id, :attribute_id, :sort_order, :requirement_level)
    ON CONFLICT (family_id, attribute_id) DO UPDATE SET
        sort_order        = EXCLUDED.sort_order,
        requirement_level = EXCLUDED.requirement_level
""")

_ASSIGN_FAMILY_TO_CATEGORY = text("""
    UPDATE categories SET family_id = :family_id WHERE slug = :slug AND parent_id IS NULL
""")

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------

SEED_GROUP = {
    "code": "physical",
    "name_i18n": {"ru": "Физические характеристики", "en": "Physical Characteristics"},
    "sort_order": 1,
}

SEED_SIZE_ATTRIBUTE = {
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
        {"code": "xxs", "slug": "xxs", "value_i18n": {"ru": "XXS", "en": "XXS"}, "search_aliases": [], "meta_data": {}, "value_group": "clothing"},
        {"code": "xs", "slug": "xs", "value_i18n": {"ru": "XS", "en": "XS"}, "search_aliases": [], "meta_data": {}, "value_group": "clothing"},
        {"code": "s", "slug": "s", "value_i18n": {"ru": "S", "en": "S"}, "search_aliases": [], "meta_data": {}, "value_group": "clothing"},
        {"code": "m", "slug": "m", "value_i18n": {"ru": "M", "en": "M"}, "search_aliases": [], "meta_data": {}, "value_group": "clothing"},
        {"code": "l", "slug": "l", "value_i18n": {"ru": "L", "en": "L"}, "search_aliases": [], "meta_data": {}, "value_group": "clothing"},
        {"code": "xl", "slug": "xl", "value_i18n": {"ru": "XL", "en": "XL"}, "search_aliases": [], "meta_data": {}, "value_group": "clothing"},
        {"code": "xxl", "slug": "xxl", "value_i18n": {"ru": "XXL", "en": "XXL"}, "search_aliases": [], "meta_data": {}, "value_group": "clothing"},
        # Footwear sizes (EU)
        {"code": "eu-36", "slug": "eu-36", "value_i18n": {"ru": "36", "en": "36"}, "search_aliases": ["36"], "meta_data": {"system": "EU"}, "value_group": "footwear"},
        {"code": "eu-37", "slug": "eu-37", "value_i18n": {"ru": "37", "en": "37"}, "search_aliases": ["37"], "meta_data": {"system": "EU"}, "value_group": "footwear"},
        {"code": "eu-38", "slug": "eu-38", "value_i18n": {"ru": "38", "en": "38"}, "search_aliases": ["38"], "meta_data": {"system": "EU"}, "value_group": "footwear"},
        {"code": "eu-39", "slug": "eu-39", "value_i18n": {"ru": "39", "en": "39"}, "search_aliases": ["39"], "meta_data": {"system": "EU"}, "value_group": "footwear"},
        {"code": "eu-40", "slug": "eu-40", "value_i18n": {"ru": "40", "en": "40"}, "search_aliases": ["40"], "meta_data": {"system": "EU"}, "value_group": "footwear"},
        {"code": "eu-41", "slug": "eu-41", "value_i18n": {"ru": "41", "en": "41"}, "search_aliases": ["41"], "meta_data": {"system": "EU"}, "value_group": "footwear"},
        {"code": "eu-42", "slug": "eu-42", "value_i18n": {"ru": "42", "en": "42"}, "search_aliases": ["42"], "meta_data": {"system": "EU"}, "value_group": "footwear"},
        {"code": "eu-43", "slug": "eu-43", "value_i18n": {"ru": "43", "en": "43"}, "search_aliases": ["43"], "meta_data": {"system": "EU"}, "value_group": "footwear"},
        {"code": "eu-44", "slug": "eu-44", "value_i18n": {"ru": "44", "en": "44"}, "search_aliases": ["44"], "meta_data": {"system": "EU"}, "value_group": "footwear"},
        {"code": "eu-45", "slug": "eu-45", "value_i18n": {"ru": "45", "en": "45"}, "search_aliases": ["45"], "meta_data": {"system": "EU"}, "value_group": "footwear"},
        {"code": "eu-46", "slug": "eu-46", "value_i18n": {"ru": "46", "en": "46"}, "search_aliases": ["46"], "meta_data": {"system": "EU"}, "value_group": "footwear"},
    ],
}

SEED_FAMILY = {
    "code": "clothing",
    "name_i18n": {"ru": "Одежда", "en": "Clothing"},
    "description_i18n": {
        "ru": "Базовая семья атрибутов для одежды",
        "en": "Base attribute family for clothing",
    },
    "sort_order": 1,
    "level": 0,
    "bindings": [
        {"attribute_code": "size", "sort_order": 1, "requirement_level": "OPTIONAL"},
    ],
    "assign_to_category_slug": "clothing",
}


# ---------------------------------------------------------------------------
# Sync logic
# ---------------------------------------------------------------------------


async def sync_attributes(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Upsert seed attribute group, size attribute, clothing family.

    Idempotent — safe to run on every deploy.
    """
    async with session_factory() as session, session.begin():
        # 1. Upsert attribute group
        result = await session.execute(
            _UPSERT_GROUP,
            {
                "id": str(uuid.uuid7()),
                "code": SEED_GROUP["code"],
                "name_i18n": json.dumps(SEED_GROUP["name_i18n"], ensure_ascii=False),
                "sort_order": SEED_GROUP["sort_order"],
            },
        )
        group_id = result.scalar_one()
        logger.info("attribute_group.synced", code=SEED_GROUP["code"])

        # 2. Upsert size attribute
        attr = SEED_SIZE_ATTRIBUTE
        result = await session.execute(
            _UPSERT_ATTRIBUTE,
            {
                "id": str(uuid.uuid7()),
                "code": attr["code"],
                "slug": attr["slug"],
                "group_id": str(group_id),
                "name_i18n": json.dumps(attr["name_i18n"], ensure_ascii=False),
                "description_i18n": json.dumps(attr["description_i18n"], ensure_ascii=False),
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
                "validation_rules": None,
            },
        )
        size_attr_id = result.scalar_one()
        logger.info("attribute.synced", code=attr["code"])

        # 3. Upsert attribute values
        val_count = 0
        for sort_idx, val in enumerate(attr["values"], start=1):
            await session.execute(
                _UPSERT_VALUE,
                {
                    "id": str(uuid.uuid7()),
                    "attribute_id": str(size_attr_id),
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
        logger.info("attribute_values.synced", count=val_count)

        # 4. Upsert AttributeFamily "clothing"
        fam = SEED_FAMILY
        result = await session.execute(
            _UPSERT_FAMILY,
            {
                "id": str(uuid.uuid7()),
                "parent_id": None,
                "code": fam["code"],
                "name_i18n": json.dumps(fam["name_i18n"], ensure_ascii=False),
                "description_i18n": json.dumps(fam["description_i18n"], ensure_ascii=False),
                "sort_order": fam["sort_order"],
                "level": fam["level"],
            },
        )
        family_id = result.scalar_one()
        logger.info("attribute_family.synced", code=fam["code"])

        # 5. Bind size → family
        for binding in fam["bindings"]:
            await session.execute(
                _UPSERT_FAMILY_BINDING,
                {
                    "id": str(uuid.uuid7()),
                    "family_id": str(family_id),
                    "attribute_id": str(size_attr_id),
                    "sort_order": binding["sort_order"],
                    "requirement_level": binding["requirement_level"],
                },
            )
        logger.info("family_bindings.synced", family=fam["code"], count=len(fam["bindings"]))

        # 6. Assign family to "Одежда" root category
        await session.execute(
            _ASSIGN_FAMILY_TO_CATEGORY,
            {"family_id": str(family_id), "slug": fam["assign_to_category_slug"]},
        )
        logger.info("category_family.assigned", category=fam["assign_to_category_slug"], family=fam["code"])

    logger.info(
        "attributes.synced",
        groups=1,
        attributes=1,
        values=val_count,
        families=1,
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
