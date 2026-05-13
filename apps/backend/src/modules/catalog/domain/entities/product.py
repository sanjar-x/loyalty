"""
Product aggregate root entity -- central catalog entity.

Owns ProductVariant child entities (which in turn own SKUs), enforces
status lifecycle transitions (FSM), and computes variant hashes for
SKU uniqueness.
Part of the domain layer -- zero infrastructure imports.
"""

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any, ClassVar

from attr import dataclass, field

from src.modules.catalog.domain.events import (
    ProductCreatedEvent,
    ProductDeletedEvent,
    ProductStatusChangedEvent,
    ProductUpdatedEvent,
    SKUAddedEvent,
    SKUDeletedEvent,
    SKUPurchasePriceUpdatedEvent,
    VariantAddedEvent,
    VariantDeletedEvent,
)
from src.modules.catalog.domain.exceptions import (
    CannotDeletePublishedProductError,
    DuplicateVariantCombinationError,
    InvalidStatusTransitionError,
    LastVariantRemovalError,
    ProductNotReadyError,
    SKUNotFoundError,
    VariantNotFoundError,
)
from src.modules.catalog.domain.value_objects import (
    DEFAULT_CURRENCY,
    Money,
    ProductStatus,
    PurchaseCurrency,
    SkuPricingStatus,
    validate_i18n_completeness,
)
from src.shared.interfaces.entities import AggregateRoot

from ._common import _generate_id, _validate_i18n_values, _validate_slug
from .product_variant import ProductVariant
from .sku import SKU

# ---------------------------------------------------------------------------
# DDD-01: Guarded fields set -- fields that may only be changed through
# explicit domain methods, never by direct attribute assignment.
# ---------------------------------------------------------------------------

_PRODUCT_GUARDED_FIELDS: frozenset[str] = frozenset({"status"})


# ---------------------------------------------------------------------------
# CAT-019 — actionable diagnostic for the publish-pricing gate.
# ---------------------------------------------------------------------------


def _publish_diagnostic_for_sku(s: SKU) -> dict:
    """One row of per-SKU breakdown for ``ProductNotReadyError.details``.

    The admin UI consumes this to show a per-SKU next-step instead of
    the generic "no SKU has a price" message. Each row carries:

    * ``sku_id`` — UUID of the SKU
    * ``sku_code`` — admin-visible code
    * ``pricing_status`` — current FSM state of the recompute pipeline
    * ``has_manual_price`` — whether ``s.price`` is set (manual fallback)
    * ``has_selling_price`` — whether autonomous recompute landed
    * ``has_purchase_price`` — input to the recompute pipeline
    * ``failure_reason`` — populated for ``stale_fx`` /
      ``missing_purchase_price`` / ``formula_error``
    * ``next_step`` — operator-actionable hint derived from the above
    """
    next_step = _next_step_for(s)
    return {
        "sku_id": str(s.id),
        "sku_code": s.sku_code,
        "pricing_status": s.pricing_status.value,
        "has_manual_price": s.price is not None,
        "has_selling_price": s.selling_price is not None,
        "has_purchase_price": s.purchase_price is not None,
        "failure_reason": s.priced_failure_reason,
        "next_step": next_step,
    }


def _next_step_for(s: SKU) -> str:
    """Derive an operator-readable next-step from the SKU's pricing state."""
    if s.price is not None or s.selling_price is not None:
        # Defensive — gate failure means none should reach this branch,
        # but if a SKU is priced and the gate still fails (corrupt
        # state), say so rather than printing a misleading next-step.
        return "ok (already priced — investigate why publish gate fired)"
    status = s.pricing_status
    if status is SkuPricingStatus.PENDING:
        return (
            "Recompute is in flight. Wait a few seconds and retry, "
            "or open the SSE stream to see when it lands."
        )
    if status is SkuPricingStatus.MISSING_PURCHASE_PRICE:
        return (
            "Set ``purchase_price`` on this SKU — the recompute pipeline "
            "needs it to derive ``selling_price``. Alternatively, set a "
            "manual ``price`` to bypass autonomous pricing."
        )
    if status is SkuPricingStatus.STALE_FX:
        return (
            "FX rate is stale — ask an admin to refresh the FX rate on "
            "the pricing context, then re-save ``purchase_price`` to "
            "trigger a fresh recompute."
        )
    if status is SkuPricingStatus.FORMULA_ERROR:
        return (
            "Pricing formula failed to evaluate — see "
            "``failure_reason``. Either fix the formula version, "
            "set a manual ``price`` as fallback, or investigate the "
            "supplier-type → context mapping."
        )
    if status is SkuPricingStatus.LEGACY:
        return (
            "Legacy SKU never went through the recompute pipeline. "
            "Either set ``purchase_price`` (to opt in to autonomous "
            "pricing) or set a manual ``price``."
        )
    if status is SkuPricingStatus.PRICED:
        # Shouldn't happen — PRICED implies selling_price is set.
        return "ok (corrupt state — PRICED without selling_price)"
    return f"unknown pricing_status: {status.value}"


@dataclass
class Product(AggregateRoot):
    """Product aggregate root -- central catalog entity.

    Owns ProductVariant child entities (which in turn own SKUs), enforces
    status lifecycle transitions (FSM), and computes variant hashes for
    SKU uniqueness.  Carries a ``version``
    field for optimistic locking (incremented by the repository on save)
    and supports soft-delete via ``deleted_at``.

    Emits ProductCreatedEvent on creation and ProductStatusChangedEvent on status transitions.

    Status FSM (allowed transitions)::

        DRAFT -> ENRICHING
        ENRICHING -> DRAFT | READY_FOR_REVIEW
        READY_FOR_REVIEW -> ENRICHING | PUBLISHED
        PUBLISHED -> ARCHIVED
        ARCHIVED -> DRAFT

    Attributes:
        id: Unique product identifier.
        slug: URL-safe unique identifier for routing.
        title_i18n: Multilingual product title (at least one entry required).
        description_i18n: Multilingual product description.
        status: Current lifecycle state (FSM-controlled).
        brand_id: FK to the Brand aggregate.
        primary_category_id: FK to the primary Category.
        supplier_id: FK to the Supplier, or None.
        country_of_origin: ISO 3166-1 alpha-2 country code, or None.
        tags: List of searchable tags.
        version: Optimistic locking version counter (managed by repo).
        deleted_at: Soft-delete timestamp, or None if active.
        created_at: Creation timestamp (UTC).
        updated_at: Last modification timestamp (UTC).
        published_at: Timestamp of first publication, or None.
        variants: List of owned ProductVariant child entities (includes soft-deleted).
    """

    # Class-level FSM transition table -- excluded from attrs __init__ via ClassVar.
    _ALLOWED_TRANSITIONS: ClassVar[dict[ProductStatus, set[ProductStatus]]] = {
        ProductStatus.DRAFT: {ProductStatus.ENRICHING},
        ProductStatus.ENRICHING: {ProductStatus.DRAFT, ProductStatus.READY_FOR_REVIEW},
        ProductStatus.READY_FOR_REVIEW: {
            ProductStatus.ENRICHING,
            ProductStatus.PUBLISHED,
        },
        ProductStatus.PUBLISHED: {ProductStatus.ARCHIVED},
        ProductStatus.ARCHIVED: {ProductStatus.DRAFT},
    }

    id: uuid.UUID
    slug: str
    title_i18n: dict[str, str]
    description_i18n: dict[str, str]
    status: ProductStatus
    brand_id: uuid.UUID
    primary_category_id: uuid.UUID
    supplier_id: uuid.UUID | None = None
    source_url: str | None = None
    country_of_origin: str | None = None
    _tags: list[str] = field(factory=list, alias="tags")
    version: int = 1
    deleted_at: datetime | None = None
    created_at: datetime = field(factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(factory=lambda: datetime.now(UTC))
    published_at: datetime | None = None
    _variants: list[ProductVariant] = field(factory=list, alias="variants")

    @property
    def tags(self) -> tuple[str, ...]:
        """Read-only view of product tags."""
        return tuple(self._tags)

    @property
    def variants(self) -> tuple[ProductVariant, ...]:
        """Read-only view of product variants. Use add_variant()/remove_variant() to mutate."""
        return tuple(self._variants)

    # DDD-01: guard status against direct mutation
    def __setattr__(self, name: str, value: object) -> None:
        if name in _PRODUCT_GUARDED_FIELDS and getattr(
            self, "_Product__initialized", False
        ):
            raise AttributeError(
                f"Cannot set '{name}' directly on Product. Use transition_status() instead."
            )
        super().__setattr__(name, value)

    def __attrs_post_init__(self) -> None:
        super().__attrs_post_init__()
        object.__setattr__(self, "_Product__initialized", True)

    @classmethod
    def create(
        cls,
        *,
        slug: str,
        title_i18n: dict[str, str],
        brand_id: uuid.UUID,
        primary_category_id: uuid.UUID,
        description_i18n: dict[str, str] | None = None,
        supplier_id: uuid.UUID | None = None,
        source_url: str | None = None,
        country_of_origin: str | None = None,
        tags: list[str] | None = None,
        product_id: uuid.UUID | None = None,
    ) -> Product:
        """Factory method to construct a new Product in DRAFT status.

        Args:
            slug: URL-safe unique identifier.
            title_i18n: Multilingual product title. At least one entry required.
            brand_id: UUID of the owning Brand aggregate.
            primary_category_id: UUID of the primary Category.
            description_i18n: Optional multilingual description.
            supplier_id: Optional UUID of the Supplier.
            country_of_origin: Optional ISO 3166-1 alpha-2 country code.
            tags: Optional list of searchable tags.
            product_id: Optional pre-generated UUID; generates uuid7/uuid4 if omitted.

        Returns:
            A new Product instance in DRAFT status with one default variant.

        Raises:
            ValueError: If ``title_i18n`` is empty.
        """
        _validate_slug(slug, "Product")
        if not title_i18n:
            raise ValueError("title_i18n must contain at least one language entry")
        _validate_i18n_values(title_i18n, "title_i18n")
        validate_i18n_completeness(title_i18n, "title_i18n")

        product = cls(
            id=product_id or _generate_id(),
            slug=slug,
            title_i18n=title_i18n,
            description_i18n=description_i18n or {},
            status=ProductStatus.DRAFT,
            brand_id=brand_id,
            primary_category_id=primary_category_id,
            supplier_id=supplier_id,
            source_url=source_url,
            country_of_origin=country_of_origin,
            tags=tags or [],
            version=1,
            variants=[],
        )
        # Auto-create 1 default variant
        default_variant = ProductVariant.create(
            product_id=product.id,
            name_i18n=title_i18n,
        )
        product._variants.append(default_variant)
        product.add_domain_event(
            ProductCreatedEvent(
                product_id=product.id,
                slug=product.slug,
                aggregate_id=str(product.id),
            )
        )
        return product

    _UPDATABLE_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "title_i18n",
            "description_i18n",
            "slug",
            "brand_id",
            "primary_category_id",
            "supplier_id",
            "country_of_origin",
            "tags",
        }
    )

    def update(self, **kwargs: Any) -> None:
        """Update mutable product fields.

        Only fields present in ``kwargs`` are modified; absent fields are
        left unchanged.  Nullable fields (``supplier_id``,
        ``country_of_origin``) can be set to ``None`` to clear them.

        Args:
            **kwargs: Field-name/value pairs to update.  Supported keys:
                ``title_i18n``, ``description_i18n``, ``slug``, ``brand_id``,
                ``primary_category_id``, ``supplier_id``, ``country_of_origin``,
                ``tags``.

        Raises:
            TypeError: If an unknown/immutable field name is passed.
            ValueError: If ``title_i18n`` is provided but empty, or if
                ``brand_id`` / ``primary_category_id`` is set to None.
        """
        unknown = set(kwargs) - self._UPDATABLE_FIELDS
        if unknown:
            raise TypeError(f"Cannot update immutable/unknown fields: {unknown}")

        changed = False

        if "title_i18n" in kwargs:
            if not kwargs["title_i18n"]:
                raise ValueError("title_i18n must contain at least one language entry")
            _validate_i18n_values(kwargs["title_i18n"], "title_i18n")
            validate_i18n_completeness(kwargs["title_i18n"], "title_i18n")
            self.title_i18n = kwargs["title_i18n"]
            changed = True

        if "description_i18n" in kwargs:
            self.description_i18n = kwargs["description_i18n"] or {}
            changed = True

        if "slug" in kwargs:
            _validate_slug(kwargs["slug"], "Product")
            self.slug = kwargs["slug"]
            changed = True

        if "brand_id" in kwargs:
            if kwargs["brand_id"] is None:
                raise ValueError("brand_id cannot be None")
            self.brand_id = kwargs["brand_id"]
            changed = True

        if "primary_category_id" in kwargs:
            if kwargs["primary_category_id"] is None:
                raise ValueError("primary_category_id cannot be None")
            self.primary_category_id = kwargs["primary_category_id"]
            changed = True

        if "supplier_id" in kwargs:
            self.supplier_id = kwargs["supplier_id"]  # can be None
            changed = True

        if "country_of_origin" in kwargs:
            self.country_of_origin = kwargs["country_of_origin"]  # can be None
            changed = True

        if "tags" in kwargs:
            self._tags = list(kwargs["tags"])
            changed = True

        if changed:
            self.updated_at = datetime.now(UTC)
            self.add_domain_event(
                ProductUpdatedEvent(
                    product_id=self.id,
                    aggregate_id=str(self.id),
                )
            )

    def soft_delete(self) -> None:
        """Mark this product as deleted.

        Sets ``deleted_at`` and ``updated_at`` to the current UTC timestamp.
        Cascades soft-delete to all active variants (which in turn cascade
        to their SKUs). The record is retained in the database; queries
        must exclude non-None ``deleted_at`` when listing active products.

        Raises:
            InvalidStatusTransitionError: If the product is currently
                PUBLISHED -- it must be ARCHIVED first.
        """
        if self.deleted_at is not None:
            return
        if self.status == ProductStatus.PUBLISHED:
            raise CannotDeletePublishedProductError(
                product_id=self.id,
                current_status=self.status.value,
            )
        now = datetime.now(UTC)
        self.deleted_at = now
        self.updated_at = now
        for variant in self.variants:
            if variant.deleted_at is None:
                variant.soft_delete()
        self.add_domain_event(
            ProductDeletedEvent(
                product_id=self.id,
                slug=self.slug,
                aggregate_id=str(self.id),
            )
        )

    def transition_status(self, new_status: ProductStatus) -> None:
        """Transition the product to a new lifecycle status.

        Validates the transition against the FSM table defined in
        ``_ALLOWED_TRANSITIONS``.  If transitioning to PUBLISHED, sets
        ``published_at`` to the current UTC timestamp (only set once;
        not cleared on subsequent transitions).

        Args:
            new_status: The target ProductStatus value.

        Raises:
            InvalidStatusTransitionError: If ``new_status`` is not in the
                set of allowed transitions from the current ``status``.
        """
        allowed = self._ALLOWED_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise InvalidStatusTransitionError(
                current_status=self.status,
                target_status=new_status,
                allowed_transitions=list(allowed),
            )
        if new_status in (ProductStatus.PUBLISHED, ProductStatus.READY_FOR_REVIEW):
            active_skus = [
                s
                for v in self.variants
                if v.deleted_at is None
                for s in v.skus
                if s.deleted_at is None and s.is_active
            ]
            if not active_skus:
                raise ProductNotReadyError(
                    product_id=self.id,
                    reason=f"Cannot transition to {new_status.value}: product has no active SKUs",
                )
            # CAT-009 — accept either a manual ``price`` (legacy / fallback
            # path) OR an autonomous ``selling_price`` produced by the
            # ADR-005 recompute pipeline.
            # CAT-019 — when the gate fails, attach a per-SKU diagnostic
            # so the admin UI can show actionable next-steps instead of
            # the generic "no SKU has a price" message.
            if new_status == ProductStatus.PUBLISHED and not any(
                s.price is not None or s.selling_price is not None for s in active_skus
            ):
                sku_diagnostics = [_publish_diagnostic_for_sku(s) for s in active_skus]
                raise ProductNotReadyError(
                    product_id=self.id,
                    reason=(
                        "Cannot publish — no active SKU has a price. "
                        "See ``sku_diagnostics`` for per-SKU next steps."
                    ),
                    sku_diagnostics=sku_diagnostics,
                )
        old_status = self.status.value
        # Bypass the guard for controlled FSM mutation
        object.__setattr__(self, "status", new_status)
        if new_status == ProductStatus.PUBLISHED and self.published_at is None:
            self.published_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)
        self.add_domain_event(
            ProductStatusChangedEvent(
                product_id=self.id,
                old_status=old_status,
                new_status=new_status.value,
                aggregate_id=str(self.id),
            )
        )

    # ------------------------------------------------------------------
    # Variant management
    # ------------------------------------------------------------------

    def add_variant(
        self,
        *,
        name_i18n: dict[str, str],
        description_i18n: dict[str, str] | None = None,
        sort_order: int = 0,
        default_price: Money | None = None,
        default_currency: str = DEFAULT_CURRENCY,
    ) -> ProductVariant:
        """Create and attach a new ProductVariant to this product.

        Args:
            name_i18n: Multilingual variant name. At least one entry required.
            description_i18n: Optional multilingual description.
            sort_order: Display ordering among sibling variants (default: 0).
            default_price: Optional default price for SKUs in this variant.
            default_currency: Default currency code (default: "RUB").

        Returns:
            The newly created and attached ProductVariant instance.
        """
        variant = ProductVariant.create(
            product_id=self.id,
            name_i18n=name_i18n,
            description_i18n=description_i18n,
            sort_order=sort_order,
            default_price=default_price,
            default_currency=default_currency,
        )
        self._variants.append(variant)
        self.add_domain_event(
            VariantAddedEvent(
                product_id=self.id, variant_id=variant.id, aggregate_id=str(self.id)
            )
        )
        self.updated_at = datetime.now(UTC)
        return variant

    def find_variant(self, variant_id: uuid.UUID) -> ProductVariant | None:
        """Find an active (non-deleted) variant by its identifier.

        Args:
            variant_id: The UUID of the variant to locate.

        Returns:
            The matching ProductVariant instance, or None if not found or soft-deleted.
        """
        for variant in self.variants:
            if variant.id == variant_id and variant.deleted_at is None:
                return variant
        return None

    def remove_variant(self, variant_id: uuid.UUID) -> None:
        """Soft-delete a variant and all its SKUs from this product.

        Cannot delete the last active variant.

        Args:
            variant_id: The UUID of the variant to delete.

        Raises:
            VariantNotFoundError: If no active variant with the given ID exists.
            LastVariantRemovalError: If this is the only remaining active variant.
        """
        variant = self.find_variant(variant_id)
        if variant is None:
            raise VariantNotFoundError(variant_id=variant_id, product_id=self.id)
        active_variants = [v for v in self.variants if v.deleted_at is None]
        if len(active_variants) <= 1:
            raise LastVariantRemovalError(product_id=self.id)
        variant.soft_delete()
        self.add_domain_event(
            VariantDeletedEvent(
                product_id=self.id, variant_id=variant_id, aggregate_id=str(self.id)
            )
        )
        self.updated_at = datetime.now(UTC)

    # ------------------------------------------------------------------
    # SKU management (delegated through variants)
    # ------------------------------------------------------------------

    def add_sku(
        self,
        variant_id: uuid.UUID,
        *,
        sku_code: str,
        price: Money | None = None,
        compare_at_price: Money | None = None,
        purchase_price: Money | None = None,
        purchase_currency: PurchaseCurrency | None = None,
        is_active: bool = True,
        variant_attributes: list[tuple[uuid.UUID, uuid.UUID]] | None = None,
    ) -> SKU:
        """Create and attach a new SKU to a specific variant of this product.

        Computes the ``variant_hash`` from ``variant_attributes`` and checks
        it is unique among non-deleted SKUs across ALL variants.

        Args:
            variant_id: UUID of the target ProductVariant.
            sku_code: Human-readable stock-keeping code.
            price: Optional base selling price (can be None; inherits from variant).
            compare_at_price: Optional strikethrough price (must be > price).
            purchase_price: Wholesale cost (CAT-001). When provided, drives
                the autonomous pricing recompute pipeline (ADR-005).
                ``purchase_currency`` must be supplied alongside.
            purchase_currency: Required iff ``purchase_price`` is provided.
            is_active: Whether the new SKU is immediately available.
            variant_attributes: List of (attribute_id, attribute_value_id) pairs
                that uniquely identify this variant combination.

        Returns:
            The newly created and attached SKU instance.

        Raises:
            VariantNotFoundError: If no active variant with the given ID exists.
            DuplicateVariantCombinationError: If an active SKU with the same
                variant attribute combination already exists.
            ValueError: If only one of ``purchase_price`` / ``purchase_currency``
                is provided, or their currencies disagree.
        """
        variant = self.find_variant(variant_id)
        if variant is None:
            raise VariantNotFoundError(variant_id=variant_id, product_id=self.id)
        # compute hash, check uniqueness across ALL variants
        effective_attrs = variant_attributes or []
        variant_hash = self.compute_variant_hash(variant_id, effective_attrs)
        for v in self.variants:
            for existing in v.skus:
                if (
                    existing.deleted_at is None
                    and existing.variant_hash == variant_hash
                ):
                    raise DuplicateVariantCombinationError(
                        product_id=self.id,
                        variant_hash=variant_hash,
                    )
        sku = SKU(
            id=_generate_id(),
            product_id=self.id,
            variant_id=variant_id,
            sku_code=sku_code,
            variant_hash=variant_hash,
            price=price,
            compare_at_price=compare_at_price,
            is_active=is_active,
            variant_attributes=list(effective_attrs),
        )
        if purchase_price is not None or purchase_currency is not None:
            if purchase_price is None or purchase_currency is None:
                raise ValueError(
                    "purchase_price and purchase_currency must be set together"
                )
            sku.set_purchase_price(
                purchase_price=purchase_price,
                purchase_currency=purchase_currency,
            )
            # CAT-010 — emit on the aggregate so the outbox relay arms the
            # autonomous recompute pipeline. ``SKU.set_purchase_price``
            # arms ``pricing_status=PENDING`` but only the aggregate root
            # accumulates domain events; without this emit the SKU sits
            # in PENDING forever and the storefront never sees a price.
            self.add_domain_event(
                SKUPurchasePriceUpdatedEvent(
                    product_id=self.id,
                    variant_id=variant_id,
                    sku_id=sku.id,
                    purchase_price_amount=purchase_price.amount,
                    purchase_currency=purchase_currency.value,
                    aggregate_id=str(self.id),
                )
            )
        variant._skus.append(sku)
        self.add_domain_event(
            SKUAddedEvent(
                product_id=self.id,
                variant_id=variant_id,
                sku_id=sku.id,
                aggregate_id=str(self.id),
            )
        )
        self.updated_at = datetime.now(UTC)
        return sku

    def find_sku(self, sku_id: uuid.UUID) -> SKU | None:
        """Find an active (non-deleted) SKU by its identifier across all variants.

        Args:
            sku_id: The UUID of the SKU to locate.

        Returns:
            The matching SKU instance, or None if not found or soft-deleted.
        """
        for variant in self.variants:
            for sku in variant.skus:
                if sku.id == sku_id and sku.deleted_at is None:
                    return sku
        return None

    def remove_sku(self, sku_id: uuid.UUID) -> None:
        """Soft-delete a SKU from this product (searches across all variants).

        Args:
            sku_id: The UUID of the SKU to delete.

        Raises:
            SKUNotFoundError: If no active SKU with the given ID exists.
        """
        for variant in self.variants:
            for sku in variant.skus:
                if sku.id == sku_id and sku.deleted_at is None:
                    sku.soft_delete()
                    self.add_domain_event(
                        SKUDeletedEvent(
                            product_id=self.id,
                            variant_id=variant.id,
                            sku_id=sku_id,
                            aggregate_id=str(self.id),
                        )
                    )
                    self.updated_at = datetime.now(UTC)
                    return
        raise SKUNotFoundError(sku_id=sku_id)

    @staticmethod
    def compute_variant_hash(
        variant_id: uuid.UUID,
        variant_attributes: list[tuple[uuid.UUID, uuid.UUID]],
    ) -> str:
        """Compute a deterministic SHA-256 hash for a variant attribute combination.

        Includes ``variant_id`` in the hash so that different variants can
        each have an empty-attributes SKU without collision.  Sorts pairs
        by attribute_id (as string) before hashing so that the result is
        independent of insertion order.

        Args:
            variant_id: UUID of the owning ProductVariant.
            variant_attributes: List of (attribute_id, attribute_value_id) pairs.

        Returns:
            A 64-character lowercase hex string (SHA-256 digest).
        """
        sorted_attrs = sorted(variant_attributes, key=lambda x: str(x[0]))
        payload = (
            str(variant_id) + ":" + "|".join(f"{a!s}:{v!s}" for a, v in sorted_attrs)
        )
        return hashlib.sha256(payload.encode()).hexdigest()
