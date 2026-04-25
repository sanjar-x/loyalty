"""Pricing domain interfaces (ports)."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

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
    ) -> list[Variable]:
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
    ) -> list[PricingContext]:
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
    async def add(
        self, settings: SupplierPricingSettings
    ) -> SupplierPricingSettings:
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
