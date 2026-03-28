"""
Shared integration test fixtures for catalog repository tests.

Provides seed data fixtures that insert prerequisite rows (Currency,
Brand, Category, Attribute, AttributeValue) so that FK-dependent
repositories (Product, MediaAsset, ProductAttributeValue, etc.) can
operate without setup boilerplate in each test file.
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.entities import Brand, Category
from src.modules.catalog.domain.value_objects import (
    AttributeDataType,
    AttributeLevel,
    AttributeUIType,
)
from src.modules.catalog.infrastructure.models import (
    Attribute as OrmAttribute,
    AttributeGroup as OrmAttributeGroup,
    AttributeValue as OrmAttributeValue,
)
from src.modules.catalog.infrastructure.repositories.brand import BrandRepository
from src.modules.catalog.infrastructure.repositories.category import CategoryRepository
from src.modules.geo.infrastructure.models import CurrencyModel


@pytest.fixture()
async def seed_currency(db_session: AsyncSession) -> CurrencyModel:
    """Insert a CurrencyModel row with code='RUB' required by SKU/Variant FK."""
    currency = CurrencyModel(
        code="RUB",
        numeric="643",
        name="Russian Ruble",
        minor_unit=2,
    )
    db_session.add(currency)
    await db_session.flush()
    return currency


@pytest.fixture()
async def seed_brand(db_session: AsyncSession) -> Brand:
    """Create and persist a Brand domain entity via BrandRepository."""
    repo = BrandRepository(session=db_session)
    brand = Brand.create(name="Test Brand", slug="test-brand")
    return await repo.add(brand)


@pytest.fixture()
async def seed_category(db_session: AsyncSession) -> Category:
    """Create and persist a root Category domain entity via CategoryRepository."""
    repo = CategoryRepository(session=db_session)
    category = Category.create_root(
        name_i18n={"en": "Electronics", "ru": "Электроника"},
        slug="electronics",
    )
    return await repo.add(category)


@pytest.fixture()
async def seed_product_deps(
    seed_currency: CurrencyModel,
    seed_brand: Brand,
    seed_category: Category,
) -> dict[str, uuid.UUID]:
    """Return dict with 'brand_id' and 'category_id' for Product.create() calls."""
    return {
        "brand_id": seed_brand.id,
        "category_id": seed_category.id,
    }


@pytest.fixture()
async def seed_attribute_with_values(
    db_session: AsyncSession,
) -> dict[str, uuid.UUID]:
    """Create an AttributeGroup, Attribute, and two AttributeValues via ORM inserts.

    Returns dict with attribute_id, value_id_1, value_id_2 for SKU attribute
    value link tests.
    """
    group_id = uuid.uuid4()
    group = OrmAttributeGroup(
        id=group_id,
        code="test-group",
        name_i18n={"en": "Test Group", "ru": "Тестовая группа"},
        sort_order=0,
    )
    db_session.add(group)
    await db_session.flush()

    attr_id = uuid.uuid4()
    attr = OrmAttribute(
        id=attr_id,
        code="test-attr",
        slug="test-attr",
        group_id=group_id,
        name_i18n={"en": "Test Attribute", "ru": "Тестовый атрибут"},
        description_i18n={"en": "Test", "ru": "Тест"},
        data_type=AttributeDataType.STRING,
        ui_type=AttributeUIType.TEXT_BUTTON,
        is_dictionary=True,
        level=AttributeLevel.VARIANT,
        is_filterable=False,
        is_searchable=False,
        search_weight=5,
        is_comparable=False,
        is_visible_on_card=False,
    )
    db_session.add(attr)
    await db_session.flush()

    val_id_1 = uuid.uuid4()
    val_1 = OrmAttributeValue(
        id=val_id_1,
        attribute_id=attr_id,
        code="val-1",
        slug="val-1",
        value_i18n={"en": "Value 1", "ru": "Значение 1"},
        sort_order=0,
    )
    val_id_2 = uuid.uuid4()
    val_2 = OrmAttributeValue(
        id=val_id_2,
        attribute_id=attr_id,
        code="val-2",
        slug="val-2",
        value_i18n={"en": "Value 2", "ru": "Значение 2"},
        sort_order=1,
    )
    db_session.add_all([val_1, val_2])
    await db_session.flush()

    return {
        "group_id": group_id,
        "attribute_id": attr_id,
        "value_id_1": val_id_1,
        "value_id_2": val_id_2,
    }
