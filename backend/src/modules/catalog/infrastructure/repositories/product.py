"""
Product repository -- Data Mapper implementation.

Translates between :class:`~src.modules.catalog.domain.entities.Product`
(domain aggregate with ProductVariant and SKU child entities) and the
``products`` / ``product_variants`` / ``skus`` ORM tables.  Handles Money
value-object decomposition, eager variant/SKU loading, and optimistic-locking
conflict detection.
"""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.exc import StaleDataError

from src.modules.catalog.domain.entities import SKU as DomainSKU
from src.modules.catalog.domain.entities import Product as DomainProduct
from src.modules.catalog.domain.entities import ProductVariant as DomainProductVariant
from src.modules.catalog.domain.exceptions import (
    ConcurrencyError,
    ProductSlugConflictError,
)
from src.modules.catalog.domain.interfaces import IProductRepository
from src.modules.catalog.domain.value_objects import (
    Money,
    ProductStatus,
    PurchaseCurrency,
    SkuPricingStatus,
)
from src.modules.catalog.infrastructure.models import SKU as OrmSKU
from src.modules.catalog.infrastructure.models import Product as OrmProduct
from src.modules.catalog.infrastructure.models import (
    ProductVariant as OrmProductVariant,
)
from src.modules.catalog.infrastructure.models import (
    SKUAttributeValueLink as OrmSKUAttrLink,
)


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
        price: Money | None = None
        if orm_sku.price is not None:
            price = Money(amount=orm_sku.price, currency=orm_sku.currency)

        compare_at_price: Money | None = None
        if orm_sku.compare_at_price is not None:
            compare_at_price = Money(
                amount=orm_sku.compare_at_price,
                currency=orm_sku.currency,
            )

        purchase_price: Money | None = None
        purchase_currency_vo: PurchaseCurrency | None = None
        if orm_sku.purchase_price is not None and orm_sku.purchase_currency:
            purchase_currency_vo = PurchaseCurrency(orm_sku.purchase_currency)
            purchase_price = Money(
                amount=orm_sku.purchase_price,
                currency=purchase_currency_vo.value,
            )

        selling_price: Money | None = None
        if orm_sku.selling_price is not None and orm_sku.selling_currency:
            selling_price = Money(
                amount=orm_sku.selling_price,
                currency=orm_sku.selling_currency,
            )

        return DomainSKU(
            id=orm_sku.id,
            product_id=orm_sku.product_id,
            variant_id=orm_sku.variant_id,
            sku_code=orm_sku.sku_code,
            variant_hash=orm_sku.variant_hash,
            price=price,
            compare_at_price=compare_at_price,
            purchase_price=purchase_price,
            purchase_currency=purchase_currency_vo,
            selling_price=selling_price,
            pricing_status=SkuPricingStatus(orm_sku.pricing_status)
            if isinstance(orm_sku.pricing_status, str)
            else orm_sku.pricing_status,
            priced_at=orm_sku.priced_at,
            priced_with_formula_version_id=orm_sku.priced_with_formula_version_id,
            priced_inputs_hash=orm_sku.priced_inputs_hash,
            priced_failure_reason=orm_sku.priced_failure_reason,
            is_active=orm_sku.is_active,
            version=orm_sku.version,
            deleted_at=orm_sku.deleted_at,
            created_at=orm_sku.created_at,
            updated_at=orm_sku.updated_at,
            variant_attributes=[
                (link.attribute_id, link.attribute_value_id)
                for link in orm_sku.attribute_values
            ],
        )

    def _sku_to_orm(
        self, domain_sku: DomainSKU, orm_sku: OrmSKU | None = None
    ) -> OrmSKU:
        """Map a domain SKU entity to an ORM SKU row.

        When ``orm_sku`` is ``None`` a new row is created with safe defaults
        for ORM-only fields (``attributes_cache``).
        When updating an existing row those fields are preserved.
        """
        is_create = orm_sku is None
        if orm_sku is None:
            orm_sku = OrmSKU()

        orm_sku.id = domain_sku.id
        orm_sku.product_id = domain_sku.product_id
        orm_sku.variant_id = domain_sku.variant_id
        orm_sku.sku_code = domain_sku.sku_code
        orm_sku.variant_hash = domain_sku.variant_hash
        orm_sku.is_active = domain_sku.is_active
        orm_sku.version = domain_sku.version
        orm_sku.deleted_at = domain_sku.deleted_at

        # Only set timestamps on create; let DB server_default / onupdate handle them
        if is_create:
            orm_sku.created_at = domain_sku.created_at
            orm_sku.updated_at = domain_sku.updated_at

        # Money VO decomposition (price is now nullable)
        if domain_sku.price is not None:
            orm_sku.price = domain_sku.price.amount
            orm_sku.currency = domain_sku.price.currency
        else:
            orm_sku.price = None
            # currency stays as-is or from variant
        orm_sku.compare_at_price = (
            domain_sku.compare_at_price.amount
            if domain_sku.compare_at_price is not None
            else None
        )

        # ADR-005 — purchase price + autonomous pricing FSM provenance
        if domain_sku.purchase_price is not None:
            orm_sku.purchase_price = domain_sku.purchase_price.amount
        else:
            orm_sku.purchase_price = None
        orm_sku.purchase_currency = (
            domain_sku.purchase_currency.value
            if domain_sku.purchase_currency is not None
            else None
        )
        if domain_sku.selling_price is not None:
            orm_sku.selling_price = domain_sku.selling_price.amount
            orm_sku.selling_currency = domain_sku.selling_price.currency
        else:
            orm_sku.selling_price = None
            orm_sku.selling_currency = None
        orm_sku.pricing_status = domain_sku.pricing_status
        orm_sku.priced_at = domain_sku.priced_at
        orm_sku.priced_with_formula_version_id = (
            domain_sku.priced_with_formula_version_id
        )
        orm_sku.priced_inputs_hash = domain_sku.priced_inputs_hash
        orm_sku.priced_failure_reason = domain_sku.priced_failure_reason

        # ORM-only fields: set defaults on create, preserve on update
        if is_create:
            orm_sku.attributes_cache = {}

        # Sync variant_attributes -> SKUAttributeValueLink rows (diff-based)
        desired_pairs = {(a_id, v_id) for a_id, v_id in domain_sku.variant_attributes}
        existing_pairs = {
            (link.attribute_id, link.attribute_value_id)
            for link in orm_sku.attribute_values
        }

        if desired_pairs != existing_pairs:
            # Delete links that are no longer desired
            to_remove = [
                link
                for link in orm_sku.attribute_values
                if (link.attribute_id, link.attribute_value_id) not in desired_pairs
            ]
            for link in to_remove:
                orm_sku.attribute_values.remove(link)

            # Add links that don't exist yet
            pairs_to_add = desired_pairs - existing_pairs
            for attr_id, attr_val_id in pairs_to_add:
                orm_sku.attribute_values.append(
                    OrmSKUAttrLink(
                        sku_id=domain_sku.id,
                        attribute_id=attr_id,
                        attribute_value_id=attr_val_id,
                    )
                )

        return orm_sku

    def _variant_to_domain(
        self, orm_variant: OrmProductVariant
    ) -> DomainProductVariant:
        """Map an ORM ProductVariant row to a domain ProductVariant entity."""
        default_price: Money | None = None
        if orm_variant.default_price is not None:
            default_price = Money(
                amount=orm_variant.default_price, currency=orm_variant.default_currency
            )
        return DomainProductVariant(
            id=orm_variant.id,
            product_id=orm_variant.product_id,
            name_i18n=dict(orm_variant.name_i18n) if orm_variant.name_i18n else {},
            description_i18n=dict(orm_variant.description_i18n)
            if orm_variant.description_i18n
            else None,
            sort_order=orm_variant.sort_order,
            default_price=default_price,
            default_currency=orm_variant.default_currency,
            skus=[self._sku_to_domain(sku) for sku in orm_variant.skus],
            deleted_at=orm_variant.deleted_at,
            created_at=orm_variant.created_at,
            updated_at=orm_variant.updated_at,
        )

    def _variant_to_orm(
        self,
        domain_variant: DomainProductVariant,
        orm_variant: OrmProductVariant | None = None,
    ) -> OrmProductVariant:
        """Map a domain ProductVariant entity to an ORM row (create or update)."""
        is_create = orm_variant is None
        if orm_variant is None:
            orm_variant = OrmProductVariant()
        orm_variant.id = domain_variant.id
        orm_variant.product_id = domain_variant.product_id
        orm_variant.name_i18n = domain_variant.name_i18n
        orm_variant.description_i18n = domain_variant.description_i18n
        orm_variant.sort_order = domain_variant.sort_order
        orm_variant.default_price = (
            domain_variant.default_price.amount
            if domain_variant.default_price is not None
            else None
        )
        orm_variant.default_currency = domain_variant.default_currency
        orm_variant.deleted_at = domain_variant.deleted_at

        # Only set timestamps on create; let DB server_default / onupdate handle them
        if is_create:
            orm_variant.created_at = domain_variant.created_at
            orm_variant.updated_at = domain_variant.updated_at

        return orm_variant

    def _base_product_fields(self, orm: OrmProduct) -> dict:
        """Extract common Product fields from an ORM row into a dict."""
        return {
            "id": orm.id,
            "slug": orm.slug,
            "title_i18n": dict(orm.title_i18n) if orm.title_i18n else {},
            "description_i18n": dict(orm.description_i18n)
            if orm.description_i18n
            else {},
            "status": ProductStatus(orm.status.value),
            "brand_id": orm.brand_id,
            "primary_category_id": orm.primary_category_id,
            "supplier_id": orm.supplier_id,
            "country_of_origin": orm.country_of_origin,
            "tags": list(orm.tags) if orm.tags else [],
            "source_url": orm.source_url,
            "version": orm.version,
            "deleted_at": orm.deleted_at,
            "created_at": orm.created_at,
            "updated_at": orm.updated_at,
            "published_at": orm.published_at,
        }

    def _to_domain(self, orm: OrmProduct) -> DomainProduct:
        """Map an ORM Product row to a domain Product entity WITH variants.

        Callers must ensure ``orm.variants`` (and nested SKUs) are loaded
        (via ``selectinload``) before calling this method.
        """
        return DomainProduct(
            **self._base_product_fields(orm),
            variants=[self._variant_to_domain(v) for v in orm.variants],
        )

    def _to_domain_without_skus(self, orm: OrmProduct) -> DomainProduct:
        """Map an ORM Product row to a domain Product entity WITHOUT variants.

        Used by methods that do not eager-load variants (``get``, ``get_by_slug``,
        ``get_for_update``) to avoid lazy-load errors in async sessions.
        """
        return DomainProduct(
            **self._base_product_fields(orm),
            variants=[],
        )

    def _to_orm(
        self, entity: DomainProduct, orm: OrmProduct | None = None
    ) -> OrmProduct:
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
        orm.supplier_id = entity.supplier_id
        orm.deleted_at = entity.deleted_at
        orm.published_at = entity.published_at
        orm.country_of_origin = entity.country_of_origin

        # Only set version and timestamps on create; let DB handle them on update
        if is_create:
            orm.version = entity.version
            orm.created_at = entity.created_at
            orm.updated_at = entity.updated_at

        orm.status = ProductStatus(entity.status.value)
        orm.title_i18n = entity.title_i18n
        orm.description_i18n = entity.description_i18n
        orm.tags = list(entity.tags)
        orm.source_url = entity.source_url

        # ORM-only fields: set defaults on create, preserve on update
        if is_create:
            orm.popularity_score = 0
            orm.is_visible = True
            orm.attributes = {}

        return orm

    def _sync_variants(self, product: DomainProduct, orm: OrmProduct) -> None:
        """Reconcile domain variant list with the ORM variant collection.

        Handles additions, updates, and removals of child variant entities
        and their nested SKUs.
        """
        existing_variants: dict[uuid.UUID, OrmProductVariant] = {
            v.id: v for v in orm.variants
        }
        domain_variant_ids: set[uuid.UUID] = set()

        for domain_variant in product.variants:
            domain_variant_ids.add(domain_variant.id)
            existing_orm_variant = existing_variants.get(domain_variant.id)
            if existing_orm_variant is not None:
                self._variant_to_orm(domain_variant, existing_orm_variant)
                # Sync SKUs within this variant
                self._sync_skus_for_variant(domain_variant, existing_orm_variant)
            else:
                new_orm_variant = self._variant_to_orm(domain_variant)
                for domain_sku in domain_variant.skus:
                    new_orm_variant.skus.append(self._sku_to_orm(domain_sku))
                orm.variants.append(new_orm_variant)

        to_remove = [
            v
            for v in orm.variants
            if v.id not in domain_variant_ids and v.deleted_at is None
        ]
        for v in to_remove:
            orm.variants.remove(v)

    def _sync_skus_for_variant(
        self, domain_variant: DomainProductVariant, orm_variant: OrmProductVariant
    ) -> None:
        """Reconcile domain SKU list within a single variant."""
        existing_by_id: dict[uuid.UUID, OrmSKU] = {
            sku.id: sku for sku in orm_variant.skus
        }
        domain_sku_ids: set[uuid.UUID] = set()

        for domain_sku in domain_variant.skus:
            domain_sku_ids.add(domain_sku.id)
            existing_orm_sku = existing_by_id.get(domain_sku.id)
            if existing_orm_sku is not None:
                self._sku_to_orm(domain_sku, existing_orm_sku)
            else:
                new_orm_sku = self._sku_to_orm(domain_sku)
                orm_variant.skus.append(new_orm_sku)

        to_remove = [
            sku
            for sku in orm_variant.skus
            if sku.id not in domain_sku_ids and sku.deleted_at is None
        ]
        for sku in to_remove:
            orm_variant.skus.remove(sku)

    # ------------------------------------------------------------------
    # Public methods -- IProductRepository + ICatalogRepository
    # ------------------------------------------------------------------

    async def add(self, entity: DomainProduct) -> DomainProduct:
        """Persist a new product and return the refreshed domain entity.

        Raises:
            ConcurrencyError: If an optimistic locking conflict is detected.
        """
        orm = self._to_orm(entity)

        for domain_variant in entity.variants:
            orm_variant = self._variant_to_orm(domain_variant)
            for domain_sku in domain_variant.skus:
                orm_variant.skus.append(self._sku_to_orm(domain_sku))
            orm.variants.append(orm_variant)

        self._session.add(orm)

        try:
            await self._session.flush()
        except StaleDataError:
            raise ConcurrencyError(
                entity_type="Product",
                entity_id=entity.id,
                expected_version=entity.version,
                actual_version=None,
            ) from None
        except IntegrityError as e:
            constraint = str(e.orig) if e.orig else str(e)
            if "uix_products_slug" in constraint:
                raise ProductSlugConflictError(slug=entity.slug) from e
            raise

        # Return domain entity built from the original input + generated fields.
        # Using _to_domain(orm) would trigger lazy-load of variant.skus in
        # async context (MissingGreenlet).  Since add() only inserts, the
        # caller already has the complete entity; we just need the DB-assigned
        # version and timestamps.
        return entity

    async def get(self, entity_id: uuid.UUID) -> DomainProduct | None:
        """Retrieve a product by primary key, or ``None`` if not found.

        Soft-deleted products are excluded. SKUs are NOT loaded.
        """
        orm = await self._session.get(OrmProduct, entity_id, populate_existing=True)
        if orm is None or orm.deleted_at is not None:
            return None
        return self._to_domain_without_skus(orm)

    async def update(self, entity: DomainProduct) -> DomainProduct:
        """Merge updated domain state into the existing ORM row.

        Eagerly loads variants and their SKU/attribute-value links to enable
        proper reconciliation via ``_sync_variants``.

        Raises:
            ValueError: If the product row does not exist.
            ConcurrencyError: If an optimistic locking conflict is detected.
        """
        stmt = (
            select(OrmProduct)
            .where(OrmProduct.id == entity.id)
            .options(
                selectinload(OrmProduct.variants)
                .selectinload(OrmProductVariant.skus)
                .selectinload(OrmSKU.attribute_values)
            )
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None:
            raise ValueError(f"Product with id {entity.id} not found in DB")

        self._to_orm(entity, orm)
        self._sync_variants(entity, orm)

        try:
            await self._session.flush()
        except StaleDataError:
            raise ConcurrencyError(
                entity_type="Product",
                entity_id=entity.id,
                expected_version=entity.version,
                actual_version=None,
            ) from None

        # Return the input domain entity instead of re-mapping from ORM.
        # After flush(), ORM attributes are expired and _to_domain(orm)
        # triggers lazy loads that fail in async context (MissingGreenlet).
        return entity

    async def delete(self, entity_id: uuid.UUID) -> None:
        """Hard-delete a product row by primary key."""
        stmt = delete(OrmProduct).where(OrmProduct.id == entity_id)
        await self._session.execute(stmt)

    async def check_sku_code_exists(
        self, sku_code: str, exclude_sku_id: uuid.UUID | None = None
    ) -> bool:
        """Return ``True`` if any non-deleted SKU already uses this code."""
        filters = [OrmSKU.sku_code == sku_code, OrmSKU.deleted_at.is_(None)]
        if exclude_sku_id is not None:
            filters.append(OrmSKU.id != exclude_sku_id)
        stmt = select(OrmSKU.id).where(*filters).limit(1)
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def _field_exists(
        self,
        field_name: str,
        value: object,
        *,
        exclude_id: uuid.UUID | None = None,
    ) -> bool:
        """Check whether a non-deleted product row with the given field value exists.

        Args:
            field_name: Name of the ORM column to check (e.g. ``"slug"``).
            value: The value to look for.
            exclude_id: When provided, excludes the row with this primary
                key from the check (used during updates).
        """
        column = getattr(OrmProduct, field_name)
        filters = [column == value, OrmProduct.deleted_at.is_(None)]
        if exclude_id is not None:
            filters.append(OrmProduct.id != exclude_id)
        stmt = select(OrmProduct.id).where(*filters).limit(1)
        result = await self._session.execute(stmt)
        return result.first() is not None

    async def check_slug_exists(self, slug: str) -> bool:
        """Return ``True`` if any non-deleted product already uses this slug."""
        return await self._field_exists("slug", slug)

    async def check_slug_exists_excluding(
        self, slug: str, exclude_id: uuid.UUID
    ) -> bool:
        """Return ``True`` if the slug is taken by another non-deleted product."""
        return await self._field_exists("slug", slug, exclude_id=exclude_id)

    async def get_for_update_with_variants(
        self, product_id: uuid.UUID
    ) -> DomainProduct | None:
        """Retrieve a product with pessimistic lock AND eagerly loaded variants/SKUs.

        Combines ``SELECT FOR UPDATE`` with variant/SKU eager loading so
        that domain methods like ``transition_status`` can inspect child
        entities while holding the row lock.
        """
        stmt = (
            select(OrmProduct)
            .where(OrmProduct.id == product_id, OrmProduct.deleted_at.is_(None))
            .options(
                selectinload(
                    OrmProduct.variants.and_(OrmProductVariant.deleted_at.is_(None))
                )
                .selectinload(OrmProductVariant.skus.and_(OrmSKU.deleted_at.is_(None)))
                .selectinload(OrmSKU.attribute_values)
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is not None:
            return self._to_domain(orm)
        return None

    async def get_with_variants(self, product_id: uuid.UUID) -> DomainProduct | None:
        """Retrieve a product with eagerly loaded variant and SKU child entities.

        Soft-deleted products are excluded. Variants, their SKUs, and
        SKU attribute-value links are loaded via ``selectinload``.
        Deleted variants and SKUs are filtered out.
        """
        stmt = (
            select(OrmProduct)
            .where(OrmProduct.id == product_id)
            .options(
                selectinload(
                    OrmProduct.variants.and_(OrmProductVariant.deleted_at.is_(None))
                )
                .selectinload(OrmProductVariant.skus.and_(OrmSKU.deleted_at.is_(None)))
                .selectinload(OrmSKU.attribute_values)
            )
            .execution_options(populate_existing=True)
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None or orm.deleted_at is not None:
            return None

        return self._to_domain(orm)
