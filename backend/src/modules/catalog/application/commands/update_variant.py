"""Command handler: update an existing product variant.

Fetches the product aggregate with its variants, locates the target
variant, builds update kwargs from provided fields, and delegates
mutation to ``ProductVariant.update()``.

Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass, field

from src.modules.catalog.domain.exceptions import (
    ProductNotFoundError,
    VariantNotFoundError,
)
from src.modules.catalog.domain.interfaces import IProductRepository
from src.modules.catalog.domain.value_objects import Money
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class UpdateVariantCommand:
    """Input for updating an existing product variant.

    All fields except ``product_id`` and ``variant_id`` are optional;
    omitting a field means "keep the current value". Pass ``None``
    explicitly for ``description_i18n`` or ``default_price_amount``
    (with the field name in ``_provided_fields``) to clear the value.

    Attributes:
        product_id: UUID of the product that owns the variant.
        variant_id: UUID of the variant to update.
        name_i18n: New multilingual name, or None to keep current.
        description_i18n: New description, None to clear, or absent to keep.
        sort_order: New sort order, or None to keep current.
        default_price_amount: New default price amount, None to clear, or absent to keep.
        default_price_currency: New currency code, or None to keep current.
        _provided_fields: Set of field names explicitly provided by the caller.
    """

    product_id: uuid.UUID
    variant_id: uuid.UUID
    name_i18n: dict[str, str] | None = None
    description_i18n: dict[str, str] | None = None
    sort_order: int | None = None
    default_price_amount: int | None = None
    default_price_currency: str | None = None
    _provided_fields: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class UpdateVariantResult:
    """Output of a successful variant update.

    Attributes:
        id: UUID of the updated variant.
    """

    id: uuid.UUID


class UpdateVariantHandler:
    """Apply partial updates to an existing product variant.

    Orchestrates: fetch product with variants -> find variant ->
    build update kwargs -> delegate to ProductVariant.update() ->
    persist -> commit.
    """

    def __init__(
        self,
        product_repo: IProductRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._product_repo = product_repo
        self._uow = uow
        self._logger = logger.bind(handler="UpdateVariantHandler")

    async def handle(self, command: UpdateVariantCommand) -> UpdateVariantResult:
        """Execute the update-variant command.

        Args:
            command: Variant update parameters.

        Returns:
            Result containing the updated variant ID.

        Raises:
            ProductNotFoundError: If no product exists with the given ID.
            VariantNotFoundError: If no active variant with the given ID
                exists within the product.
            ValueError: If name_i18n is empty (propagated from domain).
        """
        async with self._uow:
            product = await self._product_repo.get_for_update_with_variants(command.product_id)
            if product is None:
                raise ProductNotFoundError(product_id=command.product_id)

            variant = product.find_variant(command.variant_id)
            if variant is None:
                raise VariantNotFoundError(
                    variant_id=command.variant_id, product_id=command.product_id
                )

            update_kwargs: dict[str, object] = {}

            if "name_i18n" in command._provided_fields:
                update_kwargs["name_i18n"] = command.name_i18n

            if "description_i18n" in command._provided_fields:
                update_kwargs["description_i18n"] = command.description_i18n

            if "sort_order" in command._provided_fields:
                update_kwargs["sort_order"] = command.sort_order

            if "default_price_currency" in command._provided_fields:
                currency = command.default_price_currency
                if currency is not None and not (
                    len(currency) == 3 and currency.isascii() and currency.isupper()
                ):
                    raise ValueError(
                        "default_price_currency must be exactly 3 uppercase ASCII letters"
                    )

            if "default_price_amount" in command._provided_fields:
                if command.default_price_amount is not None:
                    currency = (
                        command.default_price_currency or variant.default_currency
                    )
                    update_kwargs["default_price"] = Money(
                        amount=command.default_price_amount, currency=currency
                    )
                else:
                    update_kwargs["default_price"] = None

            if (
                "default_price_currency" in command._provided_fields
                and command.default_price_currency is not None
            ):
                update_kwargs["default_currency"] = command.default_price_currency

            if update_kwargs:
                variant.update(**update_kwargs)

            await self._product_repo.update(product)
            self._uow.register_aggregate(product)
            await self._uow.commit()

        self._logger.info(
            "Variant updated",
            variant_id=str(variant.id),
            product_id=str(command.product_id),
        )
        return UpdateVariantResult(id=variant.id)
