"""Pricing domain interfaces (ports)."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from src.modules.pricing.domain.entities import ProductPricingProfile
from src.modules.pricing.domain.entities.category_pricing_settings import (
    CategoryPricingSettings,
)
from src.modules.pricing.domain.entities.formula import FormulaVersion
from src.modules.pricing.domain.entities.pricing_context import PricingContext
from src.modules.pricing.domain.entities.supplier_pricing_settings import (
    SupplierPricingSettings,
)
from src.modules.pricing.domain.entities.supplier_type_context_mapping import (
    SupplierTypeContextMapping,
)
from src.modules.pricing.domain.entities.variable import Variable
from src.modules.pricing.domain.value_objects import FormulaStatus, VariableScope


class IProductPricingProfileRepository(ABC):
    """Repository contract for the ``ProductPricingProfile`` aggregate."""

    @abstractmethod
    async def add(self, profile: ProductPricingProfile) -> ProductPricingProfile:
        """Persist a newly-created profile."""

    @abstractmethod
    async def update(self, profile: ProductPricingProfile) -> ProductPricingProfile:
        """Persist changes with optimistic-locking enforcement."""

    @abstractmethod
    async def get_by_product_id(
        self,
        product_id: uuid.UUID,
        *,
        include_deleted: bool = False,
    ) -> ProductPricingProfile | None:
        """Fetch the profile for a given product or ``None`` if absent."""

    @abstractmethod
    async def get_by_product_id_for_update(
        self,
        product_id: uuid.UUID,
    ) -> ProductPricingProfile | None:
        """Fetch with ``SELECT FOR UPDATE`` — used inside upsert transactions."""

    @abstractmethod
    async def count_references_to_variable_code(self, code: str) -> int:
        """Count active profiles whose ``values`` map references ``code``.

        Used by the variable-deletion path to block removal of variables that
        are still in use. Only counts *non-deleted* profiles.
        """


@dataclass(frozen=True)
class VariableListFilter:
    """Optional filters for ``IVariableRepository.list``."""

    scope: VariableScope | None = None
    is_system: bool | None = None
    is_fx_rate: bool | None = None


class IVariableRepository(ABC):
    """Repository contract for the ``Variable`` aggregate."""

    @abstractmethod
    async def add(self, variable: Variable) -> Variable:
        """Persist a newly-created variable."""

    @abstractmethod
    async def update(self, variable: Variable) -> Variable:
        """Persist changes with optimistic-locking enforcement."""

    @abstractmethod
    async def delete(self, variable_id: uuid.UUID) -> None:
        """Hard-delete by id. Caller must ensure no references remain."""

    @abstractmethod
    async def get_by_id(self, variable_id: uuid.UUID) -> Variable | None:
        """Fetch by primary key or ``None``."""

    @abstractmethod
    async def get_by_code(self, code: str) -> Variable | None:
        """Fetch by unique code or ``None``."""

    @abstractmethod
    async def list(
        self,
        filters: VariableListFilter | None = None,
    ) -> Sequence[Variable]:
        """Return all variables matching the filter, ordered by ``code``."""


@dataclass(frozen=True)
class PricingContextListFilter:
    """Optional filters for ``IPricingContextRepository.list``."""

    is_active: bool | None = None
    is_frozen: bool | None = None


class IPricingContextRepository(ABC):
    """Repository contract for the ``PricingContext`` aggregate."""

    @abstractmethod
    async def add(self, context: PricingContext) -> PricingContext:
        """Persist a newly-created context."""

    @abstractmethod
    async def update(self, context: PricingContext) -> PricingContext:
        """Persist changes with optimistic-locking enforcement."""

    @abstractmethod
    async def get_by_id(self, context_id: uuid.UUID) -> PricingContext | None:
        """Fetch by primary key or ``None``."""

    @abstractmethod
    async def get_by_code(self, code: str) -> PricingContext | None:
        """Fetch by unique code or ``None``."""

    @abstractmethod
    async def list(
        self,
        filters: PricingContextListFilter | None = None,
    ) -> Sequence[PricingContext]:
        """Return all contexts matching the filter, ordered by ``code``."""


@dataclass(frozen=True)
class FormulaVersionListFilter:
    """Optional filters for ``IFormulaVersionRepository.list_by_context``."""

    status: FormulaStatus | None = None


class IFormulaVersionRepository(ABC):
    """Repository contract for the ``FormulaVersion`` aggregate."""

    @abstractmethod
    async def add(self, version: FormulaVersion) -> FormulaVersion:
        """Persist a newly-created version."""

    @abstractmethod
    async def update(self, version: FormulaVersion) -> FormulaVersion:
        """Persist changes with optimistic-locking enforcement."""

    @abstractmethod
    async def delete(self, version_id: uuid.UUID) -> None:
        """Hard-delete a version (only used for discarding drafts)."""

    @abstractmethod
    async def get_by_id(self, version_id: uuid.UUID) -> FormulaVersion | None:
        """Fetch by primary key or ``None``."""

    @abstractmethod
    async def get_draft_for_context(
        self, context_id: uuid.UUID
    ) -> FormulaVersion | None:
        """Return the current draft for ``context_id`` or ``None``."""

    @abstractmethod
    async def get_published_for_context(
        self, context_id: uuid.UUID
    ) -> FormulaVersion | None:
        """Return the current published version for ``context_id`` or ``None``."""

    @abstractmethod
    async def list_by_context(
        self,
        context_id: uuid.UUID,
        filters: FormulaVersionListFilter | None = None,
    ) -> list[FormulaVersion]:
        """Return all versions for the context ordered by ``version_number`` desc."""

    @abstractmethod
    async def get_max_version_number(self, context_id: uuid.UUID) -> int:
        """Return the largest ``version_number`` for the context, or 0 if empty."""


class ICategoryPricingSettingsRepository(ABC):
    """Repository contract for the ``CategoryPricingSettings`` aggregate."""

    @abstractmethod
    async def add(self, settings: CategoryPricingSettings) -> CategoryPricingSettings:
        """Persist a newly-created settings row."""

    @abstractmethod
    async def update(
        self, settings: CategoryPricingSettings
    ) -> CategoryPricingSettings:
        """Persist changes with optimistic-locking enforcement."""

    @abstractmethod
    async def delete(self, settings_id: uuid.UUID) -> None:
        """Hard-delete by id."""

    @abstractmethod
    async def get_by_category_and_context(
        self,
        *,
        category_id: uuid.UUID,
        context_id: uuid.UUID,
    ) -> CategoryPricingSettings | None:
        """Fetch settings for (category, context) or ``None`` if absent."""


class ISupplierTypeContextMappingRepository(ABC):
    """Repository contract for the ``SupplierTypeContextMapping`` aggregate."""

    @abstractmethod
    async def add(
        self, mapping: SupplierTypeContextMapping
    ) -> SupplierTypeContextMapping:
        """Persist a newly-created mapping."""

    @abstractmethod
    async def update(
        self, mapping: SupplierTypeContextMapping
    ) -> SupplierTypeContextMapping:
        """Persist changes with optimistic-locking enforcement."""

    @abstractmethod
    async def delete(self, mapping_id: uuid.UUID) -> None:
        """Hard-delete by id."""

    @abstractmethod
    async def get_by_supplier_type(
        self, supplier_type: str
    ) -> SupplierTypeContextMapping | None:
        """Fetch a mapping by ``supplier_type`` or ``None`` if absent."""

    @abstractmethod
    async def list_all(self) -> list[SupplierTypeContextMapping]:
        """Return every mapping ordered by ``supplier_type`` ascending."""


class ISupplierPricingSettingsRepository(ABC):
    """Repository contract for the ``SupplierPricingSettings`` aggregate."""

    @abstractmethod
    async def add(self, settings: SupplierPricingSettings) -> SupplierPricingSettings:
        """Persist a new settings row."""

    @abstractmethod
    async def update(
        self, settings: SupplierPricingSettings
    ) -> SupplierPricingSettings:
        """Persist changes with optimistic-locking enforcement."""

    @abstractmethod
    async def delete(self, settings_id: uuid.UUID) -> None:
        """Hard-delete by id."""

    @abstractmethod
    async def get_by_supplier_id(
        self, supplier_id: uuid.UUID
    ) -> SupplierPricingSettings | None:
        """Fetch settings for a supplier or ``None``."""


# ---------------------------------------------------------------------------
# ADR-005 — autonomous SKU pricing recompute ports
# ---------------------------------------------------------------------------
#
# These ports keep the pricing domain ignorant of catalog ORM. The
# anti-corruption adapters in ``pricing.infrastructure.adapters`` are
# whitelisted in ``tests/architecture/test_boundaries.py`` and translate
# catalog ORM rows into pure pricing DTOs.


@dataclass(frozen=True)
class SkuPricingInputs:
    """Pure DTO with everything needed to price a single SKU.

    Pricing never holds a reference to a catalog ORM row; the reader
    adapter materialises this snapshot once per recompute and the
    result writer adapter accepts a :class:`SkuPricingApplyRequest`.

    Attributes:
        sku_id: Catalog SKU UUID.
        product_id: Catalog Product UUID (denormalised for outbox routing).
        variant_id: Catalog ProductVariant UUID.
        category_id: Primary category — drives ``CategoryPricingSettings``.
        supplier_id: Supplier owning the product (``None`` if absent —
            recompute will treat this as ``no supplier overrides``).
        supplier_type: ``CROSS_BORDER`` / ``LOCAL`` — drives
            ``SupplierTypeContextMapping`` lookup. ``None`` mirrors
            ``supplier_id is None``.
        purchase_price: Wholesale cost as a ``Decimal`` (in *major* units,
            e.g. 199.50 — the adapter converts from kopecks).
        purchase_currency: ``"RUB"`` or ``"CNY"`` (ISO 4217). ``None``
            iff ``purchase_price is None``.
        version: SKU optimistic-locking version, used by the writer to
            detect concurrent updates.
    """

    sku_id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID
    category_id: uuid.UUID
    supplier_id: uuid.UUID | None
    supplier_type: str | None
    purchase_price: Decimal | None
    purchase_currency: str | None
    version: int
    pricing_status: str


@dataclass(frozen=True)
class SkuPricingApplyRequest:
    """Successful recompute payload to persist on a SKU.

    All Decimal-valued fields use *major* units (e.g. RUB rubles, not
    kopecks); the writer adapter converts to the integer storage unit
    using ISO 4217 minor-unit precision.

    ``previous_status`` is the status observed at the start of the
    recompute (under the same row lock); the writer copies it into the
    audit trail so we don't need a second SELECT (which would otherwise
    block on the ``FOR UPDATE`` taken by ``read_one(lock=True)`` and
    defeat the SKIP LOCKED contract).
    """

    sku_id: uuid.UUID
    expected_version: int
    previous_status: str | None
    selling_price: Decimal
    selling_currency: str
    formula_version_id: uuid.UUID
    inputs_hash: str
    priced_at: datetime
    correlation_id: str | None = None


@dataclass(frozen=True)
class SkuPricingFailureRequest:
    """Failed recompute payload to persist on a SKU."""

    sku_id: uuid.UUID
    expected_version: int
    previous_status: str | None
    pricing_status: str
    failure_reason: str
    correlation_id: str | None = None


class ISkuPricingInputReader(ABC):
    """Port: read SKU pricing inputs from the catalog (anti-corruption).

    The adapter implementation reads catalog ORM tables directly
    (whitelisted in the architecture fitness test) and produces a pure
    :class:`SkuPricingInputs` DTO. Pricing domain code never sees ORM.
    """

    @abstractmethod
    async def read_one(
        self,
        sku_id: uuid.UUID,
        *,
        lock: bool = False,
    ) -> SkuPricingInputs | None:
        """Return inputs for a single SKU, or ``None`` if it doesn't exist.

        When ``lock=True`` the adapter holds a ``SELECT … FOR UPDATE
        SKIP LOCKED`` on the SKU row so concurrent recompute jobs
        targeting the same SKU serialise. ``None`` is returned both
        for absent rows and for rows that were already locked by
        another worker (the duplicate trigger is a no-op).
        """

    @abstractmethod
    def iter_by_context(
        self,
        context_id: uuid.UUID,
        *,
        batch_size: int = 100,
    ) -> AsyncIterator[list[SkuPricingInputs]]:
        """Async-iterate SKUs whose resolved context matches ``context_id``.

        Implementations should yield ``list[SkuPricingInputs]`` chunks
        of size ``batch_size`` so the recompute task can fan out per-SKU
        jobs without buffering the whole catalog in memory.
        """

    @abstractmethod
    def iter_by_category(
        self,
        category_id: uuid.UUID,
        *,
        batch_size: int = 100,
    ) -> AsyncIterator[list[SkuPricingInputs]]:
        """Async-iterate SKUs whose primary_category_id matches."""

    @abstractmethod
    def iter_by_supplier(
        self,
        supplier_id: uuid.UUID,
        *,
        batch_size: int = 100,
    ) -> AsyncIterator[list[SkuPricingInputs]]:
        """Async-iterate SKUs owned by ``supplier_id``."""


class ISkuPricingResultWriter(ABC):
    """Port: persist a SKU pricing result back into the catalog.

    Implementations apply the result with optimistic locking
    (``expected_version``) and must be safe to retry: identical
    ``inputs_hash`` short-circuits as a no-op at the catalog row level.
    """

    @abstractmethod
    async def apply_success(self, request: SkuPricingApplyRequest) -> bool:
        """Apply a successful recompute. Returns False on no-op (hash match)."""

    @abstractmethod
    async def apply_failure(self, request: SkuPricingFailureRequest) -> bool:
        """Apply a failure status. Returns False on no-op."""


class ISkuPricingScopeReader(ABC):
    """Port: snapshot context-scope inputs (FX rate, supplier/category settings).

    Returns a ready-to-evaluate :class:`SkuPricingScopeSnapshot` so the
    pure-domain recompute function does not need any I/O. The adapter
    encapsulates ``SupplierTypeContextMapping`` resolution.
    """

    @abstractmethod
    async def snapshot_for_sku(
        self, inputs: SkuPricingInputs
    ) -> SkuPricingScopeSnapshot | None:
        """Resolve context, formula, settings, FX rate for one SKU.

        Returns ``None`` if no published formula is wired for the SKU's
        resolved context — the recompute service treats that as a hard
        :class:`PricingNotConfiguredError`.
        """


@dataclass(frozen=True)
class SkuPricingScopeSnapshot:
    """All context-scope inputs needed to evaluate the formula for one SKU.

    Carries enough metadata for the recompute function to compute a
    deterministic ``inputs_hash`` covering every value that can change
    the result. ``settings_versions`` is a stable mapping of
    ``(setting_kind -> version_lock)`` — bumped whenever the underlying
    settings row changes — so identical inputs map to identical hashes
    even when nothing else moves.
    """

    context_id: uuid.UUID
    target_currency: str
    rounding_mode: str
    rounding_step: Decimal | None
    formula_version_id: uuid.UUID
    formula_version_number: int
    formula_ast: dict[str, object]
    evaluation_timeout_ms: int
    variables: tuple[Variable, ...]
    global_values: dict[str, Decimal]
    global_value_set_at: dict[str, datetime]
    category_values: dict[str, Decimal]
    supplier_values: dict[str, Decimal]
    settings_versions: tuple[tuple[str, int], ...]
