"""
Command handler: create a new product.

Validates slug uniqueness, persists the Product aggregate in DRAFT status,
and returns the newly assigned product ID. Part of the application layer
(CQRS write side). Domain events for the Product lifecycle are deferred
to a future phase; this handler does NOT emit any domain events.
"""

import uuid
from dataclasses import dataclass, field

from src.modules.catalog.domain.entities import Product
from src.modules.catalog.domain.exceptions import ProductSlugConflictError
from src.modules.catalog.domain.interfaces import IProductRepository
from src.shared.interfaces.uow import IUnitOfWork


@dataclass(frozen=True)
class CreateProductCommand:
    """Input for creating a new product.

    Attributes:
        title_i18n: Multilingual product title. At least one language entry
            is required; validated by ``Product.create()``.
        slug: URL-safe unique identifier for the product.
        brand_id: UUID of the owning Brand aggregate.
        primary_category_id: UUID of the primary Category aggregate.
        description_i18n: Optional multilingual product description.
        supplier_id: Optional UUID of the Supplier (FK-only reference).
        country_of_origin: Optional ISO 3166-1 alpha-2 country code.
        tags: Optional list of searchable tag strings.
    """

    title_i18n: dict[str, str]
    slug: str
    brand_id: uuid.UUID
    primary_category_id: uuid.UUID
    description_i18n: dict[str, str] = field(default_factory=dict)
    supplier_id: uuid.UUID | None = None
    country_of_origin: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CreateProductResult:
    """Output of product creation.

    Attributes:
        product_id: UUID of the newly created product.
    """

    product_id: uuid.UUID


class CreateProductHandler:
    """Create a new product with slug uniqueness validation.

    The product is persisted in DRAFT status. No domain events are
    emitted (product lifecycle events are deferred to a future phase).
    """

    def __init__(
        self,
        product_repo: IProductRepository,
        uow: IUnitOfWork,
    ) -> None:
        self._product_repo = product_repo
        self._uow = uow

    async def handle(self, command: CreateProductCommand) -> CreateProductResult:
        """Execute the create-product command.

        Args:
            command: Product creation parameters.

        Returns:
            Result containing the new product's UUID.

        Raises:
            ProductSlugConflictError: If a product with the given slug
                already exists.
            ValueError: If ``title_i18n`` is empty (propagated from
                ``Product.create()``).
        """
        async with self._uow:
            if await self._product_repo.check_slug_exists(command.slug):
                raise ProductSlugConflictError(slug=command.slug)

            product = Product.create(
                slug=command.slug,
                title_i18n=command.title_i18n,
                brand_id=command.brand_id,
                primary_category_id=command.primary_category_id,
                description_i18n=command.description_i18n if command.description_i18n else None,
                supplier_id=command.supplier_id,
                country_of_origin=command.country_of_origin,
                tags=list(command.tags) if command.tags else None,
            )

            await self._product_repo.add(product)
            await self._uow.commit()

        return CreateProductResult(product_id=product.id)
