"""Command handler: update an existing supplier."""

import uuid
from dataclasses import dataclass, field

from src.modules.supplier.domain.exceptions import SupplierNotFoundError
from src.modules.supplier.domain.interfaces import ISupplierRepository
from src.shared.cache_keys import bump_storefront_product_generation
from src.shared.interfaces.cache import ICacheService
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork

_UNSET = object()


@dataclass(frozen=True)
class UpdateSupplierCommand:
    supplier_id: uuid.UUID
    name: str | None = None
    country_code: str | None = None
    # Use _UNSET sentinel to distinguish "not provided" from "set to None" (clear).
    subdivision_code: str | None | object = field(default=_UNSET)


class UpdateSupplierHandler:
    def __init__(
        self,
        supplier_repo: ISupplierRepository,
        uow: IUnitOfWork,
        cache: ICacheService,
        logger: ILogger,
    ) -> None:
        self._supplier_repo = supplier_repo
        self._uow = uow
        self._cache = cache
        self._logger = logger.bind(handler="UpdateSupplierHandler")

    async def handle(self, command: UpdateSupplierCommand) -> None:
        mutated = False
        async with self._uow:
            supplier = await self._supplier_repo.get(command.supplier_id)
            if supplier is None:
                raise SupplierNotFoundError(command.supplier_id)

            kwargs: dict = {}
            if command.name is not None:
                kwargs["name"] = command.name
            if command.country_code is not None:
                kwargs["country_code"] = command.country_code
            if command.subdivision_code is not _UNSET:
                kwargs["subdivision_code"] = command.subdivision_code

            if kwargs:
                supplier.update(**kwargs)
                await self._supplier_repo.update(supplier)
                self._uow.register_aggregate(supplier)
                mutated = True

            await self._uow.commit()

        # ``supplier.type`` is denormalised into the storefront PLP/PDP/
        # search caches (cross_border vs local policy on cards). Bump
        # the generation counter post-commit so downstream queries see
        # fresh data within seconds, not whenever the local TTL expires.
        if mutated:
            try:
                await bump_storefront_product_generation(self._cache)
            except Exception as exc:  # pragma: no cover
                self._logger.warning(
                    "storefront_cache_invalidation_failed",
                    error=str(exc),
                    supplier_id=str(command.supplier_id),
                )
