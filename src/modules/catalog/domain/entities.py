"""
Catalog domain entities (Brand, Category, AttributeGroup, and Attribute aggregates).

Contains the core business logic for brand lifecycle management
(including logo FSM transitions), hierarchical category trees,
attribute group management, and attribute definitions.
Part of the domain layer -- zero infrastructure imports.

Typical usage:
    brand = Brand.create(name="Nike", slug="nike")
    group = AttributeGroup.create(code="general", name_i18n={"en": "General"})
    attr = Attribute.create(code="color", slug="color", ...)
"""

import uuid
from typing import Any

from attr import dataclass

from src.modules.catalog.domain.value_objects import (
    DEFAULT_SEARCH_WEIGHT,
    MAX_SEARCH_WEIGHT,
    MIN_SEARCH_WEIGHT,
    AttributeDataType,
    AttributeLevel,
    AttributeUIType,
    MediaProcessingStatus,
    validate_validation_rules,
)
from src.shared.interfaces.entities import AggregateRoot

GENERAL_GROUP_CODE = "general"
"""Code of the default attribute group that always exists and cannot be deleted."""


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


@dataclass
class AttributeGroup(AggregateRoot):
    """Attribute group aggregate root for organizing attributes into logical sections.

    Groups provide visual and semantic grouping of attributes in the admin UI
    and on the product card (e.g. "Physical characteristics", "Technical",
    "Marketing"). The "general" group always exists and cannot be deleted.

    Attributes:
        id: Unique group identifier.
        code: Machine-readable code, globally unique and immutable after creation.
        name_i18n: Multilingual display name (e.g. ``{"en": "General", "ru": "Общие"}``).
        sort_order: Display ordering among groups (lower = first).
    """

    id: uuid.UUID
    code: str
    name_i18n: dict[str, str]
    sort_order: int

    @classmethod
    def create(
        cls,
        code: str,
        name_i18n: dict[str, str],
        sort_order: int = 0,
        group_id: uuid.UUID | None = None,
    ) -> AttributeGroup:
        """Factory method to construct a new AttributeGroup aggregate.

        Args:
            code: Machine-readable unique code (e.g. "general", "physical").
            name_i18n: Multilingual display name. Must have at least one entry.
            sort_order: Display ordering among groups.
            group_id: Optional pre-generated UUID; generates uuid7/uuid4 if omitted.

        Returns:
            A new AttributeGroup instance.

        Raises:
            ValueError: If name_i18n is empty (no language entries).
        """
        if not name_i18n:
            raise ValueError("name_i18n must contain at least one language entry")

        return cls(
            id=group_id or (uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4()),
            code=code,
            name_i18n=name_i18n,
            sort_order=sort_order,
        )

    def update(
        self,
        name_i18n: dict[str, str] | None = None,
        sort_order: int | None = None,
    ) -> None:
        """Update group details. Code is immutable and cannot be changed.

        Args:
            name_i18n: New multilingual name, or None to keep current.
            sort_order: New sort position, or None to keep current.

        Raises:
            ValueError: If name_i18n is provided but empty.
        """
        if name_i18n is not None:
            if not name_i18n:
                raise ValueError("name_i18n must contain at least one language entry")
            self.name_i18n = name_i18n

        if sort_order is not None:
            self.sort_order = sort_order

    @property
    def is_general(self) -> bool:
        """Return True if this is the protected default group."""
        return self.code == GENERAL_GROUP_CODE


@dataclass
class Attribute(AggregateRoot):
    """Attribute aggregate root -- a product characteristic definition.

    An attribute describes a single product property (e.g. "Color",
    "Screen Size", "Material"). It carries metadata about how it should
    be stored (data type), rendered (UI type), searched, filtered, and
    compared. Code and slug are immutable after creation.

    Attributes:
        id: Unique attribute identifier.
        code: Machine-readable code, globally unique and immutable.
        slug: URL-safe identifier, globally unique and immutable.
        name_i18n: Multilingual display name.
        description_i18n: Multilingual description / tooltip text.
        data_type: Primitive type (string, integer, float, boolean).
        ui_type: Widget hint for storefront rendering.
        is_dictionary: True if the attribute has predefined values.
        group_id: FK to the attribute group this attribute belongs to.
        level: Product-level or variant-level attribute.
        is_filterable: Available as filter on storefront.
        is_searchable: Participates in full-text search.
        search_weight: Priority for search ranking (1-10, default 5).
        is_comparable: Shown in product comparison table.
        is_visible_on_card: Shown on product detail page.
        is_visible_in_catalog: Shown in catalog listing preview.
        validation_rules: Type-specific validation constraints (JSONB).
    """

    id: uuid.UUID
    code: str
    slug: str
    name_i18n: dict[str, str]
    description_i18n: dict[str, str]
    data_type: AttributeDataType
    ui_type: AttributeUIType
    is_dictionary: bool
    group_id: uuid.UUID
    level: AttributeLevel
    is_filterable: bool = False
    is_searchable: bool = False
    search_weight: int = DEFAULT_SEARCH_WEIGHT
    is_comparable: bool = False
    is_visible_on_card: bool = False
    is_visible_in_catalog: bool = False
    validation_rules: dict[str, Any] | None = None

    @classmethod
    def create(
        cls,
        *,
        code: str,
        slug: str,
        name_i18n: dict[str, str],
        data_type: AttributeDataType,
        ui_type: AttributeUIType,
        is_dictionary: bool,
        group_id: uuid.UUID,
        description_i18n: dict[str, str] | None = None,
        level: AttributeLevel = AttributeLevel.PRODUCT,
        is_filterable: bool = False,
        is_searchable: bool = False,
        search_weight: int = DEFAULT_SEARCH_WEIGHT,
        is_comparable: bool = False,
        is_visible_on_card: bool = False,
        is_visible_in_catalog: bool = False,
        validation_rules: dict[str, Any] | None = None,
        attribute_id: uuid.UUID | None = None,
    ) -> Attribute:
        """Factory method to construct a new Attribute aggregate.

        Args:
            code: Machine-readable unique code.
            slug: URL-safe unique identifier.
            name_i18n: Multilingual display name. At least one language required.
            data_type: Primitive storage type.
            ui_type: Widget hint for storefront rendering.
            is_dictionary: Whether attribute has predefined option values.
            group_id: UUID of the attribute group.
            description_i18n: Optional multilingual description.
            level: Product or variant level (default: PRODUCT).
            is_filterable: Show as filter on storefront (default: False).
            is_searchable: Include in full-text search (default: False).
            search_weight: Search ranking priority 1-10 (default: 5).
            is_comparable: Include in comparison table (default: False).
            is_visible_on_card: Show on product detail page (default: False).
            is_visible_in_catalog: Show in listing preview (default: False).
            validation_rules: Type-specific validation constraints.
            attribute_id: Optional pre-generated UUID.

        Returns:
            A new Attribute instance.

        Raises:
            ValueError: If name_i18n is empty, search_weight out of range,
                or validation_rules do not match data_type.
        """
        if not name_i18n:
            raise ValueError("name_i18n must contain at least one language entry")

        if not (MIN_SEARCH_WEIGHT <= search_weight <= MAX_SEARCH_WEIGHT):
            raise ValueError(
                f"search_weight must be between {MIN_SEARCH_WEIGHT} and "
                f"{MAX_SEARCH_WEIGHT}, got {search_weight}"
            )

        validate_validation_rules(data_type, validation_rules)

        return cls(
            id=attribute_id or (uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4()),
            code=code,
            slug=slug,
            name_i18n=name_i18n,
            description_i18n=description_i18n or {},
            data_type=data_type,
            ui_type=ui_type,
            is_dictionary=is_dictionary,
            group_id=group_id,
            level=level,
            is_filterable=is_filterable,
            is_searchable=is_searchable,
            search_weight=search_weight,
            is_comparable=is_comparable,
            is_visible_on_card=is_visible_on_card,
            is_visible_in_catalog=is_visible_in_catalog,
            validation_rules=validation_rules,
        )

    def update(
        self,
        *,
        name_i18n: dict[str, str] | None = None,
        description_i18n: dict[str, str] | None = None,
        ui_type: AttributeUIType | None = None,
        group_id: uuid.UUID | None = None,
        level: AttributeLevel | None = None,
        is_filterable: bool | None = None,
        is_searchable: bool | None = None,
        search_weight: int | None = None,
        is_comparable: bool | None = None,
        is_visible_on_card: bool | None = None,
        is_visible_in_catalog: bool | None = None,
        validation_rules: dict[str, Any] | None = ...,  # type: ignore[assignment]
    ) -> None:
        """Update mutable attribute fields. Code, slug, and data_type are immutable.

        Args:
            name_i18n: New multilingual name, or None to keep current.
            description_i18n: New multilingual description, or None to keep current.
            ui_type: New UI widget type, or None to keep current.
            group_id: New group UUID, or None to keep current.
            level: New attribute level, or None to keep current.
            is_filterable: New filter flag, or None to keep current.
            is_searchable: New search flag, or None to keep current.
            search_weight: New search weight (1-10), or None to keep current.
            is_comparable: New comparison flag, or None to keep current.
            is_visible_on_card: New card visibility flag, or None to keep current.
            is_visible_in_catalog: New catalog visibility flag, or None to keep current.
            validation_rules: New validation rules dict, None to clear, or
                ``...`` (sentinel) to keep current.

        Raises:
            ValueError: If name_i18n empty, search_weight out of range,
                or validation_rules incompatible with data_type.
        """
        if name_i18n is not None:
            if not name_i18n:
                raise ValueError("name_i18n must contain at least one language entry")
            self.name_i18n = name_i18n

        if description_i18n is not None:
            self.description_i18n = description_i18n

        if ui_type is not None:
            self.ui_type = ui_type

        if group_id is not None:
            self.group_id = group_id

        if level is not None:
            self.level = level

        if is_filterable is not None:
            self.is_filterable = is_filterable

        if is_searchable is not None:
            self.is_searchable = is_searchable

        if search_weight is not None:
            if not (MIN_SEARCH_WEIGHT <= search_weight <= MAX_SEARCH_WEIGHT):
                raise ValueError(
                    f"search_weight must be between {MIN_SEARCH_WEIGHT} and "
                    f"{MAX_SEARCH_WEIGHT}, got {search_weight}"
                )
            self.search_weight = search_weight

        if is_comparable is not None:
            self.is_comparable = is_comparable

        if is_visible_on_card is not None:
            self.is_visible_on_card = is_visible_on_card

        if is_visible_in_catalog is not None:
            self.is_visible_in_catalog = is_visible_in_catalog

        # Sentinel ``...`` means "do not change"; None means "clear rules"
        if validation_rules is not ...:  # type: ignore[comparison-overlap]
            if validation_rules is not None:
                validate_validation_rules(self.data_type, validation_rules)
            self.validation_rules = validation_rules  # type: ignore[assignment]
