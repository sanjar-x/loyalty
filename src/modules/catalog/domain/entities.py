"""
Catalog domain entities (Brand and Category aggregates).

Contains the core business logic for brand lifecycle management
(including logo FSM transitions) and hierarchical category trees.
Part of the domain layer — zero infrastructure imports.

Typical usage:
    brand = Brand.create(name="Nike", slug="nike")
    brand.init_logo_upload(object_key="...", content_type="image/png")
"""

import uuid

from attr import dataclass

from src.modules.catalog.domain.value_objects import MediaProcessingStatus
from src.shared.interfaces.entities import AggregateRoot


@dataclass
class Brand(AggregateRoot):
    """Brand aggregate root with logo processing FSM.

    The logo lifecycle follows a strict state machine:
    ``None`` -> ``PENDING_UPLOAD`` -> ``PROCESSING`` -> ``COMPLETED`` | ``FAILED``.
    Each transition emits a domain event for the Transactional Outbox.

    Attributes:
        id: Unique brand identifier.
        name: Display name of the brand.
        slug: URL-safe identifier, unique across all brands.
        logo_status: Current state of the logo processing FSM, or None.
        logo_file_id: Reference to the StorageObject record, if any.
        logo_url: Public URL of the processed logo, set on completion.
    """

    id: uuid.UUID
    name: str
    slug: str
    logo_status: MediaProcessingStatus | None = None
    logo_file_id: uuid.UUID | None = None
    logo_url: str | None = None

    @classmethod
    def create(
        cls,
        name: str,
        slug: str,
        brand_id: uuid.UUID | None = None,
        logo_file_id: uuid.UUID | None = None,
        logo_status: MediaProcessingStatus | None = None,
    ) -> Brand:
        """Factory method to construct a new Brand aggregate.

        Args:
            name: Display name.
            slug: URL-safe identifier.
            brand_id: Optional pre-generated UUID; generates uuid4 if omitted.
            logo_file_id: Optional storage object reference.
            logo_status: Initial logo FSM state.

        Returns:
            A new Brand instance.
        """
        return cls(
            id=brand_id or uuid.uuid4(),
            name=name,
            slug=slug,
            logo_file_id=logo_file_id,
            logo_status=logo_status,
        )

    def update(self, name: str | None = None, slug: str | None = None) -> None:
        """Update brand details. Logo fields are managed separately via FSM methods.

        Args:
            name: New display name, or None to keep current.
            slug: New URL-safe slug, or None to keep current.
        """
        if name is not None:
            self.name = name
        if slug is not None:
            self.slug = slug

    def init_logo_upload(self, object_key: str, content_type: str) -> None:
        """Transition logo FSM to PENDING_UPLOAD and emit BrandCreatedEvent.

        Args:
            object_key: S3 key where the client will upload the raw logo.
            content_type: Expected MIME type of the upload.
        """
        self.logo_status = MediaProcessingStatus.PENDING_UPLOAD

        from src.modules.catalog.domain.events import BrandCreatedEvent

        self.add_domain_event(
            BrandCreatedEvent(
                brand_id=self.id,
                object_key=object_key,
                content_type=content_type,
                aggregate_id=str(self.id),
            )
        )

    def confirm_logo_upload(self) -> None:
        """Transition logo FSM from PENDING_UPLOAD to PROCESSING.

        Emits a ``BrandLogoConfirmedEvent`` to trigger background processing.

        Raises:
            InvalidLogoStateException: If current state is not PENDING_UPLOAD.
        """
        if self.logo_status != MediaProcessingStatus.PENDING_UPLOAD:
            from src.modules.catalog.domain.exceptions import InvalidLogoStateException

            raise InvalidLogoStateException(
                brand_id=self.id,
                current_status=str(self.logo_status) if self.logo_status else "None",
                expected_status=MediaProcessingStatus.PENDING_UPLOAD,
            )
        self.logo_status = MediaProcessingStatus.PROCESSING

        from src.modules.catalog.domain.events import BrandLogoConfirmedEvent

        self.add_domain_event(
            BrandLogoConfirmedEvent(
                brand_id=self.id,
                aggregate_id=str(self.id),
            )
        )

    def complete_logo_processing(
        self, url: str, object_key: str, content_type: str, size_bytes: int
    ) -> None:
        """Transition logo FSM from PROCESSING to COMPLETED.

        Sets the public logo URL and emits ``BrandLogoProcessedEvent``.

        Args:
            url: Public URL of the processed logo.
            object_key: Final S3 key of the processed file.
            content_type: MIME type of the processed file.
            size_bytes: Size of the processed file in bytes.

        Raises:
            InvalidLogoStateException: If current state is not PROCESSING.
        """
        if self.logo_status != MediaProcessingStatus.PROCESSING:
            from src.modules.catalog.domain.exceptions import InvalidLogoStateException

            raise InvalidLogoStateException(
                brand_id=self.id,
                current_status=str(self.logo_status) if self.logo_status else "None",
                expected_status=MediaProcessingStatus.PROCESSING,
            )
        self.logo_url = url
        self.logo_status = MediaProcessingStatus.COMPLETED

        from src.modules.catalog.domain.events import BrandLogoProcessedEvent

        self.add_domain_event(
            BrandLogoProcessedEvent(
                brand_id=self.id,
                object_key=object_key,
                content_type=content_type,
                size_bytes=size_bytes,
                aggregate_id=str(self.id),
            )
        )

    def fail_logo_processing(self) -> None:
        """Transition logo FSM from PROCESSING to FAILED.

        Raises:
            InvalidLogoStateException: If current state is not PROCESSING.
        """
        if self.logo_status != MediaProcessingStatus.PROCESSING:
            from src.modules.catalog.domain.exceptions import InvalidLogoStateException

            raise InvalidLogoStateException(
                brand_id=self.id,
                current_status=str(self.logo_status) if self.logo_status else "None",
                expected_status=MediaProcessingStatus.PROCESSING,
            )
        self.logo_status = MediaProcessingStatus.FAILED


MAX_CATEGORY_DEPTH = 3
"""Maximum allowed nesting depth for the category tree."""


@dataclass
class Category(AggregateRoot):
    """Category aggregate root supporting hierarchical trees.

    Categories form a tree with a maximum depth of ``MAX_CATEGORY_DEPTH``.
    Each category maintains a materialized ``full_slug`` path for efficient
    URL resolution and descendant queries.

    Attributes:
        id: Unique category identifier (uuid7 when available, uuid4 fallback).
        parent_id: UUID of the parent category, or None for root categories.
        name: Display name.
        slug: URL-safe identifier, unique within the same parent level.
        full_slug: Materialized path (e.g. ``"electronics/phones/android"``).
        level: Depth in the tree (0 = root).
        sort_order: Display ordering within the same parent.
    """

    id: uuid.UUID
    parent_id: uuid.UUID | None
    name: str
    slug: str
    full_slug: str
    level: int
    sort_order: int

    @classmethod
    def create_root(
        cls,
        name: str,
        slug: str,
        sort_order: int = 0,
    ) -> Category:
        """Create a top-level (root) category.

        Args:
            name: Display name.
            slug: URL-safe identifier.
            sort_order: Display ordering among root categories.

        Returns:
            A new root Category with level=0.
        """
        return cls(
            id=uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4(),
            parent_id=None,
            name=name,
            slug=slug,
            full_slug=slug,
            level=0,
            sort_order=sort_order,
        )

    @classmethod
    def create_child(
        cls,
        name: str,
        slug: str,
        parent: Category,
        sort_order: int = 0,
    ) -> Category:
        """Create a child category under the given parent.

        Args:
            name: Display name.
            slug: URL-safe identifier (unique within parent's children).
            parent: Parent category aggregate.
            sort_order: Display ordering among siblings.

        Returns:
            A new child Category with level = parent.level + 1.

        Raises:
            CategoryMaxDepthError: If the parent is already at max depth.
        """
        if parent.level >= MAX_CATEGORY_DEPTH:
            from src.modules.catalog.domain.exceptions import CategoryMaxDepthError

            raise CategoryMaxDepthError(max_depth=MAX_CATEGORY_DEPTH, current_level=parent.level)

        return cls(
            id=uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4(),
            parent_id=parent.id,
            name=name,
            slug=slug,
            full_slug=f"{parent.full_slug}/{slug}",
            level=parent.level + 1,
            sort_order=sort_order,
        )

    def update(
        self,
        name: str | None = None,
        slug: str | None = None,
        sort_order: int | None = None,
    ) -> str | None:
        """Update category details and recompute full_slug if slug changed.

        Args:
            name: New display name, or None to keep current.
            slug: New URL-safe slug, or None to keep current.
            sort_order: New sort position, or None to keep current.

        Returns:
            The old ``full_slug`` if slug was changed (caller must cascade
            to descendants), or None if slug was unchanged.
        """
        old_full_slug: str | None = None

        if name is not None:
            self.name = name

        if sort_order is not None:
            self.sort_order = sort_order

        if slug is not None and slug != self.slug:
            old_full_slug = self.full_slug
            self.slug = slug
            # Recompute own full_slug by replacing the last path segment
            if self.parent_id is None:
                self.full_slug = slug
            else:
                parent_prefix = self.full_slug.rsplit("/", 1)[0]
                self.full_slug = f"{parent_prefix}/{slug}"

        return old_full_slug
