"""Command handler: add a variant to an existing product."""

import uuid
from dataclasses import dataclass

from src.modules.catalog.application.constants import (
    DEFAULT_CURRENCY,
    storefront_pdp_cache_key,
)
from src.modules.catalog.domain.exceptions import ProductNotFoundError
from src.modules.catalog.domain.interfaces import IProductRepository
from src.modules.catalog.domain.value_objects import Money
from shared.interfaces.cache import ICacheService
from shared.interfaces.logger import ILogger
from shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class AddVariantCommand:
    """Input for adding a new variant to a product.

    Attributes:
        product_id: UUID of the product to add the variant to.
        name_i18n: Multilingual variant name (at least one entry required).
        description_i18n: Optional multilingual description.
        sort_order: Display ordering among sibling variants (default: 0).
        default_price: Optional default price as a domain ``Money`` value
            (CAT-001 — was previously ``default_price_amount`` /
            ``default_price_currency`` split fields).
    """

    product_id: uuid.UUID
    name_i18n: dict[str, str]
    description_i18n: dict[str, str] | None = None
    sort_order: int = 0
    default_price: Money | None = None


@dataclass(frozen=True)
class AddVariantResult:
    """Output of a successful variant addition.

    Attributes:
        variant_id: UUID of the newly created variant.
    """

    variant_id: uuid.UUID


class AddVariantHandler:
    """Add a new variant to an existing product.

    Constructs an optional Money value object for the default price,
    delegates variant creation to the Product aggregate, and persists
    the result.
    """

    def __init__(
        self,
        product_repo: IProductRepository,
        uow: IUnitOfWork,
        cache: ICacheService,
        logger: ILogger,
    ) -> None:
        self._product_repo = product_repo
        self._uow = uow
        self._cache = cache
        self._logger = logger.bind(handler="AddVariantHandler")

    async def handle(self, command: AddVariantCommand) -> AddVariantResult:
        """Execute the add-variant command.

        Args:
            command: Variant creation parameters.

        Returns:
            Result containing the new variant's UUID.

        Raises:
            ProductNotFoundError: If no product exists with the given ID.
            ValueError: If name_i18n is empty (propagated from domain).
        """
        async with self._uow:
            product = await self._product_repo.get_for_update_with_variants(
                command.product_id
            )
            if product is None:
                raise ProductNotFoundError(product_id=command.product_id)

            default_currency = (
                command.default_price.currency
                if command.default_price is not None
                else DEFAULT_CURRENCY
            )
            variant = product.add_variant(
                name_i18n=command.name_i18n,
                description_i18n=command.description_i18n,
                sort_order=command.sort_order,
                default_price=command.default_price,
                default_currency=default_currency,
            )

            await self._product_repo.update(product)
            self._uow.register_aggregate(product)
            await self._uow.commit()

        try:
            await self._cache.delete(storefront_pdp_cache_key(product.slug))
        except Exception as exc:  # pragma: no cover
            self._logger.warning("pdp_cache_invalidation_failed", error=str(exc))

        return AddVariantResult(variant_id=variant.id)
