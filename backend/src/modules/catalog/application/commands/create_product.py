"""
Command handler: create a new product.

Validates FK references (brand, category) and slug uniqueness, persists the
Product aggregate in DRAFT status, registers it with the Unit of Work so that
the ``ProductCreatedEvent`` reaches the Outbox, and returns the newly assigned
product ID. Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass, field

from src.modules.catalog.domain.entities import Product
from src.modules.catalog.domain.exceptions import (
    BrandNotFoundError,
    CategoryNotFoundError,
    ProductSlugConflictError,
)
from src.modules.catalog.domain.interfaces import (
    IBrandRepository,
    ICategoryRepository,
    IProductRepository,
)
from src.modules.supplier.domain.exceptions import SourceUrlRequiredError
from src.modules.supplier.domain.interfaces import ISupplierQueryService
from src.modules.supplier.domain.value_objects import SupplierType
from src.shared.interfaces.logger import ILogger
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
    source_url: str | None = None
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
    """Create a new product with FK and slug uniqueness validation.

    The product is persisted in DRAFT status. A ``ProductCreatedEvent`` is
    emitted via the Unit of Work aggregate registration.
    """

    def __init__(
        self,
        product_repo: IProductRepository,
        brand_repo: IBrandRepository,
        category_repo: ICategoryRepository,
        supplier_query_service: ISupplierQueryService,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._product_repo = product_repo
        self._brand_repo = brand_repo
        self._category_repo = category_repo
        self._supplier_query_service = supplier_query_service
        self._uow = uow
        self._logger = logger.bind(handler="CreateProductHandler")

    async def handle(self, command: CreateProductCommand) -> CreateProductResult:
        """Execute the create-product command.

        Args:
            command: Product creation parameters.

        Returns:
            Result containing the new product's UUID.

        Raises:
            BrandNotFoundError: If the referenced brand does not exist.
            CategoryNotFoundError: If the referenced category does not exist.
            ProductSlugConflictError: If a product with the given slug
                already exists.
            ValueError: If ``title_i18n`` is empty (propagated from
                ``Product.create()``).
        """
        async with self._uow:
            brand = await self._brand_repo.get(command.brand_id)
            if brand is None:
                raise BrandNotFoundError(brand_id=command.brand_id)

            category = await self._category_repo.get(command.primary_category_id)
            if category is None:
                raise CategoryNotFoundError(category_id=command.primary_category_id)

            # Validate supplier exists and is active
            if command.supplier_id is not None:
                supplier_info = await self._supplier_query_service.assert_supplier_active(command.supplier_id)
                if supplier_info.type == SupplierType.CROSS_BORDER and not command.source_url:
                    raise SourceUrlRequiredError()

            if await self._product_repo.check_slug_exists(command.slug):
                raise ProductSlugConflictError(slug=command.slug)

            product = Product.create(
                slug=command.slug,
                title_i18n=command.title_i18n,
                brand_id=command.brand_id,
                primary_category_id=command.primary_category_id,
                description_i18n=command.description_i18n if command.description_i18n else None,
                supplier_id=command.supplier_id,
                source_url=command.source_url,
                country_of_origin=command.country_of_origin,
                tags=list(command.tags) if command.tags else None,
            )

            await self._product_repo.add(product)
            self._uow.register_aggregate(product)
            await self._uow.commit()

        return CreateProductResult(product_id=product.id)
