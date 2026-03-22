"""
Product repository -- Data Mapper implementation.

Translates between :class:`~src.modules.catalog.domain.entities.Product`
(domain aggregate with SKU child entities) and the ``products`` / ``skus``
ORM tables.  Handles Money value-object decomposition, eager SKU loading,
paginated listing with filters, and optimistic-locking conflict detection.
"""

import uuid

from sqlalchemy import ColumnElement, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
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


class ProductRepository(IProductRepository):
    """Data Mapper repository for the Product aggregate.

    Converts between the database layer (``OrmProduct`` / ``OrmSKU``) and the
    domain layer (``DomainProduct`` / ``DomainSKU``), keeping ORM concerns out
    of business logic.  Money value objects are decomposed to/from flat integer
    columns on the SKU table.

    Args:
        session: SQLAlchemy async session scoped to the current request.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Private mapping helpers
    # ------------------------------------------------------------------

    def _sku_to_domain(self, orm_sku: OrmSKU) -> DomainSKU:
        """Map an ORM SKU row to a domain SKU entity with Money VOs."""
        compare_at_price: Money | None = None
        if orm_sku.compare_at_price is not None:
            compare_at_price = Money(
                amount=orm_sku.compare_at_price,
                currency=orm_sku.currency,
            )

        return DomainSKU(
            id=orm_sku.id,
            product_id=orm_sku.product_id,
            sku_code=orm_sku.sku_code,
            variant_hash=orm_sku.variant_hash,
            price=Money(amount=orm_sku.price, currency=orm_sku.currency),
            compare_at_price=compare_at_price,
            is_active=orm_sku.is_active,
            version=orm_sku.version,
            deleted_at=orm_sku.deleted_at,
            created_at=orm_sku.created_at,
            updated_at=orm_sku.updated_at,
            variant_attributes=[
                (link.attribute_id, link.attribute_value_id) for link in orm_sku.attribute_values
            ],
        )

    def _sku_to_orm(self, domain_sku: DomainSKU, orm_sku: OrmSKU | None = None) -> OrmSKU:
        """Map a domain SKU entity to an ORM SKU row.

        When ``orm_sku`` is ``None`` a new row is created with safe defaults
        for ORM-only fields (``main_image_url``, ``attributes_cache``).
        When updating an existing row those fields are preserved.
        """
        is_create = orm_sku is None
        if orm_sku is None:
            orm_sku = OrmSKU()

        orm_sku.id = domain_sku.id
        orm_sku.product_id = domain_sku.product_id
        orm_sku.sku_code = domain_sku.sku_code
        orm_sku.variant_hash = domain_sku.variant_hash
        orm_sku.is_active = domain_sku.is_active
        orm_sku.version = domain_sku.version
        orm_sku.deleted_at = domain_sku.deleted_at
        orm_sku.created_at = domain_sku.created_at
        orm_sku.updated_at = domain_sku.updated_at

        # Money VO decomposition
        orm_sku.price = domain_sku.price.amount
        orm_sku.currency = domain_sku.price.currency
        orm_sku.compare_at_price = (
            domain_sku.compare_at_price.amount if domain_sku.compare_at_price is not None else None
        )

        # ORM-only fields: set defaults on create, preserve on update
        if is_create:
            orm_sku.main_image_url = None
            orm_sku.attributes_cache = {}  # type: ignore[assignment]

        # Sync variant_attributes -> SKUAttributeValueLink rows
        orm_sku.attribute_values.clear()
        for attr_id, attr_val_id in domain_sku.variant_attributes:
            orm_sku.attribute_values.append(
                OrmSKUAttrLink(
                    sku_id=domain_sku.id,
                    attribute_id=attr_id,
                    attribute_value_id=attr_val_id,
                )
            )

        return orm_sku

    def _to_domain(self, orm: OrmProduct) -> DomainProduct:
        """Map an ORM Product row to a domain Product entity WITH SKUs.

        Callers must ensure ``orm.skus`` is loaded (via ``selectinload``
        or prior access within the session) before calling this method.
        """
        return DomainProduct(
            id=orm.id,
            slug=orm.slug,
            title_i18n=dict(orm.title_i18n) if orm.title_i18n else {},
            description_i18n=dict(orm.description_i18n) if orm.description_i18n else {},
            status=DomainProductStatus(orm.status.value),
            brand_id=orm.brand_id,
            primary_category_id=orm.primary_category_id,
            supplier_id=orm.supplier_id,
            country_of_origin=orm.country_of_origin,
            tags=list(orm.tags) if orm.tags else [],
            version=orm.version,
            deleted_at=orm.deleted_at,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            published_at=orm.published_at,
            skus=[self._sku_to_domain(sku) for sku in orm.skus],
        )

    def _to_domain_without_skus(self, orm: OrmProduct) -> DomainProduct:
        """Map an ORM Product row to a domain Product entity WITHOUT SKUs.

        Used by methods that do not eager-load SKUs (``get``, ``get_by_slug``,
        ``get_for_update``, ``list_products``) to avoid lazy-load errors in
        async sessions.
        """
        return DomainProduct(
            id=orm.id,
            slug=orm.slug,
            title_i18n=dict(orm.title_i18n) if orm.title_i18n else {},
            description_i18n=dict(orm.description_i18n) if orm.description_i18n else {},
            status=DomainProductStatus(orm.status.value),
            brand_id=orm.brand_id,
            primary_category_id=orm.primary_category_id,
            supplier_id=orm.supplier_id,
            country_of_origin=orm.country_of_origin,
            tags=list(orm.tags) if orm.tags else [],
            version=orm.version,
            deleted_at=orm.deleted_at,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            published_at=orm.published_at,
            skus=[],
        )

    def _to_orm(self, entity: DomainProduct, orm: OrmProduct | None = None) -> OrmProduct:
        """Map a domain Product entity to an ORM Product row.

        When ``orm`` is ``None`` a new row is created with safe defaults
        for ORM-only fields. When updating, those fields are preserved.
        """
        is_create = orm is None
        if orm is None:
            orm = OrmProduct()

        orm.id = entity.id
        orm.slug = entity.slug
        orm.brand_id = entity.brand_id
        orm.primary_category_id = entity.primary_category_id
        orm.supplier_id = entity.supplier_id  # type: ignore[assignment]
        orm.version = entity.version
        orm.deleted_at = entity.deleted_at
        orm.created_at = entity.created_at
        orm.updated_at = entity.updated_at
        orm.published_at = entity.published_at
        orm.country_of_origin = entity.country_of_origin

        orm.status = OrmProductStatus(entity.status.value)
        orm.title_i18n = entity.title_i18n  # type: ignore[assignment]
        orm.description_i18n = entity.description_i18n  # type: ignore[assignment]
        orm.tags = entity.tags  # type: ignore[assignment]

        # ORM-only fields: set defaults on create, preserve on update
        if is_create:
            orm.popularity_score = 0
            orm.is_visible = True
            orm.source_url = None
            orm.attributes = {}  # type: ignore[assignment]

        return orm

    def _sync_skus(self, product: DomainProduct, orm: OrmProduct) -> None:
        """Reconcile domain SKU list with the ORM SKU collection.

        Handles additions, updates, and removals of child SKU entities.
        """
        existing_by_id: dict[uuid.UUID, OrmSKU] = {sku.id: sku for sku in orm.skus}
        domain_sku_ids: set[uuid.UUID] = set()

        for domain_sku in product.skus:
            domain_sku_ids.add(domain_sku.id)
            existing_orm_sku = existing_by_id.get(domain_sku.id)
            if existing_orm_sku is not None:
                self._sku_to_orm(domain_sku, existing_orm_sku)
            else:
                new_orm_sku = self._sku_to_orm(domain_sku)
                orm.skus.append(new_orm_sku)

        # Remove ORM SKUs that are no longer in the domain list
        to_remove = [sku for sku in orm.skus if sku.id not in domain_sku_ids]
        for sku in to_remove:
            orm.skus.remove(sku)

    # ------------------------------------------------------------------
    # Public methods -- IProductRepository + ICatalogRepository
    # ------------------------------------------------------------------

    async def add(self, entity: DomainProduct) -> DomainProduct:
        """Persist a new product and return the refreshed domain entity.

        Raises:
            ConcurrencyError: If an optimistic locking conflict is detected.
        """
        orm = self._to_orm(entity)

        for domain_sku in entity.skus:
            orm_sku = self._sku_to_orm(domain_sku)
            orm.skus.append(orm_sku)

        self._session.add(orm)

        try:
            await self._session.flush()
        except StaleDataError:
            raise ConcurrencyError(
                entity_type="Product",
                entity_id=entity.id,
                expected_version=entity.version,
                actual_version=-1,
            ) from None

        return self._to_domain(orm)

    async def get(self, entity_id: uuid.UUID) -> DomainProduct | None:
        """Retrieve a product by primary key, or ``None`` if not found.

        Soft-deleted products are excluded. SKUs are NOT loaded.
        """
        orm = await self._session.get(OrmProduct, entity_id)
        if orm is None or orm.deleted_at is not None:
            return None
        return self._to_domain_without_skus(orm)

    async def update(self, entity: DomainProduct) -> DomainProduct:
        """Merge updated domain state into the existing ORM row.

        Eagerly loads SKUs and their attribute-value links to enable
        proper reconciliation via ``_sync_skus``.

        Raises:
            ValueError: If the product row does not exist.
            ConcurrencyError: If an optimistic locking conflict is detected.
        """
        stmt = (
            select(OrmProduct)
            .where(OrmProduct.id == entity.id)
            .options(selectinload(OrmProduct.skus).selectinload(OrmSKU.attribute_values))
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None:
            raise ValueError(f"Product with id {entity.id} not found in DB")

        self._to_orm(entity, orm)
        self._sync_skus(entity, orm)

        try:
            await self._session.flush()
        except StaleDataError:
            raise ConcurrencyError(
                entity_type="Product",
                entity_id=entity.id,
                expected_version=entity.version,
                actual_version=-1,
            ) from None

        return self._to_domain(orm)

    async def delete(self, entity_id: uuid.UUID) -> None:
        """Hard-delete a product row by primary key."""
        stmt = delete(OrmProduct).where(OrmProduct.id == entity_id)
        await self._session.execute(stmt)

    async def get_by_slug(self, slug: str) -> DomainProduct | None:
        """Retrieve a product by its URL slug, or ``None`` if not found.

        Soft-deleted products are excluded. SKUs are NOT loaded.
        """
        stmt = (
            select(OrmProduct)
            .where(OrmProduct.slug == slug, OrmProduct.deleted_at.is_(None))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is not None:
            return self._to_domain_without_skus(orm)
        return None

    async def check_slug_exists(self, slug: str) -> bool:
        """Return ``True`` if any non-deleted product already uses this slug."""
        stmt = (
            select(OrmProduct.id)
            .where(OrmProduct.slug == slug, OrmProduct.deleted_at.is_(None))
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def check_slug_exists_excluding(self, slug: str, exclude_id: uuid.UUID) -> bool:
        """Return ``True`` if the slug is taken by another non-deleted product."""
        stmt = (
            select(OrmProduct.id)
            .where(
                OrmProduct.slug == slug,
                OrmProduct.id != exclude_id,
                OrmProduct.deleted_at.is_(None),
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def get_for_update(self, product_id: uuid.UUID) -> DomainProduct | None:
        """Retrieve a product with a pessimistic lock (SELECT FOR UPDATE).

        SKUs are NOT loaded.
        """
        stmt = (
            select(OrmProduct)
            .where(OrmProduct.id == product_id, OrmProduct.deleted_at.is_(None))
            .with_for_update()
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is not None:
            return self._to_domain_without_skus(orm)
        return None

    async def get_with_skus(self, product_id: uuid.UUID) -> DomainProduct | None:
        """Retrieve a product with eagerly loaded SKU child entities.

        Soft-deleted products are excluded. SKUs and their attribute-value
        links are loaded via ``selectinload``.
        """
        stmt = (
            select(OrmProduct)
            .where(OrmProduct.id == product_id)
            .options(
                selectinload(OrmProduct.skus.and_(OrmSKU.deleted_at.is_(None))).selectinload(
                    OrmSKU.attribute_values
                )
            )
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None or orm.deleted_at is not None:
            return None

        return self._to_domain(orm)

    async def list_products(
        self,
        limit: int,
        offset: int,
        status: DomainProductStatus | None = None,
        brand_id: uuid.UUID | None = None,
    ) -> tuple[list[DomainProduct], int]:
        """List products with pagination and optional filters.

        Soft-deleted products are excluded. SKUs are NOT loaded.

        Args:
            limit: Maximum number of products to return.
            offset: Number of products to skip.
            status: Optional filter by product lifecycle status.
            brand_id: Optional filter by brand.

        Returns:
            Tuple of (product_list, total_count).
        """
        filters: list[ColumnElement[bool]] = [OrmProduct.deleted_at.is_(None)]

        if status is not None:
            filters.append(OrmProduct.status == OrmProductStatus(status.value))
        if brand_id is not None:
            filters.append(OrmProduct.brand_id == brand_id)

        # Count query
        count_stmt = select(func.count()).select_from(OrmProduct).where(*filters)
        count_result = await self._session.execute(count_stmt)
        total = count_result.scalar_one()

        # Data query
        data_stmt = (
            select(OrmProduct)
            .where(*filters)
            .order_by(OrmProduct.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        data_result = await self._session.execute(data_stmt)
        orm_products = data_result.scalars().all()

        products = [self._to_domain_without_skus(orm) for orm in orm_products]
        return products, total
