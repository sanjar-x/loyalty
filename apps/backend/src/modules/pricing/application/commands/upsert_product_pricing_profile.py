"""Upsert a ``ProductPricingProfile`` (create-or-update)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal

from src.modules.pricing.domain.entities import ProductPricingProfile
from src.modules.pricing.domain.exceptions import (
    ProductPricingProfileVersionConflictError,
)
from src.modules.pricing.domain.interfaces import IProductPricingProfileRepository
from src.modules.pricing.domain.value_objects import ProfileStatus
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpsertProductPricingProfileCommand:
    """Input for upserting a profile.

    Attributes:
        product_id: Target product (soft-ref to ``catalog.Product``).
        values: Variable-code → Decimal map.
        actor_id: Identity performing the upsert (for audit).
        context_id: Optional resolved pricing context.
        context_id_provided: ``True`` if the caller intentionally supplied
            ``context_id`` (including ``None`` to clear it); ``False`` means
            "leave existing value untouched".
        status: Desired status (defaults to ``draft``).
        expected_version_lock: Optimistic-lock version. ``None`` on create;
            required on update. ``-1`` means "upsert without version check".
    """

    product_id: uuid.UUID
    values: dict[str, Decimal]
    actor_id: uuid.UUID
    context_id: uuid.UUID | None = None
    context_id_provided: bool = False
    status: ProfileStatus = ProfileStatus.DRAFT
    expected_version_lock: int | None = None


@dataclass(frozen=True)
class UpsertProductPricingProfileResult:
    profile_id: uuid.UUID
    product_id: uuid.UUID
    version_lock: int
    status: str
    created: bool


class UpsertProductPricingProfileHandler:
    """Create-or-update a ``ProductPricingProfile``."""

    def __init__(
        self,
        repo: IProductPricingProfileRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._repo = repo
        self._uow = uow
        self._logger = logger.bind(handler="UpsertProductPricingProfileHandler")

    async def handle(
        self, command: UpsertProductPricingProfileCommand
    ) -> UpsertProductPricingProfileResult:
        async with self._uow:
            existing = await self._repo.get_by_product_id_for_update(command.product_id)

            if existing is None:
                profile = ProductPricingProfile.create(
                    product_id=command.product_id,
                    values=command.values,
                    actor_id=command.actor_id,
                    context_id=(
                        command.context_id if command.context_id_provided else None
                    ),
                    status=command.status,
                )
                await self._repo.add(profile)
                # Register the *original* aggregate (repo.add may return a
                # freshly hydrated copy with events stripped); the UoW reads
                # `_domain_events` off the object we registered.
                self._uow.register_aggregate(profile)
                await self._uow.commit()
                self._logger.info(
                    "pricing_profile_created",
                    product_id=str(profile.product_id),
                    profile_id=str(profile.id),
                )
                return UpsertProductPricingProfileResult(
                    profile_id=profile.id,
                    product_id=profile.product_id,
                    version_lock=profile.version_lock,
                    status=profile.status.value,
                    created=True,
                )

            # --- update path ---
            if (
                command.expected_version_lock is not None
                and command.expected_version_lock != -1
                and command.expected_version_lock != existing.version_lock
            ):
                raise ProductPricingProfileVersionConflictError(
                    product_id=existing.product_id,
                    expected_version=command.expected_version_lock,
                    actual_version=existing.version_lock,
                )

            existing.update_values(
                values=command.values,
                actor_id=command.actor_id,
                status=command.status,
                context_id=command.context_id,
                context_id_provided=command.context_id_provided,
            )
            updated = await self._repo.update(existing)
            self._uow.register_aggregate(existing)
            await self._uow.commit()
            self._logger.info(
                "pricing_profile_updated",
                product_id=str(updated.product_id),
                profile_id=str(updated.id),
                version_lock=updated.version_lock,
            )
            return UpsertProductPricingProfileResult(
                profile_id=updated.id,
                product_id=updated.product_id,
                version_lock=updated.version_lock,
                status=updated.status.value,
                created=False,
            )
