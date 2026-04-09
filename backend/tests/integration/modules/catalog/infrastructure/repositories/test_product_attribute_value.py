"""
Integration tests for ProductAttributeValueRepository Data Mapper roundtrips.

Proves that ProductAttributeValue entities survive CRUD cycles with
FK triple (product_id, attribute_id, attribute_value_id), list_by_product,
check_assignment_exists, and get_by_product_and_attribute.

Part of Phase 07 -- Repository & Data Integrity (REPO-02, REPO-05).
"""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.entities import Product, ProductAttributeValue
from src.modules.catalog.infrastructure.repositories.product import ProductRepository
from src.modules.catalog.infrastructure.repositories.product_attribute_value import (
    ProductAttributeValueRepository,
)


@pytest.fixture()
async def _seed_pav_deps(
    db_session: AsyncSession,
    seed_product_deps: dict[str, uuid.UUID],
    seed_attribute_with_values: dict[str, uuid.UUID],
) -> dict[str, uuid.UUID]:
    """Create a Product and return IDs for PAV tests."""
    repo = ProductRepository(session=db_session)
    product = Product.create(
        slug="pav-test-product",
        title_i18n={"en": "PAV Product", "ru": "Продукт PAV"},
        brand_id=seed_product_deps["brand_id"],
        primary_category_id=seed_product_deps["category_id"],
    )
    await repo.add(product)
    await db_session.flush()
    return {
        "product_id": product.id,
        "attribute_id": seed_attribute_with_values["attribute_id"],
        "value_id_1": seed_attribute_with_values["value_id_1"],
        "value_id_2": seed_attribute_with_values["value_id_2"],
    }


class TestProductAttributeValueRoundtrip:
    """Verify ProductAttributeValue entity survives full create-read roundtrip."""

    async def test_pav_basic_roundtrip(
        self,
        db_session: AsyncSession,
        _seed_pav_deps: dict[str, uuid.UUID],
    ) -> None:
        """All PAV FK fields survive roundtrip."""
        repo = ProductAttributeValueRepository(session=db_session)
        pav = ProductAttributeValue.create(
            product_id=_seed_pav_deps["product_id"],
            attribute_id=_seed_pav_deps["attribute_id"],
            attribute_value_id=_seed_pav_deps["value_id_1"],
        )
        await repo.add(pav)
        await db_session.flush()

        fetched = await repo.get(pav.id)

        assert fetched is not None
        assert fetched.product_id == _seed_pav_deps["product_id"]
        assert fetched.attribute_id == _seed_pav_deps["attribute_id"]
        assert fetched.attribute_value_id == _seed_pav_deps["value_id_1"]

    async def test_pav_list_by_product(
        self,
        db_session: AsyncSession,
        _seed_pav_deps: dict[str, uuid.UUID],
        seed_attribute_with_values: dict[str, uuid.UUID],
    ) -> None:
        """list_by_product returns all PAVs for a product."""
        repo = ProductAttributeValueRepository(session=db_session)

        # Need a second attribute for the second PAV (unique constraint: product_id + attribute_id)
        from src.modules.catalog.domain.value_objects import (
            AttributeDataType,
            AttributeLevel,
            AttributeUIType,
        )
        from src.modules.catalog.infrastructure.models import (
            Attribute as OrmAttribute,
        )
        from src.modules.catalog.infrastructure.models import (
            AttributeValue as OrmAttributeValue,
        )

        attr2_id = uuid.uuid4()
        attr2 = OrmAttribute(
            id=attr2_id,
            code="pav-attr-2",
            slug="pav-attr-2",
            group_id=seed_attribute_with_values["group_id"],
            name_i18n={"en": "PAV Attr 2", "ru": "PAV Атрибут 2"},
            description_i18n={},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.TEXT_BUTTON,
            is_dictionary=True,
            level=AttributeLevel.PRODUCT,
            search_weight=5,
        )
        db_session.add(attr2)
        await db_session.flush()

        val2_id = uuid.uuid4()
        val2 = OrmAttributeValue(
            id=val2_id,
            attribute_id=attr2_id,
            code="pav-val-2",
            slug="pav-val-2",
            value_i18n={"en": "V2", "ru": "З2"},
            sort_order=0,
        )
        db_session.add(val2)
        await db_session.flush()

        pav1 = ProductAttributeValue.create(
            product_id=_seed_pav_deps["product_id"],
            attribute_id=_seed_pav_deps["attribute_id"],
            attribute_value_id=_seed_pav_deps["value_id_1"],
        )
        pav2 = ProductAttributeValue.create(
            product_id=_seed_pav_deps["product_id"],
            attribute_id=attr2_id,
            attribute_value_id=val2_id,
        )
        await repo.add(pav1)
        await repo.add(pav2)
        await db_session.flush()

        result = await repo.list_by_product(_seed_pav_deps["product_id"])
        assert len(result) == 2

    async def test_pav_check_assignment_exists(
        self,
        db_session: AsyncSession,
        _seed_pav_deps: dict[str, uuid.UUID],
    ) -> None:
        """check_assignment_exists returns True/False correctly."""
        repo = ProductAttributeValueRepository(session=db_session)
        pav = ProductAttributeValue.create(
            product_id=_seed_pav_deps["product_id"],
            attribute_id=_seed_pav_deps["attribute_id"],
            attribute_value_id=_seed_pav_deps["value_id_1"],
        )
        await repo.add(pav)
        await db_session.flush()

        assert (
            await repo.check_assignment_exists(
                _seed_pav_deps["product_id"],
                _seed_pav_deps["attribute_id"],
            )
            is True
        )
        assert (
            await repo.check_assignment_exists(
                _seed_pav_deps["product_id"],
                uuid.uuid4(),
            )
            is False
        )

    async def test_pav_get_by_product_and_attribute(
        self,
        db_session: AsyncSession,
        _seed_pav_deps: dict[str, uuid.UUID],
    ) -> None:
        """get_by_product_and_attribute returns correct entity or None."""
        repo = ProductAttributeValueRepository(session=db_session)
        pav = ProductAttributeValue.create(
            product_id=_seed_pav_deps["product_id"],
            attribute_id=_seed_pav_deps["attribute_id"],
            attribute_value_id=_seed_pav_deps["value_id_1"],
        )
        await repo.add(pav)
        await db_session.flush()

        fetched = await repo.get_by_product_and_attribute(
            _seed_pav_deps["product_id"],
            _seed_pav_deps["attribute_id"],
        )
        assert fetched is not None
        assert fetched.id == pav.id

        missing = await repo.get_by_product_and_attribute(
            _seed_pav_deps["product_id"],
            uuid.uuid4(),
        )
        assert missing is None
