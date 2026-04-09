"""
Integration tests verifying soft-delete filtering across all repository read methods.

Proves that every ProductRepository read method correctly excludes soft-deleted
records and that BrandRepository/CategoryRepository has_products methods are
soft-delete-aware.

Part of Phase 07 -- Repository & Data Integrity (REPO-04).
"""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.entities import Brand, Category, Product
from src.modules.catalog.domain.value_objects import Money
from src.modules.catalog.infrastructure.repositories.brand import BrandRepository
from src.modules.catalog.infrastructure.repositories.category import CategoryRepository
from src.modules.catalog.infrastructure.repositories.product import ProductRepository


class TestProductSoftDeleteFiltering:
    """Verify all ProductRepository read methods filter soft-deleted records."""

    async def test_get_excludes_soft_deleted(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
    ) -> None:
        """get() returns None for soft-deleted, not-None for active."""
        repo = ProductRepository(session=db_session)
        active = Product.create(
            slug="sd-active",
            title_i18n={"en": "Active", "ru": "Активный"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        deleted = Product.create(
            slug="sd-deleted",
            title_i18n={"en": "Deleted", "ru": "Удалённый"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        await repo.add(active)
        await repo.add(deleted)
        await db_session.flush()

        await db_session.execute(
            text("UPDATE products SET deleted_at = NOW() WHERE id = :id"),
            {"id": str(deleted.id)},
        )
        await db_session.flush()

        assert await repo.get(deleted.id) is None
        assert await repo.get(active.id) is not None

    async def test_get_with_variants_excludes_soft_deleted_product(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
    ) -> None:
        """get_with_variants() returns None for soft-deleted Product."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="sd-gwv-product",
            title_i18n={"en": "GWV Deleted", "ru": "GWV Удалённый"},
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

        assert await repo.get_with_variants(product.id) is None

    async def test_get_with_variants_excludes_soft_deleted_variants(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
        seed_currency,
    ) -> None:
        """get_with_variants() filters soft-deleted variants within active product."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="sd-variant-filter",
            title_i18n={"en": "Variant Filter", "ru": "Фильтр вариантов"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        v2 = product.add_variant(name_i18n={"en": "V2", "ru": "В2"})
        await repo.add(product)
        await db_session.flush()

        # Soft-delete variant 2
        await db_session.execute(
            text("UPDATE product_variants SET deleted_at = NOW() WHERE id = :id"),
            {"id": str(v2.id)},
        )
        await db_session.flush()

        fetched = await repo.get_with_variants(product.id)
        assert fetched is not None
        assert len(fetched.variants) == 1  # only the default variant

    async def test_get_with_variants_excludes_soft_deleted_skus(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
        seed_currency,
    ) -> None:
        """get_with_variants() filters soft-deleted SKUs within active variant."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="sd-sku-filter",
            title_i18n={"en": "SKU Filter", "ru": "Фильтр SKU"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        default_variant = product.variants[0]
        sku1 = product.add_sku(
            default_variant.id,
            sku_code="SD-SKU-ACTIVE",
            price=Money(100, "RUB"),
        )
        sku2 = product.add_sku(
            default_variant.id,
            sku_code="SD-SKU-DELETED",
            price=Money(200, "RUB"),
        )
        await repo.add(product)
        await db_session.flush()

        # Soft-delete SKU 2
        await db_session.execute(
            text("UPDATE skus SET deleted_at = NOW() WHERE id = :id"),
            {"id": str(sku2.id)},
        )
        await db_session.flush()

        fetched = await repo.get_with_variants(product.id)
        assert fetched is not None
        assert len(fetched.variants[0].skus) == 1
        assert fetched.variants[0].skus[0].sku_code == "SD-SKU-ACTIVE"

    async def test_get_for_update_with_variants_excludes_soft_deleted(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
        seed_currency,
    ) -> None:
        """get_for_update_with_variants() filters soft-deleted variants."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="sd-foru-filter",
            title_i18n={"en": "ForU Filter", "ru": "ФорУ Фильтр"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        v2 = product.add_variant(name_i18n={"en": "ForU V2", "ru": "ФорУ В2"})
        await repo.add(product)
        await db_session.flush()

        await db_session.execute(
            text("UPDATE product_variants SET deleted_at = NOW() WHERE id = :id"),
            {"id": str(v2.id)},
        )
        await db_session.flush()

        fetched = await repo.get_for_update_with_variants(product.id)
        assert fetched is not None
        assert len(fetched.variants) == 1

    async def test_check_slug_exists_excludes_soft_deleted(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
    ) -> None:
        """check_slug_exists returns False for soft-deleted product."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="sd-slug-check",
            title_i18n={"en": "SD Slug", "ru": "МУ Слаг"},
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

        assert await repo.check_slug_exists("sd-slug-check") is False

        # Active product should still be found
        active = Product.create(
            slug="sd-slug-active",
            title_i18n={"en": "Active Slug", "ru": "Активный слаг"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        await repo.add(active)
        await db_session.flush()
        assert await repo.check_slug_exists("sd-slug-active") is True

    async def test_check_slug_exists_excluding_excludes_soft_deleted(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
    ) -> None:
        """check_slug_exists_excluding returns False for soft-deleted."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="sd-slug-excl",
            title_i18n={"en": "SD Slug Excl", "ru": "МУ Слаг Искл"},
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

        # Even with a different exclude_id, soft-deleted slug should not be found
        assert (
            await repo.check_slug_exists_excluding("sd-slug-excl", uuid.uuid4())
            is False
        )

    async def test_check_sku_code_exists_excludes_soft_deleted(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
        seed_currency,
    ) -> None:
        """check_sku_code_exists returns False for soft-deleted SKU."""
        repo = ProductRepository(session=db_session)
        product = Product.create(
            slug="sd-sku-code",
            title_i18n={"en": "SD SKU Code", "ru": "МУ Код SKU"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=seed_product_deps["category_id"],
        )
        sku = product.add_sku(
            product.variants[0].id,
            sku_code="SD-CODE-001",
            price=Money(100, "RUB"),
        )
        await repo.add(product)
        await db_session.flush()

        await db_session.execute(
            text("UPDATE skus SET deleted_at = NOW() WHERE id = :id"),
            {"id": str(sku.id)},
        )
        await db_session.flush()

        assert await repo.check_sku_code_exists("SD-CODE-001") is False


class TestRelatedEntitySoftDeleteAwareness:
    """Verify has_products on Brand/Category exclude soft-deleted products."""

    async def test_brand_has_products_excludes_soft_deleted(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
    ) -> None:
        """BrandRepository.has_products returns False when only soft-deleted products exist."""
        brand_repo = BrandRepository(session=db_session)
        product_repo = ProductRepository(session=db_session)

        # Create a new brand for isolation
        brand = Brand.create(name="SD Brand Test", slug="sd-brand-test")
        await brand_repo.add(brand)
        await db_session.flush()

        product = Product.create(
            slug="sd-brand-product",
            title_i18n={"en": "Brand Product", "ru": "Продукт бренда"},
            brand_id=brand.id,
            primary_category_id=seed_product_deps["category_id"],
        )
        await product_repo.add(product)
        await db_session.flush()

        # Soft-delete the product
        await db_session.execute(
            text("UPDATE products SET deleted_at = NOW() WHERE id = :id"),
            {"id": str(product.id)},
        )
        await db_session.flush()

        assert await brand_repo.has_products(brand.id) is False

        # Create an active product
        active = Product.create(
            slug="sd-brand-active",
            title_i18n={"en": "Active Brand", "ru": "Активный бренд"},
            brand_id=brand.id,
            primary_category_id=seed_product_deps["category_id"],
        )
        await product_repo.add(active)
        await db_session.flush()

        assert await brand_repo.has_products(brand.id) is True

    async def test_category_has_products_excludes_soft_deleted(
        self,
        db_session: AsyncSession,
        seed_product_deps: dict[str, uuid.UUID],
    ) -> None:
        """CategoryRepository.has_products returns False when only soft-deleted products exist."""
        cat_repo = CategoryRepository(session=db_session)
        product_repo = ProductRepository(session=db_session)

        # Create a new category for isolation
        cat = Category.create_root(
            name_i18n={"en": "SD Category", "ru": "МУ Категория"},
            slug="sd-category-test",
        )
        await cat_repo.add(cat)
        await db_session.flush()

        product = Product.create(
            slug="sd-cat-product",
            title_i18n={"en": "Cat Product", "ru": "Продукт категории"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=cat.id,
        )
        await product_repo.add(product)
        await db_session.flush()

        # Soft-delete
        await db_session.execute(
            text("UPDATE products SET deleted_at = NOW() WHERE id = :id"),
            {"id": str(product.id)},
        )
        await db_session.flush()

        assert await cat_repo.has_products(cat.id) is False

        # Create active product
        active = Product.create(
            slug="sd-cat-active",
            title_i18n={"en": "Active Cat", "ru": "Активная категория"},
            brand_id=seed_product_deps["brand_id"],
            primary_category_id=cat.id,
        )
        await product_repo.add(active)
        await db_session.flush()

        assert await cat_repo.has_products(cat.id) is True
