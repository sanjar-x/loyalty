"""
Integration tests verifying FK, unique, and check constraints at the DB level.

Uses direct ORM model inserts (bypassing domain validation) to prove that
PostgreSQL enforces data integrity constraints independent of application logic.

Part of Phase 07 -- Repository & Data Integrity (REPO-03).
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.entities import (
    AttributeTemplate,
    Brand,
    Category,
    Product,
)
from src.modules.catalog.domain.value_objects import (
    AttributeDataType,
    AttributeLevel,
    AttributeUIType,
    Money,
    ProductStatus,
    RequirementLevel,
)
from src.modules.catalog.infrastructure.models import (
    Attribute as OrmAttribute,
    AttributeGroup as OrmAttributeGroup,
    AttributeValue as OrmAttributeValue,
    Brand as OrmBrand,
    Category as OrmCategory,
    MediaAsset as OrmMediaAsset,
    Product as OrmProduct,
    ProductVariant as OrmProductVariant,
    SKU as OrmSKU,
    TemplateAttributeBinding as OrmBinding,
)
from src.modules.catalog.infrastructure.models import (
    AttributeTemplate as OrmAttributeTemplate,
)
from src.modules.catalog.infrastructure.repositories.brand import BrandRepository
from src.modules.catalog.infrastructure.repositories.category import CategoryRepository
from src.modules.catalog.infrastructure.repositories.product import ProductRepository


# =========================================================================
# Task 07-03-01: FK constraint verification
# =========================================================================


class TestFKConstraints:
    """Verify that FK constraints reject orphaned records at DB level."""

    async def test_product_requires_valid_brand_id(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
    ) -> None:
        """Product with non-existent brand_id raises IntegrityError."""
        orm = OrmProduct(
            id=uuid.uuid4(),
            brand_id=uuid.uuid4(),  # non-existent
            primary_category_id=seed_product_deps["category_id"],
            slug="fk-brand-test",
            title_i18n={"en": "Test", "ru": "Тест"},
            status=ProductStatus.DRAFT,
        )
        async with db_session.begin_nested():
            db_session.add(orm)
            with pytest.raises(IntegrityError):
                await db_session.flush()

    async def test_product_requires_valid_category_id(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
    ) -> None:
        """Product with non-existent category_id raises IntegrityError."""
        orm = OrmProduct(
            id=uuid.uuid4(),
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=uuid.uuid4(),  # non-existent
            slug="fk-cat-test",
            title_i18n={"en": "Test", "ru": "Тест"},
            status=ProductStatus.DRAFT,
        )
        async with db_session.begin_nested():
            db_session.add(orm)
            with pytest.raises(IntegrityError):
                await db_session.flush()

    async def test_product_variant_requires_valid_product_id(
        self,
        db_session: AsyncSession,
        seed_currency,
    ) -> None:
        """ProductVariant with non-existent product_id raises IntegrityError."""
        orm = OrmProductVariant(
            id=uuid.uuid4(),
            product_id=uuid.uuid4(),  # non-existent
            name_i18n={"en": "Variant", "ru": "Вариант"},
            sort_order=0,
        )
        async with db_session.begin_nested():
            db_session.add(orm)
            with pytest.raises(IntegrityError):
                await db_session.flush()

    async def test_sku_requires_valid_variant_id(
        self,
        db_session: AsyncSession,
        seed_currency,
    ) -> None:
        """SKU with non-existent variant_id raises IntegrityError."""
        orm = OrmSKU(
            id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            variant_id=uuid.uuid4(),  # non-existent
            sku_code="FK-SKU-001",
            variant_hash="abc123",
        )
        async with db_session.begin_nested():
            db_session.add(orm)
            with pytest.raises(IntegrityError):
                await db_session.flush()

    async def test_sku_requires_valid_currency(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
        seed_currency,
    ) -> None:
        """SKU with invalid currency code raises IntegrityError."""
        # Create a product with variant first
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="fk-currency-test",
            title_i18n={"en": "Currency FK", "ru": "FK валюты"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        await repo.add(product)
        await db_session.flush()

        variant_id = product.variants[0].id
        orm = OrmSKU(
            id=uuid.uuid4(),
            product_id=product.id,
            variant_id=variant_id,
            sku_code="FK-CUR-001",
            variant_hash="currency-test-hash",
            currency="XXX",  # non-existent currency
        )
        async with db_session.begin_nested():
            db_session.add(orm)
            with pytest.raises(IntegrityError):
                await db_session.flush()

    async def test_attribute_value_requires_valid_attribute_id(
        self,
        db_session: AsyncSession,
    ) -> None:
        """AttributeValue with non-existent attribute_id raises IntegrityError."""
        orm = OrmAttributeValue(
            id=uuid.uuid4(),
            attribute_id=uuid.uuid4(),  # non-existent
            code="fk-av-test",
            slug="fk-av-test",
            value_i18n={"en": "Test", "ru": "Тест"},
            sort_order=0,
        )
        async with db_session.begin_nested():
            db_session.add(orm)
            with pytest.raises(IntegrityError):
                await db_session.flush()

    async def test_template_binding_requires_valid_template_id(
        self,
        db_session: AsyncSession,
        seed_attribute_with_values: dict[str, uuid.UUID],
    ) -> None:
        """TemplateAttributeBinding with non-existent template_id raises IntegrityError."""
        orm = OrmBinding(
            id=uuid.uuid4(),
            template_id=uuid.uuid4(),  # non-existent
            attribute_id=seed_attribute_with_values["attribute_id"],
            sort_order=0,
            requirement_level=RequirementLevel.OPTIONAL,
        )
        async with db_session.begin_nested():
            db_session.add(orm)
            with pytest.raises(IntegrityError):
                await db_session.flush()

    async def test_template_binding_requires_valid_attribute_id(
        self,
        db_session: AsyncSession,
    ) -> None:
        """TemplateAttributeBinding with non-existent attribute_id raises IntegrityError."""
        # Create a template first
        template = OrmAttributeTemplate(
            id=uuid.uuid4(),
            code="fk-binding-template",
            name_i18n={"en": "FK Test", "ru": "Тест FK"},
            description_i18n={},
            sort_order=0,
        )
        db_session.add(template)
        await db_session.flush()

        orm = OrmBinding(
            id=uuid.uuid4(),
            template_id=template.id,
            attribute_id=uuid.uuid4(),  # non-existent
            sort_order=0,
            requirement_level=RequirementLevel.OPTIONAL,
        )
        async with db_session.begin_nested():
            db_session.add(orm)
            with pytest.raises(IntegrityError):
                await db_session.flush()


# =========================================================================
# Task 07-03-02: Unique constraint and check constraint verification
# =========================================================================


class TestUniqueConstraints:
    """Verify that unique constraints reject duplicate values at DB level."""

    async def test_brand_slug_unique(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Two brands with same slug raises IntegrityError."""
        b1 = OrmBrand(id=uuid.uuid4(), name="Brand A", slug="same-slug")
        b2 = OrmBrand(id=uuid.uuid4(), name="Brand B", slug="same-slug")
        db_session.add(b1)
        await db_session.flush()

        async with db_session.begin_nested():
            db_session.add(b2)
            with pytest.raises(IntegrityError):
                await db_session.flush()

    async def test_brand_name_unique(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Two brands with same name raises IntegrityError."""
        b1 = OrmBrand(id=uuid.uuid4(), name="Same Name", slug="slug-a")
        b2 = OrmBrand(id=uuid.uuid4(), name="Same Name", slug="slug-b")
        db_session.add(b1)
        await db_session.flush()

        async with db_session.begin_nested():
            db_session.add(b2)
            with pytest.raises(IntegrityError):
                await db_session.flush()

    async def test_category_slug_unique_within_parent(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Same slug+parent_id fails; same slug under different parent succeeds."""
        # Two root categories (parent_id=NULL) with same slug
        c1 = OrmCategory(
            id=uuid.uuid4(),
            parent_id=None,
            slug="dup-slug",
            full_slug="dup-slug",
            level=0,
            name_i18n={"en": "Cat 1", "ru": "Кат 1"},
            sort_order=0,
        )
        c2 = OrmCategory(
            id=uuid.uuid4(),
            parent_id=None,
            slug="dup-slug",
            full_slug="dup-slug-2",
            level=0,
            name_i18n={"en": "Cat 2", "ru": "Кат 2"},
            sort_order=1,
        )
        db_session.add(c1)
        await db_session.flush()

        async with db_session.begin_nested():
            db_session.add(c2)
            with pytest.raises(IntegrityError):
                await db_session.flush()

        # Same slug under different parent succeeds
        c3 = OrmCategory(
            id=uuid.uuid4(),
            parent_id=c1.id,
            slug="dup-slug",
            full_slug="dup-slug/dup-slug",
            level=1,
            name_i18n={"en": "Child", "ru": "Дочерний"},
            sort_order=0,
        )
        db_session.add(c3)
        await db_session.flush()  # should succeed

    async def test_attribute_code_unique(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Two attributes with same code raises IntegrityError."""
        group_id = uuid.uuid4()
        group = OrmAttributeGroup(
            id=group_id,
            code="uq-grp",
            name_i18n={"en": "G", "ru": "Г"},
            sort_order=0,
        )
        db_session.add(group)
        await db_session.flush()

        a1 = OrmAttribute(
            id=uuid.uuid4(),
            code="dup-code",
            slug="slug-1",
            group_id=group_id,
            name_i18n={"en": "A1", "ru": "А1"},
            description_i18n={},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.TEXT_BUTTON,
            is_dictionary=True,
            level=AttributeLevel.PRODUCT,
            search_weight=5,
        )
        a2 = OrmAttribute(
            id=uuid.uuid4(),
            code="dup-code",
            slug="slug-2",
            group_id=group_id,
            name_i18n={"en": "A2", "ru": "А2"},
            description_i18n={},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.TEXT_BUTTON,
            is_dictionary=True,
            level=AttributeLevel.PRODUCT,
            search_weight=5,
        )
        db_session.add(a1)
        await db_session.flush()

        async with db_session.begin_nested():
            db_session.add(a2)
            with pytest.raises(IntegrityError):
                await db_session.flush()

    async def test_attribute_slug_unique(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Two attributes with same slug raises IntegrityError."""
        group_id = uuid.uuid4()
        group = OrmAttributeGroup(
            id=group_id,
            code="uq-slug-grp",
            name_i18n={"en": "G", "ru": "Г"},
            sort_order=0,
        )
        db_session.add(group)
        await db_session.flush()

        a1 = OrmAttribute(
            id=uuid.uuid4(),
            code="code-1",
            slug="dup-slug",
            group_id=group_id,
            name_i18n={"en": "A1", "ru": "А1"},
            description_i18n={},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.TEXT_BUTTON,
            is_dictionary=True,
            level=AttributeLevel.PRODUCT,
            search_weight=5,
        )
        a2 = OrmAttribute(
            id=uuid.uuid4(),
            code="code-2",
            slug="dup-slug",
            group_id=group_id,
            name_i18n={"en": "A2", "ru": "А2"},
            description_i18n={},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.TEXT_BUTTON,
            is_dictionary=True,
            level=AttributeLevel.PRODUCT,
            search_weight=5,
        )
        db_session.add(a1)
        await db_session.flush()

        async with db_session.begin_nested():
            db_session.add(a2)
            with pytest.raises(IntegrityError):
                await db_session.flush()

    async def test_attribute_value_code_unique_per_attribute(
        self,
        db_session: AsyncSession,
        seed_attribute_with_values: dict[str, uuid.UUID],
    ) -> None:
        """Same code under same attribute fails; under different attribute succeeds."""
        attr_id = seed_attribute_with_values["attribute_id"]

        # Duplicate code under same attribute
        v = OrmAttributeValue(
            id=uuid.uuid4(),
            attribute_id=attr_id,
            code="val-1",  # already exists from seed
            slug="val-1-dup",
            value_i18n={"en": "Dup", "ru": "Дуп"},
            sort_order=99,
        )
        async with db_session.begin_nested():
            db_session.add(v)
            with pytest.raises(IntegrityError):
                await db_session.flush()

    async def test_template_binding_pair_unique(
        self,
        db_session: AsyncSession,
        seed_attribute_with_values: dict[str, uuid.UUID],
    ) -> None:
        """Two bindings with same (template_id, attribute_id) raises IntegrityError."""
        template = OrmAttributeTemplate(
            id=uuid.uuid4(),
            code="pair-uq-template",
            name_i18n={"en": "T", "ru": "Ш"},
            description_i18n={},
            sort_order=0,
        )
        db_session.add(template)
        await db_session.flush()

        attr_id = seed_attribute_with_values["attribute_id"]
        b1 = OrmBinding(
            id=uuid.uuid4(),
            template_id=template.id,
            attribute_id=attr_id,
            sort_order=0,
            requirement_level=RequirementLevel.OPTIONAL,
        )
        b2 = OrmBinding(
            id=uuid.uuid4(),
            template_id=template.id,
            attribute_id=attr_id,
            sort_order=1,
            requirement_level=RequirementLevel.REQUIRED,
        )
        db_session.add(b1)
        await db_session.flush()

        async with db_session.begin_nested():
            db_session.add(b2)
            with pytest.raises(IntegrityError):
                await db_session.flush()

    async def test_product_slug_partial_unique(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
    ) -> None:
        """Partial unique index: two active products same slug fail; active+soft-deleted succeeds."""
        brand_id = seed_product_deps["brand_id"]
        cat_id = seed_product_deps["category_id"]

        p1 = OrmProduct(
            id=uuid.uuid4(),
            brand_id=brand_id,
            primary_category_id=cat_id,
            slug="partial-uq",
            title_i18n={"en": "P1", "ru": "П1"},
            status=ProductStatus.DRAFT,
            deleted_at=None,
        )
        db_session.add(p1)
        await db_session.flush()

        # Second active product with same slug -- should fail
        p2 = OrmProduct(
            id=uuid.uuid4(),
            brand_id=brand_id,
            primary_category_id=cat_id,
            slug="partial-uq",
            title_i18n={"en": "P2", "ru": "П2"},
            status=ProductStatus.DRAFT,
            deleted_at=None,
        )
        async with db_session.begin_nested():
            db_session.add(p2)
            with pytest.raises(IntegrityError):
                await db_session.flush()

        # Soft-deleted product with same slug -- should succeed
        p3 = OrmProduct(
            id=uuid.uuid4(),
            brand_id=brand_id,
            primary_category_id=cat_id,
            slug="partial-uq",
            title_i18n={"en": "P3", "ru": "П3"},
            status=ProductStatus.DRAFT,
            deleted_at=datetime.now(UTC),
        )
        db_session.add(p3)
        await db_session.flush()  # should succeed

    async def test_sku_code_partial_unique(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
        seed_currency,
    ) -> None:
        """Partial unique on sku_code: two active same code fail; active+soft-deleted succeeds."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="sku-uq-test",
            title_i18n={"en": "SKU UQ", "ru": "SKU УК"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        product.add_sku(
            product.variants[0].id,
            sku_code="UQ-SKU-001",
            price=Money(100, "RUB"),
        )
        await repo.add(product)
        await db_session.flush()

        # Insert another SKU with same code directly via ORM
        sku2 = OrmSKU(
            id=uuid.uuid4(),
            product_id=product.id,
            variant_id=product.variants[0].id,
            sku_code="UQ-SKU-001",
            variant_hash="different-hash-2",
            deleted_at=None,
        )
        async with db_session.begin_nested():
            db_session.add(sku2)
            with pytest.raises(IntegrityError):
                await db_session.flush()

        # Soft-deleted SKU with same code should succeed
        sku3 = OrmSKU(
            id=uuid.uuid4(),
            product_id=product.id,
            variant_id=product.variants[0].id,
            sku_code="UQ-SKU-001",
            variant_hash="different-hash-3",
            deleted_at=datetime.now(UTC),
        )
        db_session.add(sku3)
        await db_session.flush()  # should succeed

    async def test_sku_variant_hash_partial_unique(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
        seed_currency,
    ) -> None:
        """Partial unique on variant_hash: two active same hash fail."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="hash-uq-test",
            title_i18n={"en": "Hash UQ", "ru": "Хеш УК"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        product.add_sku(
            product.variants[0].id,
            sku_code="HASH-001",
            price=Money(100, "RUB"),
        )
        await repo.add(product)
        await db_session.flush()

        existing_hash = product.variants[0].skus[0].variant_hash
        sku2 = OrmSKU(
            id=uuid.uuid4(),
            product_id=product.id,
            variant_id=product.variants[0].id,
            sku_code="HASH-002",
            variant_hash=existing_hash,
            deleted_at=None,
        )
        async with db_session.begin_nested():
            db_session.add(sku2)
            with pytest.raises(IntegrityError):
                await db_session.flush()


class TestCheckConstraints:
    """Verify check constraints at DB level."""

    async def test_attribute_search_weight_range(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Check constraint rejects search_weight outside 1-10 range."""
        group_id = uuid.uuid4()
        group = OrmAttributeGroup(
            id=group_id,
            code="ck-grp",
            name_i18n={"en": "G", "ru": "Г"},
            sort_order=0,
        )
        db_session.add(group)
        await db_session.flush()

        # Below min (0)
        a_low = OrmAttribute(
            id=uuid.uuid4(),
            code="ck-low",
            slug="ck-low",
            group_id=group_id,
            name_i18n={"en": "Low", "ru": "Низкий"},
            description_i18n={},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.TEXT_BUTTON,
            is_dictionary=True,
            level=AttributeLevel.PRODUCT,
            search_weight=0,
        )
        async with db_session.begin_nested():
            db_session.add(a_low)
            with pytest.raises(IntegrityError):
                await db_session.flush()

        # Above max (11)
        a_high = OrmAttribute(
            id=uuid.uuid4(),
            code="ck-high",
            slug="ck-high",
            group_id=group_id,
            name_i18n={"en": "High", "ru": "Высокий"},
            description_i18n={},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.TEXT_BUTTON,
            is_dictionary=True,
            level=AttributeLevel.PRODUCT,
            search_weight=11,
        )
        async with db_session.begin_nested():
            db_session.add(a_high)
            with pytest.raises(IntegrityError):
                await db_session.flush()

        # Valid (5) -- should succeed
        a_ok = OrmAttribute(
            id=uuid.uuid4(),
            code="ck-ok",
            slug="ck-ok",
            group_id=group_id,
            name_i18n={"en": "OK", "ru": "ОК"},
            description_i18n={},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.TEXT_BUTTON,
            is_dictionary=True,
            level=AttributeLevel.PRODUCT,
            search_weight=5,
        )
        db_session.add(a_ok)
        await db_session.flush()  # should succeed


# =========================================================================
# Task 07-03-03: CASCADE and RESTRICT delete behavior verification
# =========================================================================


class TestCascadeDeletes:
    """Verify ON DELETE CASCADE correctly removes child rows."""

    async def test_delete_product_cascades_to_variants(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
        seed_currency,
    ) -> None:
        """Hard-deleting a Product cascades to ProductVariants."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="cascade-variant",
            title_i18n={"en": "Cascade Var", "ru": "Каскад вар"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        product.add_variant(name_i18n={"en": "V2", "ru": "В2"})
        await repo.add(product)
        await db_session.flush()

        # Hard-delete via raw SQL
        await db_session.execute(
            text("DELETE FROM products WHERE id = :id"),
            {"id": str(product.id)},
        )
        await db_session.flush()

        result = await db_session.execute(
            text("SELECT COUNT(*) FROM product_variants WHERE product_id = :id"),
            {"id": str(product.id)},
        )
        assert result.scalar() == 0

    async def test_delete_product_cascades_to_skus(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
        seed_currency,
    ) -> None:
        """Hard-deleting a Product cascades through variants to SKUs."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="cascade-sku",
            title_i18n={"en": "Cascade SKU", "ru": "Каскад SKU"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        product.add_sku(
            product.variants[0].id,
            sku_code="CASCADE-SKU-001",
            price=Money(100, "RUB"),
        )
        await repo.add(product)
        await db_session.flush()

        await db_session.execute(
            text("DELETE FROM products WHERE id = :id"),
            {"id": str(product.id)},
        )
        await db_session.flush()

        result = await db_session.execute(
            text("SELECT COUNT(*) FROM skus WHERE product_id = :id"),
            {"id": str(product.id)},
        )
        assert result.scalar() == 0

    async def test_delete_product_cascades_to_media_assets(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
    ) -> None:
        """Hard-deleting a Product cascades to MediaAssets."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="cascade-media",
            title_i18n={"en": "Cascade Media", "ru": "Каскад медиа"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        await repo.add(product)
        await db_session.flush()

        ma = OrmMediaAsset(
            id=uuid.uuid4(),
            product_id=product.id,
            media_type="IMAGE",
            role="GALLERY",
            sort_order=0,
        )
        db_session.add(ma)
        await db_session.flush()

        await db_session.execute(
            text("DELETE FROM products WHERE id = :id"),
            {"id": str(product.id)},
        )
        await db_session.flush()

        result = await db_session.execute(
            text("SELECT COUNT(*) FROM media_assets WHERE product_id = :id"),
            {"id": str(product.id)},
        )
        assert result.scalar() == 0

    async def test_delete_product_cascades_to_pav(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
        seed_attribute_with_values: dict[str, uuid.UUID],
    ) -> None:
        """Hard-deleting a Product cascades to ProductAttributeValues."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="cascade-pav",
            title_i18n={"en": "Cascade PAV", "ru": "Каскад PAV"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        await repo.add(product)
        await db_session.flush()

        from src.modules.catalog.infrastructure.models import (
            ProductAttributeValue as OrmPAV,
        )

        pav = OrmPAV(
            id=uuid.uuid4(),
            product_id=product.id,
            attribute_id=seed_attribute_with_values["attribute_id"],
            attribute_value_id=seed_attribute_with_values["value_id_1"],
        )
        db_session.add(pav)
        await db_session.flush()

        await db_session.execute(
            text("DELETE FROM products WHERE id = :id"),
            {"id": str(product.id)},
        )
        await db_session.flush()

        result = await db_session.execute(
            text(
                "SELECT COUNT(*) FROM product_attribute_values WHERE product_id = :id"
            ),
            {"id": str(product.id)},
        )
        assert result.scalar() == 0

    async def test_delete_attribute_cascades_to_values(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Hard-deleting an Attribute cascades to AttributeValues."""
        group_id = uuid.uuid4()
        group = OrmAttributeGroup(
            id=group_id,
            code="casc-attr-grp",
            name_i18n={"en": "G", "ru": "Г"},
            sort_order=0,
        )
        db_session.add(group)
        await db_session.flush()

        attr_id = uuid.uuid4()
        attr = OrmAttribute(
            id=attr_id,
            code="casc-attr",
            slug="casc-attr",
            group_id=group_id,
            name_i18n={"en": "A", "ru": "А"},
            description_i18n={},
            data_type=AttributeDataType.STRING,
            ui_type=AttributeUIType.TEXT_BUTTON,
            is_dictionary=True,
            level=AttributeLevel.PRODUCT,
            search_weight=5,
        )
        db_session.add(attr)
        await db_session.flush()

        for i in range(3):
            v = OrmAttributeValue(
                id=uuid.uuid4(),
                attribute_id=attr_id,
                code=f"casc-val-{i}",
                slug=f"casc-val-{i}",
                value_i18n={"en": f"V{i}", "ru": f"З{i}"},
                sort_order=i,
            )
            db_session.add(v)
        await db_session.flush()

        await db_session.execute(
            text("DELETE FROM attributes WHERE id = :id"),
            {"id": str(attr_id)},
        )
        await db_session.flush()

        result = await db_session.execute(
            text("SELECT COUNT(*) FROM attribute_values WHERE attribute_id = :id"),
            {"id": str(attr_id)},
        )
        assert result.scalar() == 0

    async def test_delete_template_cascades_to_bindings(
        self,
        db_session: AsyncSession,
        seed_attribute_with_values: dict[str, uuid.UUID],
    ) -> None:
        """Hard-deleting a Template cascades to Bindings."""
        template_id = uuid.uuid4()
        template = OrmAttributeTemplate(
            id=template_id,
            code="casc-template",
            name_i18n={"en": "T", "ru": "Ш"},
            description_i18n={},
            sort_order=0,
        )
        db_session.add(template)
        await db_session.flush()

        for i in range(2):
            # Need separate attributes for unique constraint
            grp_id = uuid.uuid4()
            grp = OrmAttributeGroup(
                id=grp_id,
                code=f"casc-bind-grp-{i}",
                name_i18n={"en": f"G{i}", "ru": f"Г{i}"},
                sort_order=i,
            )
            db_session.add(grp)
            await db_session.flush()

            a_id = uuid.uuid4()
            a = OrmAttribute(
                id=a_id,
                code=f"casc-bind-attr-{i}",
                slug=f"casc-bind-attr-{i}",
                group_id=grp_id,
                name_i18n={"en": f"A{i}", "ru": f"А{i}"},
                description_i18n={},
                data_type=AttributeDataType.STRING,
                ui_type=AttributeUIType.TEXT_BUTTON,
                is_dictionary=True,
                level=AttributeLevel.PRODUCT,
                search_weight=5,
            )
            db_session.add(a)
            await db_session.flush()

            b = OrmBinding(
                id=uuid.uuid4(),
                template_id=template_id,
                attribute_id=a_id,
                sort_order=i,
                requirement_level=RequirementLevel.OPTIONAL,
            )
            db_session.add(b)
        await db_session.flush()

        await db_session.execute(
            text("DELETE FROM attribute_templates WHERE id = :id"),
            {"id": str(template_id)},
        )
        await db_session.flush()

        result = await db_session.execute(
            text(
                "SELECT COUNT(*) FROM template_attribute_bindings WHERE template_id = :id"
            ),
            {"id": str(template_id)},
        )
        assert result.scalar() == 0


class TestRestrictDeletes:
    """Verify ON DELETE RESTRICT prevents parent deletion when children exist."""

    async def test_cannot_delete_brand_with_products(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
    ) -> None:
        """Deleting a Brand referenced by a Product raises IntegrityError."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="restrict-brand",
            title_i18n={"en": "Restrict Brand", "ru": "Ограничение бренда"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        await repo.add(product)
        await db_session.flush()

        async with db_session.begin_nested():
            with pytest.raises(IntegrityError):
                await db_session.execute(
                    text("DELETE FROM brands WHERE id = :id"),
                    {"id": str(seed_product_deps["brand_id"])},
                )

    async def test_cannot_delete_category_with_products(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
    ) -> None:
        """Deleting a Category referenced by a Product raises IntegrityError."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="restrict-cat",
            title_i18n={"en": "Restrict Cat", "ru": "Ограничение категории"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        await repo.add(product)
        await db_session.flush()

        async with db_session.begin_nested():
            with pytest.raises(IntegrityError):
                await db_session.execute(
                    text("DELETE FROM categories WHERE id = :id"),
                    {"id": str(seed_product_deps["category_id"])},
                )

    async def test_cannot_delete_category_with_children(
        self,
        db_session: AsyncSession,
    ) -> None:
        """Deleting a parent Category with child categories raises IntegrityError."""
        parent = OrmCategory(
            id=uuid.uuid4(),
            parent_id=None,
            slug="parent-restrict",
            full_slug="parent-restrict",
            level=0,
            name_i18n={"en": "Parent", "ru": "Родитель"},
            sort_order=0,
        )
        db_session.add(parent)
        await db_session.flush()

        child = OrmCategory(
            id=uuid.uuid4(),
            parent_id=parent.id,
            slug="child-restrict",
            full_slug="parent-restrict/child-restrict",
            level=1,
            name_i18n={"en": "Child", "ru": "Дочерний"},
            sort_order=0,
        )
        db_session.add(child)
        await db_session.flush()

        async with db_session.begin_nested():
            with pytest.raises(IntegrityError):
                await db_session.execute(
                    text("DELETE FROM categories WHERE id = :id"),
                    {"id": str(parent.id)},
                )
