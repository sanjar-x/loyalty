"""Unit tests for ProductRepository (Data Mapper).

Tests the repository's mapper methods (_to_domain, _to_domain_without_skus,
_to_orm, _sku_to_domain, _sku_to_orm, _sync_skus) and verifies that each
public method delegates to the correct SQLAlchemy session operations.
Uses AsyncMock for the session -- no database required.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.orm.exc import StaleDataError

from src.modules.catalog.domain.entities import SKU as DomainSKU
from src.modules.catalog.domain.entities import Product as DomainProduct
from src.modules.catalog.domain.exceptions import ConcurrencyError
from src.modules.catalog.domain.interfaces import IProductRepository
from src.modules.catalog.domain.value_objects import Money
from src.modules.catalog.domain.value_objects import ProductStatus as DomainProductStatus
from src.modules.catalog.infrastructure.models import SKU as OrmSKU
from src.modules.catalog.infrastructure.models import Product as OrmProduct
from src.modules.catalog.infrastructure.models import ProductStatus as OrmProductStatus
from src.modules.catalog.infrastructure.models import SKUAttributeValueLink as OrmSKUAttrLink
from src.modules.catalog.infrastructure.repositories.product import ProductRepository

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime.now(UTC)


def _make_orm_sku(
    sku_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
    price: int = 10000,
    compare_at_price: int | None = None,
    currency: str = "RUB",
    variant_attributes: list[tuple[uuid.UUID, uuid.UUID]] | None = None,
) -> OrmSKU:
    """Build an ORM SKU with given or default values."""
    orm = OrmSKU()
    orm.id = sku_id or uuid.uuid4()
    orm.product_id = product_id or uuid.uuid4()
    orm.sku_code = f"SKU-{uuid.uuid4().hex[:6]}"
    orm.variant_hash = uuid.uuid4().hex
    orm.price = price
    orm.compare_at_price = compare_at_price
    orm.currency = currency
    orm.is_active = True
    orm.version = 1
    orm.deleted_at = None
    orm.created_at = _NOW
    orm.updated_at = _NOW
    orm.main_image_url = None
    orm.attributes_cache = {}

    # Build attribute_values relationship mock
    links = []
    if variant_attributes:
        for attr_id, attr_val_id in variant_attributes:
            link = OrmSKUAttrLink()
            link.sku_id = orm.id
            link.attribute_id = attr_id
            link.attribute_value_id = attr_val_id
            links.append(link)
    orm.attribute_values = links
    return orm


def _make_orm_product(
    product_id: uuid.UUID | None = None,
    slug: str = "test-product",
    status: OrmProductStatus = OrmProductStatus.DRAFT,
    skus: list[OrmSKU] | None = None,
    deleted_at: datetime | None = None,
) -> OrmProduct:
    """Build an ORM Product with given or default values."""
    orm = OrmProduct()
    orm.id = product_id or uuid.uuid4()
    orm.slug = slug
    orm.title_i18n = {"en": "Test Product"}
    orm.description_i18n = {"en": "A test product description"}
    orm.status = status
    orm.brand_id = uuid.uuid4()
    orm.primary_category_id = uuid.uuid4()
    orm.supplier_id = uuid.uuid4()
    orm.country_of_origin = "US"
    orm.tags = ["tag1", "tag2"]
    orm.version = 1
    orm.deleted_at = deleted_at
    orm.created_at = _NOW
    orm.updated_at = _NOW
    orm.published_at = None
    orm.popularity_score = 0
    orm.is_visible = True
    orm.source_url = None
    orm.attributes = {}
    orm.skus = skus if skus is not None else []
    return orm


def _make_domain_product(
    product_id: uuid.UUID | None = None,
    slug: str = "test-product",
    status: DomainProductStatus = DomainProductStatus.DRAFT,
    skus: list[DomainSKU] | None = None,
) -> DomainProduct:
    """Build a domain Product with given or default values."""
    pid = product_id or uuid.uuid4()
    return DomainProduct(
        id=pid,
        slug=slug,
        title_i18n={"en": "Test Product"},
        description_i18n={"en": "A test product description"},
        status=status,
        brand_id=uuid.uuid4(),
        primary_category_id=uuid.uuid4(),
        supplier_id=uuid.uuid4(),
        country_of_origin="US",
        tags=["tag1", "tag2"],
        version=1,
        deleted_at=None,
        created_at=_NOW,
        updated_at=_NOW,
        published_at=None,
        skus=skus or [],
    )


def _make_domain_sku(
    sku_id: uuid.UUID | None = None,
    product_id: uuid.UUID | None = None,
    price: Money | None = None,
    compare_at_price: Money | None = None,
    variant_attributes: list[tuple[uuid.UUID, uuid.UUID]] | None = None,
) -> DomainSKU:
    """Build a domain SKU with given or default values."""
    return DomainSKU(
        id=sku_id or uuid.uuid4(),
        product_id=product_id or uuid.uuid4(),
        sku_code=f"SKU-{uuid.uuid4().hex[:6]}",
        variant_hash=uuid.uuid4().hex,
        price=price or Money(amount=10000, currency="RUB"),
        compare_at_price=compare_at_price,
        is_active=True,
        version=1,
        deleted_at=None,
        created_at=_NOW,
        updated_at=_NOW,
        variant_attributes=variant_attributes or [],
    )


# ---------------------------------------------------------------------------
# Contract compliance
# ---------------------------------------------------------------------------


class TestRepositoryContract:
    """ProductRepository implements the IProductRepository interface."""

    def test_implements_interface(self) -> None:
        """Repository is a subclass of IProductRepository."""
        assert issubclass(ProductRepository, IProductRepository)

    def test_has_add_method(self) -> None:
        """Repository exposes an async 'add' method."""
        assert callable(getattr(ProductRepository, "add", None))

    def test_has_get_method(self) -> None:
        """Repository exposes an async 'get' method."""
        assert callable(getattr(ProductRepository, "get", None))

    def test_has_update_method(self) -> None:
        """Repository exposes an async 'update' method."""
        assert callable(getattr(ProductRepository, "update", None))

    def test_has_delete_method(self) -> None:
        """Repository exposes an async 'delete' method."""
        assert callable(getattr(ProductRepository, "delete", None))

    def test_has_get_by_slug_method(self) -> None:
        """Repository exposes an async 'get_by_slug' method."""
        assert callable(getattr(ProductRepository, "get_by_slug", None))

    def test_has_check_slug_exists_method(self) -> None:
        """Repository exposes 'check_slug_exists' method."""
        assert callable(getattr(ProductRepository, "check_slug_exists", None))

    def test_has_check_slug_exists_excluding_method(self) -> None:
        """Repository exposes 'check_slug_exists_excluding' method."""
        assert callable(getattr(ProductRepository, "check_slug_exists_excluding", None))

    def test_has_get_for_update_method(self) -> None:
        """Repository exposes 'get_for_update' method."""
        assert callable(getattr(ProductRepository, "get_for_update", None))

    def test_has_get_with_skus_method(self) -> None:
        """Repository exposes 'get_with_skus' method."""
        assert callable(getattr(ProductRepository, "get_with_skus", None))

    def test_has_list_products_method(self) -> None:
        """Repository exposes 'list_products' method."""
        assert callable(getattr(ProductRepository, "list_products", None))


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


class TestConstructor:
    """Tests for repository initialization."""

    def test_stores_session(self) -> None:
        """Repository stores the provided session as _session."""
        session = AsyncMock()
        repo = ProductRepository(session=session)
        assert repo._session is session


# ---------------------------------------------------------------------------
# SKU mapper tests: _sku_to_domain
# ---------------------------------------------------------------------------


class TestSkuToDomain:
    """Tests for _sku_to_domain: ORM SKU -> domain SKU."""

    def test_maps_price_to_money_vo(self) -> None:
        """Price integer + currency are composed into a Money VO."""
        orm_sku = _make_orm_sku(price=15000, currency="USD")
        repo = ProductRepository(session=AsyncMock())

        domain_sku = repo._sku_to_domain(orm_sku)

        assert isinstance(domain_sku.price, Money)
        assert domain_sku.price.amount == 15000
        assert domain_sku.price.currency == "USD"

    def test_maps_compare_at_price_when_present(self) -> None:
        """compare_at_price is composed into a Money VO when non-null."""
        orm_sku = _make_orm_sku(price=10000, compare_at_price=20000, currency="RUB")
        repo = ProductRepository(session=AsyncMock())

        domain_sku = repo._sku_to_domain(orm_sku)

        assert domain_sku.compare_at_price is not None
        assert domain_sku.compare_at_price.amount == 20000
        assert domain_sku.compare_at_price.currency == "RUB"

    def test_compare_at_price_none_when_absent(self) -> None:
        """compare_at_price is None when ORM column is null."""
        orm_sku = _make_orm_sku(compare_at_price=None)
        repo = ProductRepository(session=AsyncMock())

        domain_sku = repo._sku_to_domain(orm_sku)

        assert domain_sku.compare_at_price is None

    def test_maps_variant_attributes(self) -> None:
        """variant_attributes are extracted from SKUAttributeValueLink rows."""
        attr_id1 = uuid.uuid4()
        val_id1 = uuid.uuid4()
        attr_id2 = uuid.uuid4()
        val_id2 = uuid.uuid4()

        orm_sku = _make_orm_sku(variant_attributes=[(attr_id1, val_id1), (attr_id2, val_id2)])
        repo = ProductRepository(session=AsyncMock())

        domain_sku = repo._sku_to_domain(orm_sku)

        assert len(domain_sku.variant_attributes) == 2
        assert (attr_id1, val_id1) in domain_sku.variant_attributes
        assert (attr_id2, val_id2) in domain_sku.variant_attributes

    def test_maps_all_scalar_fields(self) -> None:
        """All scalar fields transfer correctly from ORM to domain."""
        sku_id = uuid.uuid4()
        product_id = uuid.uuid4()
        orm_sku = _make_orm_sku(sku_id=sku_id, product_id=product_id)
        repo = ProductRepository(session=AsyncMock())

        domain_sku = repo._sku_to_domain(orm_sku)

        assert domain_sku.id == sku_id
        assert domain_sku.product_id == product_id
        assert domain_sku.sku_code == orm_sku.sku_code
        assert domain_sku.variant_hash == orm_sku.variant_hash
        assert domain_sku.is_active == orm_sku.is_active
        assert domain_sku.version == orm_sku.version
        assert domain_sku.deleted_at == orm_sku.deleted_at
        assert domain_sku.created_at == orm_sku.created_at
        assert domain_sku.updated_at == orm_sku.updated_at

    def test_returns_domain_sku_type(self) -> None:
        """Return type is a domain SKU, not the ORM model."""
        orm_sku = _make_orm_sku()
        repo = ProductRepository(session=AsyncMock())
        domain_sku = repo._sku_to_domain(orm_sku)
        assert isinstance(domain_sku, DomainSKU)


# ---------------------------------------------------------------------------
# SKU mapper tests: _sku_to_orm
# ---------------------------------------------------------------------------


class TestSkuToOrm:
    """Tests for _sku_to_orm: domain SKU -> ORM SKU."""

    def test_decomposes_money_price(self) -> None:
        """Money VO is decomposed into price + currency columns."""
        domain_sku = _make_domain_sku(price=Money(amount=25000, currency="EUR"))
        repo = ProductRepository(session=AsyncMock())

        orm_sku = repo._sku_to_orm(domain_sku)

        assert orm_sku.price == 25000
        assert orm_sku.currency == "EUR"

    def test_decomposes_compare_at_price(self) -> None:
        """compare_at_price Money VO is decomposed to ORM column."""
        domain_sku = _make_domain_sku(
            price=Money(amount=10000, currency="RUB"),
            compare_at_price=Money(amount=20000, currency="RUB"),
        )
        repo = ProductRepository(session=AsyncMock())

        orm_sku = repo._sku_to_orm(domain_sku)

        assert orm_sku.compare_at_price == 20000

    def test_compare_at_price_none_maps_to_null(self) -> None:
        """When compare_at_price is None, ORM column is set to None."""
        domain_sku = _make_domain_sku(compare_at_price=None)
        repo = ProductRepository(session=AsyncMock())

        orm_sku = repo._sku_to_orm(domain_sku)

        assert orm_sku.compare_at_price is None

    def test_creates_new_orm_sku_with_defaults(self) -> None:
        """New ORM SKU gets ORM-only defaults (main_image_url, attributes_cache)."""
        domain_sku = _make_domain_sku()
        repo = ProductRepository(session=AsyncMock())

        orm_sku = repo._sku_to_orm(domain_sku)

        assert orm_sku.main_image_url is None
        assert orm_sku.attributes_cache == {}

    def test_updates_existing_orm_sku_preserves_orm_fields(self) -> None:
        """Updating an existing ORM SKU preserves ORM-only fields."""
        existing_orm = _make_orm_sku()
        existing_orm.main_image_url = "https://cdn.example.com/image.jpg"
        existing_orm.attributes_cache = {"color": "red"}

        domain_sku = _make_domain_sku(
            sku_id=existing_orm.id,
            product_id=existing_orm.product_id,
        )
        repo = ProductRepository(session=AsyncMock())

        repo._sku_to_orm(domain_sku, existing_orm)

        assert existing_orm.main_image_url == "https://cdn.example.com/image.jpg"
        assert existing_orm.attributes_cache == {"color": "red"}

    def test_syncs_variant_attribute_links(self) -> None:
        """variant_attributes are synced to SKUAttributeValueLink rows."""
        attr_id = uuid.uuid4()
        val_id = uuid.uuid4()
        domain_sku = _make_domain_sku(variant_attributes=[(attr_id, val_id)])
        repo = ProductRepository(session=AsyncMock())

        orm_sku = repo._sku_to_orm(domain_sku)

        assert len(orm_sku.attribute_values) == 1
        link = orm_sku.attribute_values[0]
        assert link.attribute_id == attr_id
        assert link.attribute_value_id == val_id

    def test_returns_orm_sku_type(self) -> None:
        """Return type is an ORM SKU model."""
        domain_sku = _make_domain_sku()
        repo = ProductRepository(session=AsyncMock())
        orm_sku = repo._sku_to_orm(domain_sku)
        assert isinstance(orm_sku, OrmSKU)


# ---------------------------------------------------------------------------
# Product mapper tests: _to_domain
# ---------------------------------------------------------------------------


class TestToDomain:
    """Tests for _to_domain: ORM Product + SKUs -> domain Product."""

    def test_maps_all_product_fields(self) -> None:
        """All product fields are correctly transferred from ORM to domain."""
        product_id = uuid.uuid4()
        orm = _make_orm_product(product_id=product_id, slug="my-slug")
        repo = ProductRepository(session=AsyncMock())

        domain = repo._to_domain(orm)

        assert domain.id == product_id
        assert domain.slug == "my-slug"
        assert domain.title_i18n == {"en": "Test Product"}
        assert domain.description_i18n == {"en": "A test product description"}
        assert domain.status == DomainProductStatus.DRAFT
        assert domain.brand_id == orm.brand_id
        assert domain.primary_category_id == orm.primary_category_id
        assert domain.supplier_id == orm.supplier_id
        assert domain.country_of_origin == "US"
        assert domain.tags == ["tag1", "tag2"]
        assert domain.version == 1
        assert domain.created_at == _NOW
        assert domain.updated_at == _NOW

    def test_maps_skus(self) -> None:
        """SKUs are mapped from ORM to domain entities."""
        product_id = uuid.uuid4()
        sku1 = _make_orm_sku(product_id=product_id)
        sku2 = _make_orm_sku(product_id=product_id)
        orm = _make_orm_product(product_id=product_id, skus=[sku1, sku2])
        repo = ProductRepository(session=AsyncMock())

        domain = repo._to_domain(orm)

        assert len(domain.skus) == 2
        assert all(isinstance(s, DomainSKU) for s in domain.skus)

    def test_maps_status_via_value_string(self) -> None:
        """ORM ProductStatus enum is converted to domain ProductStatus via string value."""
        orm = _make_orm_product(status=OrmProductStatus.PUBLISHED)
        repo = ProductRepository(session=AsyncMock())

        domain = repo._to_domain(orm)

        assert domain.status == DomainProductStatus.PUBLISHED

    def test_returns_domain_product_type(self) -> None:
        """Return type is a domain Product, not the ORM model."""
        orm = _make_orm_product()
        repo = ProductRepository(session=AsyncMock())
        domain = repo._to_domain(orm)
        assert isinstance(domain, DomainProduct)
        assert not isinstance(domain, OrmProduct)

    def test_handles_empty_title_i18n(self) -> None:
        """When title_i18n is falsy, it maps to an empty dict."""
        orm = _make_orm_product()
        orm.title_i18n = None  # type: ignore[assignment]
        repo = ProductRepository(session=AsyncMock())

        domain = repo._to_domain(orm)

        assert domain.title_i18n == {}

    def test_handles_empty_tags(self) -> None:
        """When tags is falsy, it maps to an empty list."""
        orm = _make_orm_product()
        orm.tags = None  # type: ignore[assignment]
        repo = ProductRepository(session=AsyncMock())

        domain = repo._to_domain(orm)

        assert domain.tags == []


# ---------------------------------------------------------------------------
# Product mapper tests: _to_domain_without_skus
# ---------------------------------------------------------------------------


class TestToDomainWithoutSkus:
    """Tests for _to_domain_without_skus: ORM Product -> domain Product (empty SKU list)."""

    def test_returns_empty_skus_list(self) -> None:
        """SKUs list is always empty regardless of ORM skus."""
        sku = _make_orm_sku()
        orm = _make_orm_product(skus=[sku])
        repo = ProductRepository(session=AsyncMock())

        domain = repo._to_domain_without_skus(orm)

        assert domain.skus == []

    def test_maps_all_product_fields(self) -> None:
        """All non-SKU fields map correctly."""
        product_id = uuid.uuid4()
        orm = _make_orm_product(product_id=product_id)
        repo = ProductRepository(session=AsyncMock())

        domain = repo._to_domain_without_skus(orm)

        assert domain.id == product_id
        assert domain.slug == orm.slug
        assert domain.status == DomainProductStatus(orm.status.value)


# ---------------------------------------------------------------------------
# Product mapper tests: _to_orm
# ---------------------------------------------------------------------------


class TestToOrm:
    """Tests for _to_orm: domain Product -> ORM Product."""

    def test_maps_all_fields(self) -> None:
        """All domain fields transfer to ORM model."""
        domain = _make_domain_product(slug="my-product")
        repo = ProductRepository(session=AsyncMock())

        orm = repo._to_orm(domain)

        assert orm.id == domain.id
        assert orm.slug == "my-product"
        assert orm.brand_id == domain.brand_id
        assert orm.primary_category_id == domain.primary_category_id
        assert orm.supplier_id == domain.supplier_id
        assert orm.version == domain.version
        assert orm.country_of_origin == domain.country_of_origin

    def test_maps_status_to_orm_enum(self) -> None:
        """Domain ProductStatus is converted to ORM ProductStatus via value."""
        domain = _make_domain_product(status=DomainProductStatus.ENRICHING)
        repo = ProductRepository(session=AsyncMock())

        orm = repo._to_orm(domain)

        assert orm.status == OrmProductStatus.ENRICHING

    def test_creates_new_orm_with_defaults(self) -> None:
        """New ORM product gets ORM-only defaults."""
        domain = _make_domain_product()
        repo = ProductRepository(session=AsyncMock())

        orm = repo._to_orm(domain)

        assert orm.popularity_score == 0
        assert orm.is_visible is True
        assert orm.source_url is None
        assert orm.attributes == {}

    def test_updates_existing_preserves_orm_fields(self) -> None:
        """Updating an existing ORM Product preserves ORM-only fields."""
        existing_orm = _make_orm_product()
        existing_orm.popularity_score = 42
        existing_orm.is_visible = False
        existing_orm.source_url = "https://example.com"
        existing_orm.attributes = {"key": "value"}

        domain = _make_domain_product(product_id=existing_orm.id)
        repo = ProductRepository(session=AsyncMock())

        repo._to_orm(domain, existing_orm)

        assert existing_orm.popularity_score == 42
        assert existing_orm.is_visible is False
        assert existing_orm.source_url == "https://example.com"
        assert existing_orm.attributes == {"key": "value"}

    def test_returns_orm_product_type(self) -> None:
        """Return type is an ORM Product model."""
        domain = _make_domain_product()
        repo = ProductRepository(session=AsyncMock())
        orm = repo._to_orm(domain)
        assert isinstance(orm, OrmProduct)


# ---------------------------------------------------------------------------
# _sync_skus
# ---------------------------------------------------------------------------


class TestSyncSkus:
    """Tests for _sync_skus: reconcile domain SKU list with ORM collection."""

    def test_adds_new_skus(self) -> None:
        """New domain SKUs not in ORM collection are appended."""
        product_id = uuid.uuid4()
        orm = _make_orm_product(product_id=product_id, skus=[])
        new_sku = _make_domain_sku(product_id=product_id)
        domain = _make_domain_product(product_id=product_id, skus=[new_sku])

        repo = ProductRepository(session=AsyncMock())
        repo._sync_skus(domain, orm)

        assert len(orm.skus) == 1
        assert orm.skus[0].id == new_sku.id

    def test_updates_existing_skus(self) -> None:
        """Existing SKUs are updated in place."""
        sku_id = uuid.uuid4()
        product_id = uuid.uuid4()
        existing_orm_sku = _make_orm_sku(sku_id=sku_id, product_id=product_id, price=10000)
        orm = _make_orm_product(product_id=product_id, skus=[existing_orm_sku])

        updated_domain_sku = _make_domain_sku(
            sku_id=sku_id,
            product_id=product_id,
            price=Money(amount=20000, currency="RUB"),
        )
        domain = _make_domain_product(product_id=product_id, skus=[updated_domain_sku])

        repo = ProductRepository(session=AsyncMock())
        repo._sync_skus(domain, orm)

        assert len(orm.skus) == 1
        assert orm.skus[0].price == 20000

    def test_removes_deleted_skus(self) -> None:
        """ORM SKUs not in domain list are removed."""
        product_id = uuid.uuid4()
        orphan_sku = _make_orm_sku(product_id=product_id)
        orm = _make_orm_product(product_id=product_id, skus=[orphan_sku])

        domain = _make_domain_product(product_id=product_id, skus=[])

        repo = ProductRepository(session=AsyncMock())
        repo._sync_skus(domain, orm)

        assert len(orm.skus) == 0


# ---------------------------------------------------------------------------
# Public method tests: add()
# ---------------------------------------------------------------------------


class TestAdd:
    """Tests for ProductRepository.add()."""

    async def test_add_calls_session_add_and_flush(self) -> None:
        """add() calls session.add() with ORM model and flushes."""
        session = AsyncMock()
        repo = ProductRepository(session=session)
        domain = _make_domain_product()

        await repo.add(domain)

        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    async def test_add_passes_orm_model_to_session(self) -> None:
        """The object passed to session.add() is an ORM model."""
        session = AsyncMock()
        repo = ProductRepository(session=session)
        domain = _make_domain_product()

        await repo.add(domain)

        added_obj = session.add.call_args[0][0]
        assert isinstance(added_obj, OrmProduct)

    async def test_add_returns_domain_product(self) -> None:
        """add() returns a domain Product after persistence."""
        session = AsyncMock()
        repo = ProductRepository(session=session)
        domain = _make_domain_product()

        result = await repo.add(domain)

        assert isinstance(result, DomainProduct)
        assert result.id == domain.id

    async def test_add_includes_skus_in_orm(self) -> None:
        """add() maps domain SKUs to ORM and appends to the product."""
        product_id = uuid.uuid4()
        sku = _make_domain_sku(product_id=product_id)
        domain = _make_domain_product(product_id=product_id, skus=[sku])

        session = AsyncMock()
        repo = ProductRepository(session=session)

        result = await repo.add(domain)

        added_obj = session.add.call_args[0][0]
        assert len(added_obj.skus) == 1

    async def test_add_raises_concurrency_error_on_stale_data(self) -> None:
        """StaleDataError during flush is translated to ConcurrencyError."""
        session = AsyncMock()
        session.flush.side_effect = StaleDataError()
        repo = ProductRepository(session=session)
        domain = _make_domain_product()

        with pytest.raises(ConcurrencyError) as exc_info:
            await repo.add(domain)

        assert "Product" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Public method tests: get()
# ---------------------------------------------------------------------------


class TestGet:
    """Tests for ProductRepository.get()."""

    async def test_get_found_returns_domain_product(self) -> None:
        """get() returns a domain product when the ORM row exists."""
        product_id = uuid.uuid4()
        orm = _make_orm_product(product_id=product_id)

        session = AsyncMock()
        session.get.return_value = orm
        repo = ProductRepository(session=session)

        result = await repo.get(product_id)

        assert result is not None
        assert isinstance(result, DomainProduct)
        assert result.id == product_id

    async def test_get_not_found_returns_none(self) -> None:
        """get() returns None when the ORM row does not exist."""
        session = AsyncMock()
        session.get.return_value = None
        repo = ProductRepository(session=session)

        result = await repo.get(uuid.uuid4())

        assert result is None

    async def test_get_soft_deleted_returns_none(self) -> None:
        """get() returns None for soft-deleted products."""
        orm = _make_orm_product(deleted_at=_NOW)

        session = AsyncMock()
        session.get.return_value = orm
        repo = ProductRepository(session=session)

        result = await repo.get(orm.id)

        assert result is None

    async def test_get_returns_product_without_skus(self) -> None:
        """get() returns product with empty SKUs list (no eager load)."""
        sku = _make_orm_sku()
        orm = _make_orm_product(skus=[sku])

        session = AsyncMock()
        session.get.return_value = orm
        repo = ProductRepository(session=session)

        result = await repo.get(orm.id)

        assert result is not None
        assert result.skus == []


# ---------------------------------------------------------------------------
# Public method tests: update()
# ---------------------------------------------------------------------------


class TestUpdate:
    """Tests for ProductRepository.update()."""

    async def test_update_raises_value_error_when_not_found(self) -> None:
        """update() raises ValueError when product not in DB."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None

        session = AsyncMock()
        session.execute.return_value = result_mock
        repo = ProductRepository(session=session)
        domain = _make_domain_product()

        with pytest.raises(ValueError, match="not found in DB"):
            await repo.update(domain)

    async def test_update_flushes_session(self) -> None:
        """update() calls session.flush()."""
        product_id = uuid.uuid4()
        orm = _make_orm_product(product_id=product_id, skus=[])

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = orm

        session = AsyncMock()
        session.execute.return_value = result_mock
        repo = ProductRepository(session=session)
        domain = _make_domain_product(product_id=product_id)

        await repo.update(domain)

        session.flush.assert_awaited_once()

    async def test_update_raises_concurrency_error_on_stale_data(self) -> None:
        """StaleDataError during flush is translated to ConcurrencyError."""
        product_id = uuid.uuid4()
        orm = _make_orm_product(product_id=product_id, skus=[])

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = orm

        session = AsyncMock()
        session.execute.return_value = result_mock
        session.flush.side_effect = StaleDataError()
        repo = ProductRepository(session=session)
        domain = _make_domain_product(product_id=product_id)

        with pytest.raises(ConcurrencyError):
            await repo.update(domain)


# ---------------------------------------------------------------------------
# Public method tests: delete()
# ---------------------------------------------------------------------------


class TestDelete:
    """Tests for ProductRepository.delete()."""

    async def test_delete_executes_statement(self) -> None:
        """delete() calls session.execute() with a DELETE statement."""
        session = AsyncMock()
        repo = ProductRepository(session=session)
        product_id = uuid.uuid4()

        await repo.delete(product_id)

        session.execute.assert_awaited_once()

    async def test_delete_returns_none(self) -> None:
        """delete() returns None (void operation)."""
        session = AsyncMock()
        repo = ProductRepository(session=session)

        result = await repo.delete(uuid.uuid4())

        assert result is None


# ---------------------------------------------------------------------------
# Public method tests: get_by_slug()
# ---------------------------------------------------------------------------


class TestGetBySlug:
    """Tests for ProductRepository.get_by_slug()."""

    async def test_found_returns_domain_product(self) -> None:
        """get_by_slug() returns a domain product when found."""
        orm = _make_orm_product(slug="found-slug")

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = orm

        session = AsyncMock()
        session.execute.return_value = result_mock
        repo = ProductRepository(session=session)

        result = await repo.get_by_slug("found-slug")

        assert result is not None
        assert result.slug == "found-slug"
        assert result.skus == []  # uses _to_domain_without_skus

    async def test_not_found_returns_none(self) -> None:
        """get_by_slug() returns None when no product matches."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None

        session = AsyncMock()
        session.execute.return_value = result_mock
        repo = ProductRepository(session=session)

        result = await repo.get_by_slug("nonexistent")

        assert result is None


# ---------------------------------------------------------------------------
# Public method tests: check_slug_exists() / check_slug_exists_excluding()
# ---------------------------------------------------------------------------


class TestCheckSlugExists:
    """Tests for slug existence checks."""

    async def test_check_slug_exists_returns_true(self) -> None:
        """check_slug_exists() returns True when a row is found."""
        result_mock = MagicMock()
        result_mock.first.return_value = (uuid.uuid4(),)

        session = AsyncMock()
        session.execute.return_value = result_mock
        repo = ProductRepository(session=session)

        assert await repo.check_slug_exists("taken-slug") is True

    async def test_check_slug_exists_returns_false(self) -> None:
        """check_slug_exists() returns False when no row is found."""
        result_mock = MagicMock()
        result_mock.first.return_value = None

        session = AsyncMock()
        session.execute.return_value = result_mock
        repo = ProductRepository(session=session)

        assert await repo.check_slug_exists("free-slug") is False

    async def test_check_slug_exists_excluding_returns_true(self) -> None:
        """check_slug_exists_excluding() returns True when taken by another."""
        result_mock = MagicMock()
        result_mock.first.return_value = (uuid.uuid4(),)

        session = AsyncMock()
        session.execute.return_value = result_mock
        repo = ProductRepository(session=session)

        assert await repo.check_slug_exists_excluding("taken", uuid.uuid4()) is True

    async def test_check_slug_exists_excluding_returns_false(self) -> None:
        """check_slug_exists_excluding() returns False when slug is free."""
        result_mock = MagicMock()
        result_mock.first.return_value = None

        session = AsyncMock()
        session.execute.return_value = result_mock
        repo = ProductRepository(session=session)

        assert await repo.check_slug_exists_excluding("free", uuid.uuid4()) is False


# ---------------------------------------------------------------------------
# Public method tests: get_for_update()
# ---------------------------------------------------------------------------


class TestGetForUpdate:
    """Tests for ProductRepository.get_for_update()."""

    async def test_found_returns_domain_product(self) -> None:
        """get_for_update() returns a domain product when found."""
        orm = _make_orm_product()

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = orm

        session = AsyncMock()
        session.execute.return_value = result_mock
        repo = ProductRepository(session=session)

        result = await repo.get_for_update(orm.id)

        assert result is not None
        assert result.skus == []  # uses _to_domain_without_skus

    async def test_not_found_returns_none(self) -> None:
        """get_for_update() returns None when product not found."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None

        session = AsyncMock()
        session.execute.return_value = result_mock
        repo = ProductRepository(session=session)

        result = await repo.get_for_update(uuid.uuid4())

        assert result is None


# ---------------------------------------------------------------------------
# Public method tests: get_with_skus()
# ---------------------------------------------------------------------------


class TestGetWithSkus:
    """Tests for ProductRepository.get_with_skus()."""

    async def test_found_returns_product_with_skus(self) -> None:
        """get_with_skus() returns product with eagerly loaded SKUs."""
        product_id = uuid.uuid4()
        sku = _make_orm_sku(product_id=product_id)
        orm = _make_orm_product(product_id=product_id, skus=[sku])

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = orm

        session = AsyncMock()
        session.execute.return_value = result_mock
        repo = ProductRepository(session=session)

        result = await repo.get_with_skus(product_id)

        assert result is not None
        assert len(result.skus) == 1

    async def test_not_found_returns_none(self) -> None:
        """get_with_skus() returns None when product not found."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None

        session = AsyncMock()
        session.execute.return_value = result_mock
        repo = ProductRepository(session=session)

        result = await repo.get_with_skus(uuid.uuid4())

        assert result is None

    async def test_soft_deleted_returns_none(self) -> None:
        """get_with_skus() returns None for soft-deleted products."""
        orm = _make_orm_product(deleted_at=_NOW)

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = orm

        session = AsyncMock()
        session.execute.return_value = result_mock
        repo = ProductRepository(session=session)

        result = await repo.get_with_skus(orm.id)

        assert result is None


# ---------------------------------------------------------------------------
# Public method tests: list_products()
# ---------------------------------------------------------------------------


class TestListProducts:
    """Tests for ProductRepository.list_products()."""

    async def test_returns_tuple_of_products_and_count(self) -> None:
        """list_products() returns (list[DomainProduct], total_count)."""
        orm1 = _make_orm_product()
        orm2 = _make_orm_product()

        # Count query result
        count_result = MagicMock()
        count_result.scalar_one.return_value = 2

        # Data query result
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [orm1, orm2]
        data_result = MagicMock()
        data_result.scalars.return_value = scalars_mock

        session = AsyncMock()
        session.execute.side_effect = [count_result, data_result]
        repo = ProductRepository(session=session)

        products, total = await repo.list_products(limit=10, offset=0)

        assert total == 2
        assert len(products) == 2
        assert all(isinstance(p, DomainProduct) for p in products)

    async def test_returns_products_without_skus(self) -> None:
        """list_products() uses _to_domain_without_skus (empty SKU list)."""
        sku = _make_orm_sku()
        orm = _make_orm_product(skus=[sku])

        count_result = MagicMock()
        count_result.scalar_one.return_value = 1

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [orm]
        data_result = MagicMock()
        data_result.scalars.return_value = scalars_mock

        session = AsyncMock()
        session.execute.side_effect = [count_result, data_result]
        repo = ProductRepository(session=session)

        products, _ = await repo.list_products(limit=10, offset=0)

        assert products[0].skus == []

    async def test_returns_empty_when_no_products(self) -> None:
        """list_products() returns ([], 0) when no products match."""
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        data_result = MagicMock()
        data_result.scalars.return_value = scalars_mock

        session = AsyncMock()
        session.execute.side_effect = [count_result, data_result]
        repo = ProductRepository(session=session)

        products, total = await repo.list_products(limit=10, offset=0)

        assert products == []
        assert total == 0

    async def test_executes_two_queries(self) -> None:
        """list_products() executes two queries: count + data."""
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        data_result = MagicMock()
        data_result.scalars.return_value = scalars_mock

        session = AsyncMock()
        session.execute.side_effect = [count_result, data_result]
        repo = ProductRepository(session=session)

        await repo.list_products(limit=10, offset=0)

        assert session.execute.await_count == 2


# ---------------------------------------------------------------------------
# Roundtrip mapping
# ---------------------------------------------------------------------------


class TestRoundtripMapping:
    """Roundtrip: domain -> ORM -> domain preserves data."""

    def test_product_roundtrip(self) -> None:
        """Product domain -> ORM -> domain roundtrip preserves all fields."""
        domain = _make_domain_product(slug="roundtrip-product")
        repo = ProductRepository(session=AsyncMock())

        orm = repo._to_orm(domain)
        # Simulate ORM state for _to_domain
        orm.skus = []
        restored = repo._to_domain(orm)

        assert restored.id == domain.id
        assert restored.slug == domain.slug
        assert restored.title_i18n == domain.title_i18n
        assert restored.description_i18n == domain.description_i18n
        assert restored.status == domain.status
        assert restored.brand_id == domain.brand_id
        assert restored.primary_category_id == domain.primary_category_id
        assert restored.supplier_id == domain.supplier_id
        assert restored.country_of_origin == domain.country_of_origin
        assert restored.tags == domain.tags
        assert restored.version == domain.version

    def test_sku_roundtrip_with_money(self) -> None:
        """SKU domain -> ORM -> domain roundtrip preserves Money VOs."""
        domain_sku = _make_domain_sku(
            price=Money(amount=15000, currency="USD"),
            compare_at_price=Money(amount=25000, currency="USD"),
        )
        repo = ProductRepository(session=AsyncMock())

        orm_sku = repo._sku_to_orm(domain_sku)
        restored = repo._sku_to_domain(orm_sku)

        assert restored.price == domain_sku.price
        assert restored.compare_at_price == domain_sku.compare_at_price
        assert restored.id == domain_sku.id

    def test_sku_roundtrip_with_variant_attributes(self) -> None:
        """SKU roundtrip preserves variant_attributes list."""
        attr_id = uuid.uuid4()
        val_id = uuid.uuid4()
        domain_sku = _make_domain_sku(variant_attributes=[(attr_id, val_id)])
        repo = ProductRepository(session=AsyncMock())

        orm_sku = repo._sku_to_orm(domain_sku)
        restored = repo._sku_to_domain(orm_sku)

        assert restored.variant_attributes == [(attr_id, val_id)]
