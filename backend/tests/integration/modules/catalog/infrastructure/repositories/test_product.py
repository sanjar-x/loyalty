"""
Integration tests for ProductRepository Data Mapper roundtrips.

Proves that the full Product aggregate hierarchy (Product -> ProductVariant
-> SKU -> SKUAttributeValueLink) survives create-read-update-delete cycles
through real PostgreSQL. Validates Money VO decomposition, JSONB i18n,
nullable fields, enum mapping, variant sync, and N+1 query detection.

Part of Phase 07 -- Repository & Data Integrity (REPO-01, REPO-05).
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.entities import Product
from src.modules.catalog.domain.value_objects import Money, ProductStatus
from src.modules.catalog.infrastructure.repositories.product import ProductRepository
from tests.utils.query_counter import assert_query_count

# =========================================================================
# Task 07-01-02: Product create-read roundtrip with full field verification
# =========================================================================


class TestProductCreateReadRoundtrip:
    """Verify Product aggregate survives full create-read roundtrip."""

    async def test_product_basic_roundtrip(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
    ) -> None:
        """All Product scalar fields survive ORM roundtrip."""
        # Arrange
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="basic-roundtrip",
            title_i18n={"en": "Basic Product", "ru": "Базовый продукт"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        await repo.add(product)
        await db_session.flush()

        # Act
        fetched = await repo.get_with_variants(product.id)

        # Assert
        assert fetched is not None
        assert fetched.id == product.id
        assert fetched.slug == "basic-roundtrip"
        assert fetched.title_i18n == {"en": "Basic Product", "ru": "Базовый продукт"}
        assert fetched.description_i18n == {}
        assert fetched.status == ProductStatus.DRAFT
        assert fetched.brand_id == seed_product_deps["brand_id"]
        assert fetched.primary_category_id == seed_product_deps["category_id"]
        assert fetched.supplier_id is None
        assert fetched.country_of_origin is None
        assert list(fetched.tags) == []
        assert fetched.source_url is None
        assert fetched.published_at is None
        assert fetched.deleted_at is None
        # Default variant is auto-created by Product.create()
        assert len(fetched.variants) == 1

    async def test_product_with_variant_and_sku_roundtrip(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
        seed_currency,
    ) -> None:
        """3-level hierarchy (Product->Variant->SKU) survives roundtrip."""
        # Arrange
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="with-sku",
            title_i18n={"en": "SKU Product", "ru": "Продукт с SKU"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        # Use the default variant (auto-created)
        default_variant = product.variants[0]
        sku = product.add_sku(
            default_variant.id,
            sku_code="TEST-001",
            price=Money(10000, "RUB"),
            compare_at_price=Money(15000, "RUB"),
            is_active=True,
        )
        await repo.add(product)
        await db_session.flush()

        # Act
        fetched = await repo.get_with_variants(product.id)

        # Assert
        assert fetched is not None
        assert len(fetched.variants) == 1
        variant = fetched.variants[0]
        assert variant.name_i18n == {"en": "SKU Product", "ru": "Продукт с SKU"}
        assert len(variant.skus) == 1
        fetched_sku = variant.skus[0]
        assert fetched_sku.sku_code == "TEST-001"
        assert fetched_sku.price is not None
        assert fetched_sku.price.amount == 10000
        assert fetched_sku.price.currency == "RUB"
        assert fetched_sku.compare_at_price is not None
        assert fetched_sku.compare_at_price.amount == 15000
        assert fetched_sku.compare_at_price.currency == "RUB"
        assert fetched_sku.is_active is True

    async def test_product_jsonb_fields_roundtrip(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
    ) -> None:
        """JSONB fields (title_i18n, description_i18n) and ARRAY (tags) roundtrip."""
        # Arrange
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="jsonb-test",
            title_i18n={"en": "Test Product", "ru": "Тестовый продукт"},
            description_i18n={"en": "Description", "ru": "Описание"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
            tags=["sale", "new"],
        )
        await repo.add(product)
        await db_session.flush()

        # Act
        fetched = await repo.get_with_variants(product.id)

        # Assert
        assert fetched is not None
        assert fetched.title_i18n == {"en": "Test Product", "ru": "Тестовый продукт"}
        assert fetched.description_i18n == {"en": "Description", "ru": "Описание"}
        assert list(fetched.tags) == ["sale", "new"]

    async def test_product_nullable_fields_roundtrip(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
    ) -> None:
        """Nullable fields preserve None and non-None values."""
        # Arrange
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="nullable-test",
            title_i18n={"en": "Nullable Product", "ru": "Продукт с нулями"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
            supplier_id=None,
            source_url=None,
            country_of_origin=None,
        )
        await repo.add(product)
        await db_session.flush()

        # Act
        fetched = await repo.get_with_variants(product.id)

        # Assert -- None values preserved
        assert fetched is not None
        assert fetched.supplier_id is None
        assert fetched.source_url is None
        assert fetched.country_of_origin is None
        assert fetched.published_at is None

        # Now test with non-None values
        product2 = Product.create(
            slug="non-nullable-test",
            title_i18n={"en": "Non-Null Product", "ru": "Продукт без нулей"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
            source_url="https://example.com",
            country_of_origin="CN",
        )
        await repo.add(product2)
        await db_session.flush()

        fetched2 = await repo.get_with_variants(product2.id)
        assert fetched2 is not None
        assert fetched2.source_url == "https://example.com"
        assert fetched2.country_of_origin == "CN"

    async def test_product_status_enum_roundtrip(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
    ) -> None:
        """ProductStatus.DRAFT survives roundtrip as StrEnum."""
        # Arrange
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="status-test",
            title_i18n={"en": "Status Product", "ru": "Продукт статус"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        await repo.add(product)
        await db_session.flush()

        # Act
        fetched = await repo.get_with_variants(product.id)

        # Assert
        assert fetched is not None
        assert fetched.status == ProductStatus.DRAFT
        assert isinstance(fetched.status, ProductStatus)


# =========================================================================
# Task 07-01-03: Money VO decomposition and SKU attribute value link roundtrip
# =========================================================================


class TestMoneyVODecomposition:
    """Verify Money VO decomposition to/from integer + currency columns."""

    async def test_sku_price_money_roundtrip(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
        seed_currency,
    ) -> None:
        """SKU price Money(9900, 'RUB') survives roundtrip."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="sku-price-money",
            title_i18n={"en": "Price Test", "ru": "Тест цены"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        default_variant = product.variants[0]
        product.add_sku(
            default_variant.id,
            sku_code="PRICE-001",
            price=Money(9900, "RUB"),
        )
        await repo.add(product)
        await db_session.flush()

        fetched = await repo.get_with_variants(product.id)
        assert fetched is not None
        sku = fetched.variants[0].skus[0]
        assert sku.price is not None
        assert sku.price.amount == 9900
        assert sku.price.currency == "RUB"

    async def test_sku_nullable_price_roundtrip(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
        seed_currency,
    ) -> None:
        """SKU with price=None survives roundtrip as None."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="sku-null-price",
            title_i18n={"en": "Null Price", "ru": "Нулевая цена"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        default_variant = product.variants[0]
        product.add_sku(
            default_variant.id,
            sku_code="NULL-PRICE-001",
            price=None,
        )
        await repo.add(product)
        await db_session.flush()

        fetched = await repo.get_with_variants(product.id)
        assert fetched is not None
        sku = fetched.variants[0].skus[0]
        assert sku.price is None

    async def test_sku_compare_at_price_roundtrip(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
        seed_currency,
    ) -> None:
        """SKU compare_at_price Money(15000, 'RUB') survives roundtrip."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="sku-compare-price",
            title_i18n={"en": "Compare Price", "ru": "Цена сравнения"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        default_variant = product.variants[0]
        product.add_sku(
            default_variant.id,
            sku_code="COMPARE-001",
            price=Money(10000, "RUB"),
            compare_at_price=Money(15000, "RUB"),
        )
        await repo.add(product)
        await db_session.flush()

        fetched = await repo.get_with_variants(product.id)
        assert fetched is not None
        sku = fetched.variants[0].skus[0]
        assert sku.compare_at_price is not None
        assert sku.compare_at_price.amount == 15000

    async def test_sku_compare_at_price_none_roundtrip(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
        seed_currency,
    ) -> None:
        """SKU with compare_at_price=None survives as None."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="sku-no-compare",
            title_i18n={"en": "No Compare", "ru": "Без сравнения"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        default_variant = product.variants[0]
        product.add_sku(
            default_variant.id,
            sku_code="NO-COMPARE-001",
            price=Money(5000, "RUB"),
            compare_at_price=None,
        )
        await repo.add(product)
        await db_session.flush()

        fetched = await repo.get_with_variants(product.id)
        assert fetched is not None
        sku = fetched.variants[0].skus[0]
        assert sku.compare_at_price is None

    async def test_variant_default_price_money_roundtrip(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
        seed_currency,
    ) -> None:
        """Variant default_price Money(5000, 'RUB') survives roundtrip."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="variant-price",
            title_i18n={"en": "Variant Price", "ru": "Цена варианта"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        product.add_variant(
            name_i18n={"en": "With Price", "ru": "С ценой"},
            default_price=Money(5000, "RUB"),
        )
        await repo.add(product)
        await db_session.flush()

        fetched = await repo.get_with_variants(product.id)
        assert fetched is not None
        # Find the variant we added (not the default one)
        priced_variants = [v for v in fetched.variants if v.default_price is not None]
        assert len(priced_variants) == 1
        assert priced_variants[0].default_price.amount == 5000
        assert priced_variants[0].default_price.currency == "RUB"

    async def test_variant_default_price_none_roundtrip(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
        seed_currency,
    ) -> None:
        """Variant with default_price=None survives as None."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="variant-no-price",
            title_i18n={"en": "No Price Variant", "ru": "Вариант без цены"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        await repo.add(product)
        await db_session.flush()

        fetched = await repo.get_with_variants(product.id)
        assert fetched is not None
        # Default variant has no price
        assert fetched.variants[0].default_price is None


class TestSKUAttributeValueLinks:
    """Verify SKU variant_attributes (link table) roundtrip."""

    async def test_sku_variant_attributes_roundtrip(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
        seed_currency,
        seed_attribute_with_values: dict[str, uuid.UUID],
    ) -> None:
        """SKU variant_attributes list survives roundtrip."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="sku-attrs",
            title_i18n={"en": "SKU Attrs", "ru": "СКУ атрибуты"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        default_variant = product.variants[0]
        attr_id = seed_attribute_with_values["attribute_id"]
        val_id_1 = seed_attribute_with_values["value_id_1"]
        product.add_sku(
            default_variant.id,
            sku_code="ATTR-SKU-001",
            price=Money(1000, "RUB"),
            variant_attributes=[(attr_id, val_id_1)],
        )
        await repo.add(product)
        await db_session.flush()

        fetched = await repo.get_with_variants(product.id)
        assert fetched is not None
        sku = fetched.variants[0].skus[0]
        # Compare as sets since order may differ
        assert set(sku.variant_attributes) == {(attr_id, val_id_1)}

    async def test_sku_empty_variant_attributes(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
        seed_currency,
    ) -> None:
        """SKU with empty variant_attributes survives roundtrip."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="sku-no-attrs",
            title_i18n={"en": "No Attrs", "ru": "Без атрибутов"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        default_variant = product.variants[0]
        product.add_sku(
            default_variant.id,
            sku_code="NO-ATTR-001",
            price=Money(1000, "RUB"),
            variant_attributes=[],
        )
        await repo.add(product)
        await db_session.flush()

        fetched = await repo.get_with_variants(product.id)
        assert fetched is not None
        sku = fetched.variants[0].skus[0]
        assert sku.variant_attributes == []


# =========================================================================
# Task 07-01-04: Product update with variant sync and N+1 query detection
# =========================================================================


class TestProductUpdate:
    """Verify ProductRepository.update() with variant sync."""

    async def test_update_product_scalar_fields(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
    ) -> None:
        """Updated scalar fields survive roundtrip."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="update-test",
            title_i18n={"en": "Original", "ru": "Оригинал"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        await repo.add(product)
        await db_session.flush()

        # Act
        product.update(
            title_i18n={"en": "Updated", "ru": "Обновлено"},
            description_i18n={"en": "New Desc", "ru": "Новое описание"},
            tags=["updated"],
        )
        await repo.update(product)
        await db_session.flush()

        fetched = await repo.get_with_variants(product.id)

        # Assert
        assert fetched is not None
        assert fetched.title_i18n == {"en": "Updated", "ru": "Обновлено"}
        assert fetched.description_i18n == {"en": "New Desc", "ru": "Новое описание"}
        assert list(fetched.tags) == ["updated"]

    async def test_update_add_variant(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
        seed_currency,
    ) -> None:
        """Adding a variant via update() makes it appear in read-back."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="add-variant-test",
            title_i18n={"en": "Add Variant", "ru": "Добавить вариант"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        await repo.add(product)
        await db_session.flush()
        assert len(product.variants) == 1  # default variant

        # Act
        product.add_variant(
            name_i18n={"en": "New Variant", "ru": "Новый вариант"},
            default_price=Money(3000, "RUB"),
        )
        await repo.update(product)
        await db_session.flush()

        fetched = await repo.get_with_variants(product.id)

        # Assert
        assert fetched is not None
        assert len(fetched.variants) == 2

    async def test_update_remove_variant(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
        seed_currency,
    ) -> None:
        """Soft-deleted variant is filtered by get_with_variants."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="remove-variant-test",
            title_i18n={"en": "Remove Variant", "ru": "Удалить вариант"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        variant2 = product.add_variant(
            name_i18n={"en": "Variant 2", "ru": "Вариант 2"},
        )
        await repo.add(product)
        await db_session.flush()
        assert len(product.variants) == 2

        # Act -- remove the second variant
        product.remove_variant(variant2.id)
        await repo.update(product)
        await db_session.flush()

        fetched = await repo.get_with_variants(product.id)

        # Assert
        assert fetched is not None
        assert len(fetched.variants) == 1

    async def test_update_add_sku_to_variant(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
        seed_currency,
    ) -> None:
        """Adding a SKU to a variant via update() makes it appear in read-back."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="add-sku-test",
            title_i18n={"en": "Add SKU", "ru": "Добавить SKU"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        await repo.add(product)
        await db_session.flush()

        # Act
        default_variant = product.variants[0]
        product.add_sku(
            default_variant.id,
            sku_code="NEW-SKU-001",
            price=Money(7777, "RUB"),
        )
        await repo.update(product)
        await db_session.flush()

        fetched = await repo.get_with_variants(product.id)

        # Assert
        assert fetched is not None
        assert len(fetched.variants[0].skus) == 1
        assert fetched.variants[0].skus[0].sku_code == "NEW-SKU-001"


class TestProductQueryCount:
    """Verify bounded query count on get_with_variants."""

    async def test_get_with_variants_bounded_queries(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
        seed_currency,
    ) -> None:
        """get_with_variants() uses a bounded number of queries via selectinload."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="query-count-test",
            title_i18n={"en": "Query Count", "ru": "Счетчик запросов"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        v1 = product.variants[0]
        product.add_sku(v1.id, sku_code="QC-001", price=Money(100, "RUB"))
        product.add_sku(v1.id, sku_code="QC-002", price=Money(200, "RUB"))
        v2 = product.add_variant(name_i18n={"en": "V2", "ru": "В2"})
        product.add_sku(v2.id, sku_code="QC-003", price=Money(300, "RUB"))
        product.add_sku(v2.id, sku_code="QC-004", price=Money(400, "RUB"))
        await repo.add(product)
        await db_session.flush()

        # Expire all cached state to force DB reads
        db_session.expire_all()

        # Act & Assert -- bounded queries (product + variants + skus + sku_attr_values)
        # selectinload issues 1 query per relationship level: 4 total
        async with assert_query_count(
            db_session, expected=4, label="get_with_variants"
        ):
            result = await repo.get_with_variants(product.id)

        assert result is not None
        assert len(result.variants) == 2


# =========================================================================
# Task 07-01-05: Product delete and get methods verification
# =========================================================================


class TestProductDelete:
    """Verify ProductRepository delete and get edge cases."""

    async def test_delete_product(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
    ) -> None:
        """Hard-delete removes product from repository."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="delete-test",
            title_i18n={"en": "Delete Me", "ru": "Удалить меня"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        await repo.add(product)
        await db_session.flush()

        # Act
        await repo.delete(product.id)
        await db_session.flush()

        # Assert
        fetched = await repo.get(product.id)
        assert fetched is None

    async def test_get_returns_none_for_missing(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
    ) -> None:
        """get() returns None for non-existent ID."""
        repo = ProductRepository(session=db_session)
        fetched = await repo.get(uuid.uuid4())
        assert fetched is None

    async def test_get_excludes_soft_deleted(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
    ) -> None:
        """get() returns None for soft-deleted Product."""
        from sqlalchemy import text

        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="soft-delete-get",
            title_i18n={"en": "Soft Delete", "ru": "Мягкое удаление"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        await repo.add(product)
        await db_session.flush()

        # Soft-delete via raw SQL to bypass domain guards
        await db_session.execute(
            text("UPDATE products SET deleted_at = NOW() WHERE id = :id"),
            {"id": str(product.id)},
        )
        await db_session.flush()

        # Act
        fetched = await repo.get(product.id)

        # Assert
        assert fetched is None

    async def test_get_with_variants_excludes_soft_deleted(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
    ) -> None:
        """get_with_variants() returns None for soft-deleted Product."""
        from sqlalchemy import text

        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="soft-delete-variants",
            title_i18n={"en": "Soft Delete V", "ru": "Мягкое удаление В"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        await repo.add(product)
        await db_session.flush()

        await db_session.execute(
            text("UPDATE products SET deleted_at = NOW() WHERE id = :id"),
            {"id": str(product.id)},
        )
        await db_session.flush()

        # Act
        fetched = await repo.get_with_variants(product.id)

        # Assert
        assert fetched is None


class TestProductSlugChecks:
    """Verify slug existence checks."""

    async def test_check_slug_exists(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
    ) -> None:
        """check_slug_exists returns True/False correctly."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="slug-check-test",
            title_i18n={"en": "Slug Check", "ru": "Проверка слага"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        await repo.add(product)
        await db_session.flush()

        assert await repo.check_slug_exists("slug-check-test") is True
        assert await repo.check_slug_exists("other-slug") is False

    async def test_check_slug_exists_excluding(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
    ) -> None:
        """check_slug_exists_excluding excludes self."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="slug-exclude-test",
            title_i18n={"en": "Slug Exclude", "ru": "Исключение слага"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        await repo.add(product)
        await db_session.flush()

        # Self excluded -- returns False
        assert (
            await repo.check_slug_exists_excluding("slug-exclude-test", product.id)
            is False
        )
        # Different ID -- slug is taken
        assert (
            await repo.check_slug_exists_excluding("slug-exclude-test", uuid.uuid4())
            is True
        )

    async def test_check_slug_ignores_soft_deleted(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
    ) -> None:
        """check_slug_exists returns False for soft-deleted product."""
        from sqlalchemy import text

        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="soft-slug-test",
            title_i18n={"en": "Soft Slug", "ru": "Мягкий слаг"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        await repo.add(product)
        await db_session.flush()

        await db_session.execute(
            text("UPDATE products SET deleted_at = NOW() WHERE id = :id"),
            {"id": str(product.id)},
        )
        await db_session.flush()

        assert await repo.check_slug_exists("soft-slug-test") is False


class TestSKUCodeChecks:
    """Verify SKU code existence checks."""

    async def test_check_sku_code_exists(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
        seed_currency,
    ) -> None:
        """check_sku_code_exists returns True/False correctly."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="sku-code-check",
            title_i18n={"en": "SKU Code Check", "ru": "Проверка кода SKU"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        default_variant = product.variants[0]
        product.add_sku(
            default_variant.id,
            sku_code="SKU-CHECK-001",
            price=Money(1000, "RUB"),
        )
        await repo.add(product)
        await db_session.flush()

        assert await repo.check_sku_code_exists("SKU-CHECK-001") is True
        assert await repo.check_sku_code_exists("SKU-999") is False

    async def test_check_sku_code_excludes_soft_deleted(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
        seed_currency,
    ) -> None:
        """check_sku_code_exists returns False for soft-deleted SKU."""
        from sqlalchemy import text

        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="sku-soft-check",
            title_i18n={"en": "Soft SKU", "ru": "Мягкий SKU"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        default_variant = product.variants[0]
        sku = product.add_sku(
            default_variant.id,
            sku_code="SOFT-SKU-001",
            price=Money(1000, "RUB"),
        )
        await repo.add(product)
        await db_session.flush()

        # Soft-delete the SKU via raw SQL
        await db_session.execute(
            text("UPDATE skus SET deleted_at = NOW() WHERE id = :id"),
            {"id": str(sku.id)},
        )
        await db_session.flush()

        assert await repo.check_sku_code_exists("SOFT-SKU-001") is False
