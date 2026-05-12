"""
Command handler: bulk-create brands in a single transaction.

Validates name/slug uniqueness both within the batch and against
existing brands, persists new Brand aggregates, and emits
``BrandCreatedEvent`` for each. Supports ``skip_existing`` mode
for idempotent seed scenarios.

Part of the application layer (CQRS write side).
"""

import uuid
from dataclasses import dataclass, field

from src.modules.catalog.domain.entities import Brand
from src.modules.catalog.domain.events import BrandCreatedEvent
from src.modules.catalog.domain.exceptions import (
    BrandNameConflictError,
    BrandSlugConflictError,
)
from src.modules.catalog.domain.interfaces import IBrandRepository
from src.shared.exceptions import ValidationError
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork

MAX_BULK_BRANDS = 100


@dataclass(frozen=True)
class BulkBrandItem:
    """A single brand within a bulk-create request.

    Attributes:
        name: Display name of the brand.
        slug: URL-safe unique identifier.
        logo_url: Optional public URL for the brand logo.
    """

    name: str
    slug: str
    logo_url: str | None = None


@dataclass(frozen=True)
class BulkCreateBrandsCommand:
    """Input for bulk-creating brands.

    Attributes:
        items: List of brand items to create (max 100).
        skip_existing: When True, silently skip brands whose slug or name
            already exists instead of raising a conflict error.
    """

    items: list[BulkBrandItem]
    skip_existing: bool = False


@dataclass(frozen=True)
class BulkCreateBrandsResult:
    """Output of bulk brand creation.

    Attributes:
        created_count: Number of brands successfully created.
        skipped_count: Number of brands skipped (slug/name conflict).
        ids: UUIDs of the newly created brands (excludes skipped).
        skipped_slugs: Slugs of brands that were skipped.
    """

    created_count: int
    skipped_count: int
    ids: list[uuid.UUID]
    skipped_slugs: list[str] = field(default_factory=list)


class BulkCreateBrandsHandler:
    """Bulk-create brands with batch-level uniqueness validation.

    When ``skip_existing=False`` (default, strict mode): any conflict
    aborts the entire transaction.

    When ``skip_existing=True`` (seed mode): existing brands are
    silently skipped, the rest are created in a single transaction.
    """

    def __init__(
        self,
        brand_repo: IBrandRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._brand_repo = brand_repo
        self._uow = uow
        self._logger = logger.bind(handler="BulkCreateBrandsHandler")

    async def handle(self, command: BulkCreateBrandsCommand) -> BulkCreateBrandsResult:
        """Execute the bulk-create-brands command.

        Args:
            command: Bulk brand creation parameters.

        Returns:
            Result containing created/skipped counts and brand IDs.

        Raises:
            ValidationError: If batch exceeds limit or contains duplicates.
            BrandSlugConflictError: If a slug is taken (strict mode only).
            BrandNameConflictError: If a name is taken (strict mode only).
        """
        if len(command.items) > MAX_BULK_BRANDS:
            raise ValidationError(
                message=f"Bulk operation supports at most {MAX_BULK_BRANDS} items.",
                error_code="BULK_LIMIT_EXCEEDED",
                details={"max": MAX_BULK_BRANDS, "received": len(command.items)},
            )

        # Validate no duplicates within batch (always — even in skip mode)
        batch_slugs = [item.slug for item in command.items]
        if len(batch_slugs) != len(set(batch_slugs)):
            seen: set[str] = set()
            dupes = [s for s in batch_slugs if s in seen or seen.add(s)]
            raise ValidationError(
                message="Duplicate slugs within the batch.",
                error_code="BULK_DUPLICATE_SLUGS",
                details={"duplicate_slugs": list(set(dupes))},
            )

        batch_names = [item.name for item in command.items]
        if len(batch_names) != len(set(batch_names)):
            seen_n: set[str] = set()
            dupes_n = [n for n in batch_names if n in seen_n or seen_n.add(n)]
            raise ValidationError(
                message="Duplicate names within the batch.",
                error_code="BULK_DUPLICATE_NAMES",
                details={"duplicate_names": list(set(dupes_n))},
            )

        async with self._uow:
            created_ids: list[uuid.UUID] = []
            skipped_slugs: list[str] = []

            for item in command.items:
                slug_taken = await self._brand_repo.check_slug_exists(item.slug)
                name_taken = await self._brand_repo.check_name_exists(item.name)

                if slug_taken or name_taken:
                    if command.skip_existing:
                        skipped_slugs.append(item.slug)
                        continue
                    if slug_taken:
                        raise BrandSlugConflictError(slug=item.slug)
                    raise BrandNameConflictError(name=item.name)

                brand = Brand.create(
                    name=item.name,
                    slug=item.slug,
                    logo_url=item.logo_url,
                )
                brand = await self._brand_repo.add(brand)
                brand.add_domain_event(
                    BrandCreatedEvent(
                        brand_id=brand.id,
                        slug=brand.slug,
                        aggregate_id=str(brand.id),
                    )
                )
                self._uow.register_aggregate(brand)
                created_ids.append(brand.id)

            await self._uow.commit()

        self._logger.info(
            "Brands bulk-created",
            created=len(created_ids),
            skipped=len(skipped_slugs),
        )
        return BulkCreateBrandsResult(
            created_count=len(created_ids),
            skipped_count=len(skipped_slugs),
            ids=created_ids,
            skipped_slugs=skipped_slugs,
        )
