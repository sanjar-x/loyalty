"""
Catalog domain entities (Brand, Category, AttributeGroup, Attribute,
CategoryAttributeBinding, ProductVariant, SKU, and Product aggregates).

Contains the core business logic for brand lifecycle management
(including logo FSM transitions), hierarchical category trees,
attribute group management, attribute definitions, and the Product
aggregate root with its SKU child entities.
Part of the domain layer -- zero infrastructure imports.

Typical usage:
    brand = Brand.create(name="Nike", slug="nike")
    group = AttributeGroup.create(code="general", name_i18n={"en": "General"})
    attr = Attribute.create(code="color", slug="color", ...)
    product = Product.create(slug="nike-air-max", title_i18n={"en": "Air Max"},
                             brand_id=brand.id, primary_category_id=cat.id)
"""

import hashlib
import re
import uuid
from datetime import UTC, datetime
from typing import Any, ClassVar

from attr import dataclass, field

from src.modules.catalog.domain.events import (
    BrandLogoConfirmedEvent,
    BrandLogoProcessedEvent,
    BrandLogoUploadInitiatedEvent,
    ProductCreatedEvent,
    ProductMediaConfirmedEvent,
    ProductMediaProcessedEvent,
    ProductStatusChangedEvent,
    ProductUpdatedEvent,
    SKUAddedEvent,
    SKURemovedEvent,
    VariantAddedEvent,
    VariantRemovedEvent,
)
from src.modules.catalog.domain.exceptions import (
    BrandHasProductsError,
    CannotDeletePublishedProductError,
    CategoryHasChildrenError,
    CategoryHasProductsError,
    CategoryMaxDepthError,
    DuplicateVariantCombinationError,
    InvalidLogoStateError,
    InvalidMediaStateError,
    InvalidStatusTransitionError,
    LastVariantRemovalError,
    ProductNotReadyError,
    SKUNotFoundError,
    VariantNotFoundError,
)
from src.modules.catalog.domain.value_objects import (
    DEFAULT_CURRENCY,
    DEFAULT_SEARCH_WEIGHT,
    MAX_SEARCH_WEIGHT,
    MIN_SEARCH_WEIGHT,
    AttributeDataType,
    AttributeLevel,
    AttributeUIType,
    BehaviorFlags,
    MediaProcessingStatus,
    Money,
    ProductStatus,
    RequirementLevel,
    validate_validation_rules,
)
from src.shared.interfaces.entities import AggregateRoot, DomainEvent

GENERAL_GROUP_CODE = "general"
"""Code of the default attribute group that always exists and cannot be deleted."""

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _validate_slug(slug: str, entity_name: str) -> None:
    """Validate that a slug is URL-safe (lowercase alphanumeric with hyphens)."""
    if not slug or not _SLUG_PATTERN.match(slug):
        raise ValueError(
            f"{entity_name} slug must be non-empty and match pattern: "
            f"lowercase letters, digits, and hyphens (e.g. 'my-slug-123')"
        )


def _generate_id() -> uuid.UUID:
    """Generate a time-sortable UUID (v7 if available, v4 fallback)."""
    return uuid.uuid7() if hasattr(uuid, "uuid7") else uuid.uuid4()


# ---------------------------------------------------------------------------
# DDD-01: Guarded fields set -- fields that may only be changed through
# explicit domain methods, never by direct attribute assignment.
# ---------------------------------------------------------------------------

_PRODUCT_GUARDED_FIELDS: frozenset[str] = frozenset({"status"})
_BRAND_GUARDED_FIELDS: frozenset[str] = frozenset({"slug"})
_CATEGORY_GUARDED_FIELDS: frozenset[str] = frozenset({"slug"})


# ---------------------------------------------------------------------------
# DUP-05: Partial-update mixin to eliminate repetitive update() boilerplate
# ---------------------------------------------------------------------------


class _PartialUpdateMixin:
    """Mixin providing a reusable ``_apply_partial_update`` helper.

    Subclasses define ``_UPDATABLE_FIELDS: ClassVar[frozenset[str]]`` and
    call this helper from their ``update()`` method to apply only the
    supplied kwargs, rejecting any unknown/immutable fields.
    """

    _UPDATABLE_FIELDS: ClassVar[frozenset[str]]

    def _apply_partial_update(
        self,
        kwargs: dict[str, Any],
        *,
        validators: dict[str, Any] | None = None,
    ) -> set[str]:
        """Apply a partial update from *kwargs* to ``self``.

        Args:
            kwargs: Field-name / value pairs to apply.
            validators: Optional mapping of field name -> callable.
                Each callable receives ``(self, value)`` and should raise
                on invalid input. Called *before* the assignment.

        Returns:
            Set of field names that were actually changed.

        Raises:
            TypeError: If *kwargs* contains keys not in ``_UPDATABLE_FIELDS``.
        """
        unknown = set(kwargs) - self._UPDATABLE_FIELDS
        if unknown:
            raise TypeError(
                f"update() got unexpected keyword argument(s): {', '.join(sorted(unknown))}"
            )

        changed: set[str] = set()
        validators = validators or {}

        for key, value in kwargs.items():
            validator = validators.get(key)
            if validator is not None:
                validator(self, value)
            setattr(self, key, value)
            changed.add(key)

        return changed


# ---------------------------------------------------------------------------
# ARCH-05: Lightweight entity base with event support (not an aggregate root)
# ---------------------------------------------------------------------------


class _EventEmitterEntity:
    """Mixin for child entities that need domain event support.

    Provides the same ``add_domain_event`` / ``domain_events`` /
    ``clear_domain_events`` API as ``AggregateRoot`` but communicates
    that this is a child entity, not a consistency boundary.
    """

    def __attrs_post_init__(self) -> None:
        self._domain_events: list[DomainEvent] = []

    def add_domain_event(self, event: DomainEvent) -> None:
        self._domain_events.append(event)

    def clear_domain_events(self) -> None:
        self._domain_events.clear()

    @property
    def domain_events(self) -> list[DomainEvent]:
        return self._domain_events.copy()


# ============================================================================
# Brand aggregate
# ============================================================================


@dataclass
class Brand(AggregateRoot, _PartialUpdateMixin):
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

    # DDD-01: guard slug against direct mutation
    def __setattr__(self, name: str, value: object) -> None:
        if name in _BRAND_GUARDED_FIELDS and getattr(self, "_Brand__initialized", False):
            raise AttributeError(
                f"Cannot set '{name}' directly on Brand. Use the update() method instead."
            )
        super().__setattr__(name, value)

    def __attrs_post_init__(self) -> None:
        super().__attrs_post_init__()
        object.__setattr__(self, "_Brand__initialized", True)

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
        _validate_slug(slug, "Brand")
        return cls(
            id=brand_id or _generate_id(),
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
            _validate_slug(slug, "Brand")
            # Bypass the guard for controlled mutation via domain method
            object.__setattr__(self, "slug", slug)

    # DDD-06: deletion guard
    def validate_deletable(self, *, has_products: bool) -> None:
        """Validate that this brand can be safely deleted.

        Args:
            has_products: Whether the brand still has associated products.

        Raises:
            BrandHasProductsError: If the brand has associated products.
        """
        if has_products:
            raise BrandHasProductsError(brand_id=self.id)

    def init_logo_upload(self, object_key: str, content_type: str) -> None:
        """Transition logo FSM to PENDING_UPLOAD and emit BrandLogoUploadInitiatedEvent.

        Only allowed from ``None`` (no logo) or ``COMPLETED``/``FAILED`` (re-upload).

        Args:
            object_key: S3 key where the client will upload the raw logo.
            content_type: Expected MIME type of the upload.

        Raises:
            InvalidLogoStateError: If current state is PENDING_UPLOAD or PROCESSING.
        """
        allowed = {None, MediaProcessingStatus.COMPLETED, MediaProcessingStatus.FAILED}
        if self.logo_status not in allowed:
            raise InvalidLogoStateError(
                brand_id=self.id,
                current_status=str(self.logo_status) if self.logo_status else "None",
                expected_status="None, COMPLETED, or FAILED",
            )
        self.logo_status = MediaProcessingStatus.PENDING_UPLOAD

        self.add_domain_event(
            BrandLogoUploadInitiatedEvent(
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
            InvalidLogoStateError: If current state is not PENDING_UPLOAD.
        """
        if self.logo_status != MediaProcessingStatus.PENDING_UPLOAD:
            raise InvalidLogoStateError(
                brand_id=self.id,
                current_status=str(self.logo_status) if self.logo_status else "None",
                expected_status=MediaProcessingStatus.PENDING_UPLOAD,
            )
        self.logo_status = MediaProcessingStatus.PROCESSING

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
            InvalidLogoStateError: If current state is not PROCESSING.
        """
        if self.logo_status != MediaProcessingStatus.PROCESSING:
            raise InvalidLogoStateError(
                brand_id=self.id,
                current_status=str(self.logo_status) if self.logo_status else "None",
                expected_status=MediaProcessingStatus.PROCESSING,
            )
        self.logo_url = url
        self.logo_status = MediaProcessingStatus.COMPLETED

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
            InvalidLogoStateError: If current state is not PROCESSING.
        """
        if self.logo_status != MediaProcessingStatus.PROCESSING:
            raise InvalidLogoStateError(
                brand_id=self.id,
                current_status=str(self.logo_status) if self.logo_status else "None",
                expected_status=MediaProcessingStatus.PROCESSING,
            )
        self.logo_status = MediaProcessingStatus.FAILED

    def retry_logo_upload(self, object_key: str, content_type: str) -> None:
        """Re-initiate logo upload from FAILED state.

        Transitions logo FSM from FAILED back to PENDING_UPLOAD and emits
        a BrandLogoUploadInitiatedEvent so the upload slot is prepared again.

        Args:
            object_key: S3 key where the client will upload the new raw logo.
            content_type: Expected MIME type of the upload.

        Raises:
            InvalidLogoStateError: If current state is not FAILED.
        """
        if self.logo_status != MediaProcessingStatus.FAILED:
            raise InvalidLogoStateError(
                brand_id=self.id,
                current_status=str(self.logo_status) if self.logo_status else "None",
                expected_status=MediaProcessingStatus.FAILED,
            )
        self.logo_status = MediaProcessingStatus.PENDING_UPLOAD

        self.add_domain_event(
            BrandLogoUploadInitiatedEvent(
                brand_id=self.id,
                object_key=object_key,
                content_type=content_type,
                aggregate_id=str(self.id),
            )
        )


# ============================================================================
# Category aggregate
# ============================================================================

MAX_CATEGORY_DEPTH = 3
"""Maximum allowed nesting depth for the category tree."""


@dataclass
class Category(AggregateRoot, _PartialUpdateMixin):
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

    # DDD-01: guard slug against direct mutation
    def __setattr__(self, name: str, value: object) -> None:
        if name in _CATEGORY_GUARDED_FIELDS and getattr(self, "_Category__initialized", False):
            raise AttributeError(
                f"Cannot set '{name}' directly on Category. Use the update() method instead."
            )
        super().__setattr__(name, value)

    def __attrs_post_init__(self) -> None:
        super().__attrs_post_init__()
        object.__setattr__(self, "_Category__initialized", True)

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
        _validate_slug(slug, "Category")
        return cls(
            id=_generate_id(),
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
        _validate_slug(slug, "Category")
        if parent.level >= MAX_CATEGORY_DEPTH:
            raise CategoryMaxDepthError(max_depth=MAX_CATEGORY_DEPTH, current_level=parent.level)

        return cls(
            id=_generate_id(),
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
            _validate_slug(slug, "Category")
            old_full_slug = self.full_slug
            # Bypass the guard for controlled mutation via domain method
            object.__setattr__(self, "slug", slug)
            # Recompute own full_slug by replacing the last path segment
            if self.parent_id is None:
                self.full_slug = slug
            else:
                parent_prefix = self.full_slug.rsplit("/", 1)[0]
                self.full_slug = f"{parent_prefix}/{slug}"

        return old_full_slug

    # DDD-06: deletion guard
    def validate_deletable(
        self,
        *,
        has_children: bool,
        has_products: bool,
    ) -> None:
        """Validate that this category can be safely deleted.

        Args:
            has_children: Whether the category still has child categories.
            has_products: Whether the category still has associated products.

        Raises:
            CategoryHasChildrenError: If the category has child categories.
            CategoryHasProductsError: If the category has associated products.
        """
        if has_children:
            raise CategoryHasChildrenError(category_id=self.id)
        if has_products:
            raise CategoryHasProductsError(category_id=self.id)


# ============================================================================
# AttributeGroup aggregate
# ============================================================================


@dataclass
class AttributeGroup(AggregateRoot, _PartialUpdateMixin):
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
            id=group_id or _generate_id(),
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


# ============================================================================
# Attribute aggregate
# ============================================================================


@dataclass
class Attribute(AggregateRoot, _PartialUpdateMixin):
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
        behavior: Grouped behavior flags (filterable, searchable, etc.).
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
    group_id: uuid.UUID | None
    level: AttributeLevel
    behavior: BehaviorFlags = field(factory=BehaviorFlags)
    validation_rules: dict[str, Any] | None = None

    # Expose individual flags as properties for backward compatibility
    @property
    def is_filterable(self) -> bool:
        return self.behavior.is_filterable

    @property
    def is_searchable(self) -> bool:
        return self.behavior.is_searchable

    @property
    def search_weight(self) -> int:
        return self.behavior.search_weight

    @property
    def is_comparable(self) -> bool:
        return self.behavior.is_comparable

    @property
    def is_visible_on_card(self) -> bool:
        return self.behavior.is_visible_on_card

    @property
    def is_visible_in_catalog(self) -> bool:
        return self.behavior.is_visible_in_catalog

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
        behavior: BehaviorFlags | None = None,
    ) -> Attribute:
        """Factory method to construct a new Attribute aggregate.

        Accepts either a ``BehaviorFlags`` object via *behavior* or
        individual boolean flags for backward compatibility.  If
        *behavior* is provided the individual flags are ignored.

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
            behavior: Optional pre-built BehaviorFlags (overrides individual flags).

        Returns:
            A new Attribute instance.

        Raises:
            ValueError: If name_i18n is empty, search_weight out of range,
                or validation_rules do not match data_type.
        """
        _validate_slug(slug, "Attribute")

        if not name_i18n:
            raise ValueError("name_i18n must contain at least one language entry")

        if behavior is None:
            # Build from individual flags; BehaviorFlags validates search_weight
            behavior = BehaviorFlags(
                is_filterable=is_filterable,
                is_searchable=is_searchable,
                search_weight=search_weight,
                is_comparable=is_comparable,
                is_visible_on_card=is_visible_on_card,
                is_visible_in_catalog=is_visible_in_catalog,
            )

        validate_validation_rules(data_type, validation_rules)

        return cls(
            id=attribute_id or _generate_id(),
            code=code,
            slug=slug,
            name_i18n=name_i18n,
            description_i18n=description_i18n or {},
            data_type=data_type,
            ui_type=ui_type,
            is_dictionary=is_dictionary,
            group_id=group_id,
            level=level,
            behavior=behavior,
            validation_rules=validation_rules,
        )

    _UPDATABLE_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "name_i18n",
            "description_i18n",
            "ui_type",
            "group_id",
            "level",
            "is_filterable",
            "is_searchable",
            "search_weight",
            "is_comparable",
            "is_visible_on_card",
            "is_visible_in_catalog",
            "validation_rules",
            "behavior",
        }
    )

    # Individual behavior flag names mapped to BehaviorFlags field names
    _BEHAVIOR_FLAG_NAMES: ClassVar[frozenset[str]] = frozenset(
        {
            "is_filterable",
            "is_searchable",
            "search_weight",
            "is_comparable",
            "is_visible_on_card",
            "is_visible_in_catalog",
        }
    )

    def update(self, **kwargs: Any) -> None:
        """Update mutable attribute fields. Code, slug, and data_type are immutable.

        Only fields present in *kwargs* are applied. Absent fields are left
        unchanged.  For nullable fields (``group_id``, ``validation_rules``),
        passing ``None`` explicitly clears the value.

        Accepts either a ``behavior`` key with a ``BehaviorFlags`` instance,
        or individual flag keys (``is_filterable``, ``search_weight``, etc.)
        for backward compatibility.

        Raises:
            TypeError: If an unknown/immutable field name is passed.
            ValueError: If name_i18n empty, search_weight out of range,
                or validation_rules incompatible with data_type.
        """
        unknown = kwargs.keys() - self._UPDATABLE_FIELDS
        if unknown:
            raise TypeError(
                f"update() got unexpected keyword argument(s): {', '.join(sorted(unknown))}"
            )

        if "name_i18n" in kwargs:
            name_i18n = kwargs["name_i18n"]
            if name_i18n is not None and not name_i18n:
                raise ValueError("name_i18n must contain at least one language entry")
            if name_i18n is not None:
                self.name_i18n = name_i18n

        if "description_i18n" in kwargs:
            self.description_i18n = kwargs["description_i18n"] or {}

        if "ui_type" in kwargs and kwargs["ui_type"] is not None:
            self.ui_type = kwargs["ui_type"]

        if "group_id" in kwargs:
            self.group_id = kwargs["group_id"]  # nullable -- None clears it

        if "level" in kwargs and kwargs["level"] is not None:
            self.level = kwargs["level"]

        # Handle behavior flags: accept either a BehaviorFlags object or
        # individual flag kwargs for backward compatibility.
        if "behavior" in kwargs and kwargs["behavior"] is not None:
            self.behavior = kwargs["behavior"]
        else:
            # Check if any individual flag kwargs were provided
            flag_updates: dict[str, Any] = {}
            for flag_name in self._BEHAVIOR_FLAG_NAMES:
                if flag_name in kwargs and kwargs[flag_name] is not None:
                    flag_updates[flag_name] = kwargs[flag_name]

            if flag_updates:
                # Validate search_weight if provided
                if "search_weight" in flag_updates:
                    sw = flag_updates["search_weight"]
                    if not (MIN_SEARCH_WEIGHT <= sw <= MAX_SEARCH_WEIGHT):
                        raise ValueError(
                            f"search_weight must be between {MIN_SEARCH_WEIGHT} and "
                            f"{MAX_SEARCH_WEIGHT}, got {sw}"
                        )
                # Build new BehaviorFlags merging current values with updates
                current = {
                    "is_filterable": self.behavior.is_filterable,
                    "is_searchable": self.behavior.is_searchable,
                    "search_weight": self.behavior.search_weight,
                    "is_comparable": self.behavior.is_comparable,
                    "is_visible_on_card": self.behavior.is_visible_on_card,
                    "is_visible_in_catalog": self.behavior.is_visible_in_catalog,
                }
                current.update(flag_updates)
                self.behavior = BehaviorFlags(**current)

        if "validation_rules" in kwargs:
            validation_rules = kwargs["validation_rules"]
            if validation_rules is not None:
                validate_validation_rules(self.data_type, validation_rules)
            self.validation_rules = validation_rules  # nullable -- None clears it


@dataclass
class AttributeValue:
    """Value option for a dictionary attribute (e.g. "Red", "42", "Cotton").

    AttributeValue is a child entity -- not an aggregate root. It does not
    collect domain events itself; events are emitted through the parent
    ``Attribute`` aggregate in command handlers. Each value belongs to
    exactly one ``Attribute`` and carries multilingual labels, search
    aliases, optional metadata, and display ordering.

    Attributes:
        id: Unique value identifier.
        attribute_id: FK to the parent Attribute aggregate.
        code: Machine-readable code, unique within the parent attribute.
        slug: URL-safe identifier, unique within the parent attribute.
        value_i18n: Multilingual display name (e.g. ``{"en": "Red", "ru": "Красный"}``).
        search_aliases: Multilingual synonyms for search (e.g. ``["scarlet", "crimson"]``).
        meta_data: Arbitrary JSON metadata (e.g. ``{"hex": "#FF0000"}``).
        value_group: Optional grouping label (e.g. "Warm tones", "Cool tones").
            Mapped to ``group_code`` in the ORM/database layer. The domain uses
            ``value_group`` to express intent (a UI grouping label), while the
            persistence layer uses ``group_code`` to reflect its column name.
            See ``AttributeValueRepository._to_domain`` / ``_to_orm`` for the
            mapping between the two names.
        sort_order: Display ordering among sibling values.
    """

    id: uuid.UUID
    attribute_id: uuid.UUID
    code: str
    slug: str
    value_i18n: dict[str, str]
    search_aliases: list[str]
    # Named `meta_data` (not `metadata`) to avoid collision with SQLAlchemy Base.metadata
    meta_data: dict[str, Any]
    # Named `value_group` in the domain (UI grouping label); mapped to `group_code`
    # in the ORM layer.  See AttributeValueRepository for the translation.
    value_group: str | None
    sort_order: int

    @classmethod
    def create(
        cls,
        *,
        attribute_id: uuid.UUID,
        code: str,
        slug: str,
        value_i18n: dict[str, str],
        search_aliases: list[str] | None = None,
        meta_data: dict[str, Any] | None = None,
        value_group: str | None = None,
        sort_order: int = 0,
        value_id: uuid.UUID | None = None,
    ) -> AttributeValue:
        """Factory method to construct a new AttributeValue.

        Args:
            attribute_id: UUID of the parent Attribute.
            code: Machine-readable code (unique within attribute).
            slug: URL-safe identifier (unique within attribute).
            value_i18n: Multilingual name. At least one language required.
            search_aliases: Optional list of search synonyms.
            meta_data: Optional arbitrary metadata.
            value_group: Optional grouping label.
            sort_order: Display ordering (default: 0).
            value_id: Optional pre-generated UUID.

        Returns:
            A new AttributeValue instance.

        Raises:
            ValueError: If value_i18n is empty.
        """
        if not value_i18n:
            raise ValueError("value_i18n must contain at least one language entry")
        _validate_slug(slug, "AttributeValue")

        return cls(
            id=value_id or _generate_id(),
            attribute_id=attribute_id,
            code=code,
            slug=slug,
            value_i18n=value_i18n,
            search_aliases=search_aliases or [],
            meta_data=meta_data or {},
            value_group=value_group,
            sort_order=sort_order,
        )

    _UPDATABLE_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "value_i18n",
            "search_aliases",
            "meta_data",
            "value_group",
            "sort_order",
        }
    )

    def update(self, **kwargs: Any) -> None:
        """Update mutable fields. Code and slug are immutable after creation.

        Only fields present in *kwargs* are applied. Absent fields are left
        unchanged.  For nullable fields (``value_group``), passing ``None``
        explicitly clears the value.

        Raises:
            TypeError: If an unknown/immutable field name is passed.
            ValueError: If value_i18n is provided but empty.
        """
        unknown = kwargs.keys() - self._UPDATABLE_FIELDS
        if unknown:
            raise TypeError(
                f"update() got unexpected keyword argument(s): {', '.join(sorted(unknown))}"
            )

        if "value_i18n" in kwargs:
            value_i18n = kwargs["value_i18n"]
            if value_i18n is not None and not value_i18n:
                raise ValueError("value_i18n must contain at least one language entry")
            if value_i18n is not None:
                self.value_i18n = value_i18n

        if "search_aliases" in kwargs and kwargs["search_aliases"] is not None:
            self.search_aliases = kwargs["search_aliases"]

        if "meta_data" in kwargs and kwargs["meta_data"] is not None:
            self.meta_data = kwargs["meta_data"]

        if "value_group" in kwargs:
            self.value_group = kwargs["value_group"]  # nullable -- None clears it

        if "sort_order" in kwargs and kwargs["sort_order"] is not None:
            self.sort_order = kwargs["sort_order"]


@dataclass
class ProductAttributeValue:
    """Product-level attribute assignment (EAV pivot entity).

    Links a product to a specific attribute dictionary value.
    This is a child entity -- not an aggregate root. It does not
    collect domain events; operations are managed through the
    ProductAttributeValue repository and command handlers.

    Attributes:
        id: Unique assignment identifier.
        product_id: FK to the parent Product aggregate.
        attribute_id: FK to the Attribute dictionary entry.
        attribute_value_id: FK to the specific AttributeValue chosen.
    """

    id: uuid.UUID
    product_id: uuid.UUID
    attribute_id: uuid.UUID
    attribute_value_id: uuid.UUID

    @classmethod
    def create(
        cls,
        *,
        product_id: uuid.UUID,
        attribute_id: uuid.UUID,
        attribute_value_id: uuid.UUID,
        pav_id: uuid.UUID | None = None,
    ) -> ProductAttributeValue:
        """Factory method to construct a new ProductAttributeValue.

        Args:
            product_id: UUID of the parent Product.
            attribute_id: UUID of the Attribute being assigned.
            attribute_value_id: UUID of the chosen AttributeValue.
            pav_id: Optional pre-generated UUID; generates uuid4 if omitted.

        Returns:
            A new ProductAttributeValue instance.
        """
        return cls(
            id=pav_id or _generate_id(),
            product_id=product_id,
            attribute_id=attribute_id,
            attribute_value_id=attribute_value_id,
        )


# ============================================================================
# ARCH-05: CategoryAttributeBinding -- child entity (not AggregateRoot)
# ============================================================================


@dataclass
class CategoryAttributeBinding(_EventEmitterEntity, _PartialUpdateMixin):
    """Binding between a category and an attribute with governance settings.

    Child entity (not an aggregate root) that controls which attributes
    apply to a category, their display order, requirement level for
    completeness scoring, optional behavior-flag overrides, and
    per-category filter settings.

    Retains domain event support so that command handlers can emit
    binding-related events through the entity.

    Attributes:
        id: Unique binding identifier.
        category_id: FK to the Category aggregate.
        attribute_id: FK to the Attribute aggregate.
        sort_order: Display ordering of the attribute within the category.
        requirement_level: Required / recommended / optional (default: optional).
        flag_overrides: Optional per-category overrides for global behavior flags.
            Keys match attribute flag names; values override the global setting.
            Example: ``{"is_filterable": True, "search_weight": 8}``.
        filter_settings: Optional per-category filter configuration.
            Example: ``{"filter_type": "range", "thresholds": [0, 5000, 10000]}``.
    """

    id: uuid.UUID
    category_id: uuid.UUID
    attribute_id: uuid.UUID
    sort_order: int
    requirement_level: RequirementLevel
    flag_overrides: dict[str, Any] | None
    filter_settings: dict[str, Any] | None

    @classmethod
    def create(
        cls,
        *,
        category_id: uuid.UUID,
        attribute_id: uuid.UUID,
        sort_order: int = 0,
        requirement_level: RequirementLevel | None = None,
        flag_overrides: dict[str, Any] | None = None,
        filter_settings: dict[str, Any] | None = None,
        binding_id: uuid.UUID | None = None,
    ) -> CategoryAttributeBinding:
        """Factory method to construct a new CategoryAttributeBinding.

        Args:
            category_id: UUID of the category.
            attribute_id: UUID of the attribute.
            sort_order: Display ordering (default: 0).
            requirement_level: Requirement level (default: OPTIONAL).
            flag_overrides: Optional behavior flag overrides.
            filter_settings: Optional filter configuration.
            binding_id: Optional pre-generated UUID.

        Returns:
            A new CategoryAttributeBinding instance.
        """
        return cls(
            id=binding_id or _generate_id(),
            category_id=category_id,
            attribute_id=attribute_id,
            sort_order=sort_order,
            requirement_level=requirement_level or RequirementLevel.OPTIONAL,
            flag_overrides=flag_overrides,
            filter_settings=filter_settings,
        )

    _UPDATABLE_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "sort_order",
            "requirement_level",
            "flag_overrides",
            "filter_settings",
        }
    )

    def update(self, **kwargs: Any) -> None:
        """Update mutable binding fields. category_id and attribute_id are immutable.

        Only fields present in ``kwargs`` are applied. Pass ``None`` for
        nullable fields (flag_overrides, filter_settings) to clear them.

        Raises:
            TypeError: If an unknown field name is passed.
        """
        unknown = set(kwargs) - self._UPDATABLE_FIELDS
        if unknown:
            raise TypeError(f"Cannot update immutable/unknown fields: {unknown}")

        if "sort_order" in kwargs and kwargs["sort_order"] is not None:
            self.sort_order = kwargs["sort_order"]
        if "requirement_level" in kwargs and kwargs["requirement_level"] is not None:
            self.requirement_level = kwargs["requirement_level"]
        if "flag_overrides" in kwargs:
            self.flag_overrides = kwargs["flag_overrides"]
        if "filter_settings" in kwargs:
            self.filter_settings = kwargs["filter_settings"]


# ---------------------------------------------------------------------------
# SKU -- child entity owned by the Product aggregate
# ---------------------------------------------------------------------------


@dataclass
class SKU:
    """Stock Keeping Unit -- a purchasable item within a ProductVariant.

    Child entity owned by a ProductVariant (which is itself a child of
    the Product aggregate). Each SKU represents a unique combination of
    variant attributes (e.g. size) identified by its ``variant_hash``.
    The hash is computed once by the owning Product and stored immutably;
    it is recalculated only when ``variant_attributes`` change via ``update()``.

    Attributes:
        id: Unique SKU identifier.
        product_id: FK to the owning Product aggregate (denormalized).
        variant_id: FK to the parent ProductVariant.
        sku_code: Human-readable stock-keeping code.
        variant_hash: SHA-256 hash of sorted variant attribute pairs.
        price: Base price as a Money value object, or None to inherit from variant.
        compare_at_price: Previous/original price for strikethrough display.
        is_active: Whether the SKU is available for sale.
        version: Optimistic locking version counter (incremented by repo on save).
        deleted_at: Soft-delete timestamp, or None if active.
        created_at: Creation timestamp (UTC).
        updated_at: Last modification timestamp (UTC).
        variant_attributes: List of (attribute_id, attribute_value_id) tuples.
    """

    id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID
    sku_code: str
    variant_hash: str
    price: Money | None = None
    compare_at_price: Money | None = None
    is_active: bool = True
    version: int = 1
    deleted_at: datetime | None = None
    created_at: datetime = field(factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(factory=lambda: datetime.now(UTC))
    variant_attributes: list[tuple[uuid.UUID, uuid.UUID]] = field(factory=list)

    def __attrs_post_init__(self) -> None:
        """Validate compare_at_price > price when both are provided."""
        if self.price is None and self.compare_at_price is not None:
            raise ValueError("compare_at_price cannot be set when price is None")
        if self.compare_at_price is not None:
            if self.compare_at_price.amount <= 0:
                raise ValueError("compare_at_price amount must be greater than zero")
            if self.price is not None:
                if self.compare_at_price.currency != self.price.currency:
                    raise ValueError(
                        f"compare_at_price currency ({self.compare_at_price.currency}) "
                        f"must match price currency ({self.price.currency})"
                    )
                if not self.compare_at_price > self.price:
                    raise ValueError("compare_at_price must be greater than price")

    def soft_delete(self) -> None:
        """Mark this SKU as deleted.

        Sets ``deleted_at`` and ``updated_at`` to the current UTC timestamp.
        The record is retained in the database; filters must exclude
        non-None ``deleted_at`` when listing active variants.
        """
        now = datetime.now(UTC)
        self.deleted_at = now
        self.updated_at = now

    _UPDATABLE_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "sku_code",
            "price",
            "compare_at_price",
            "is_active",
            "variant_attributes",
            "variant_hash",
        }
    )

    def update(self, **kwargs: Any) -> None:
        """Update mutable SKU fields.

        Only fields present in ``kwargs`` are applied. Pass ``None`` for
        ``compare_at_price`` to clear it.

        After any price or compare_at_price change the constraint
        ``compare_at_price > price`` is re-validated.

        Raises:
            TypeError: If an unknown field name is passed.
            ValueError: If the resulting compare_at_price <= price.
        """
        unknown = set(kwargs) - self._UPDATABLE_FIELDS
        if unknown:
            raise TypeError(f"Cannot update immutable/unknown fields: {unknown}")

        if "sku_code" in kwargs:
            self.sku_code = kwargs["sku_code"]
        if "price" in kwargs:
            self.price = kwargs["price"]
        if "compare_at_price" in kwargs:
            self.compare_at_price = kwargs["compare_at_price"]
        if "is_active" in kwargs:
            self.is_active = kwargs["is_active"]
        if "variant_attributes" in kwargs:
            self.variant_attributes = kwargs["variant_attributes"]
        if "variant_hash" in kwargs:
            self.variant_hash = kwargs["variant_hash"]

        # Re-validate price constraint after any price-related change.
        if self.price is None and self.compare_at_price is not None:
            raise ValueError("compare_at_price cannot be set when price is None")
        if self.compare_at_price is not None:
            if self.compare_at_price.amount <= 0:
                raise ValueError("compare_at_price amount must be greater than zero")
            if self.price is not None and not self.compare_at_price > self.price:
                raise ValueError("compare_at_price must be greater than price")
        if (
            self.price is not None
            and self.compare_at_price is not None
            and self.compare_at_price.currency != self.price.currency
        ):
            raise ValueError(
                f"compare_at_price currency ({self.compare_at_price.currency}) "
                f"must match price currency ({self.price.currency})"
            )

        self.updated_at = datetime.now(UTC)


# ---------------------------------------------------------------------------
# ProductVariant -- child entity owned by the Product aggregate
# ---------------------------------------------------------------------------


@dataclass
class ProductVariant:
    """Product variant -- a named variation grouping that owns SKUs.

    Child entity of the Product aggregate. Each variant represents a
    tab in the admin UI with its own name, media, and set of SKUs.
    """

    id: uuid.UUID
    product_id: uuid.UUID
    name_i18n: dict[str, str]
    description_i18n: dict[str, str] | None
    sort_order: int
    default_price: Money | None
    default_currency: str
    skus: list[SKU]
    deleted_at: datetime | None = None
    created_at: datetime = field(factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(factory=lambda: datetime.now(UTC))

    @classmethod
    def create(
        cls,
        *,
        product_id: uuid.UUID,
        name_i18n: dict[str, str],
        description_i18n: dict[str, str] | None = None,
        sort_order: int = 0,
        default_price: Money | None = None,
        default_currency: str = DEFAULT_CURRENCY,
        variant_id: uuid.UUID | None = None,
    ) -> ProductVariant:
        """Factory method to construct a new ProductVariant.

        Args:
            product_id: UUID of the owning Product aggregate.
            name_i18n: Multilingual variant name. At least one entry required.
            description_i18n: Optional multilingual description.
            sort_order: Display ordering among sibling variants (default: 0).
            default_price: Optional default price for SKUs in this variant.
            default_currency: Default currency code (default: "RUB").
            variant_id: Optional pre-generated UUID.

        Returns:
            A new ProductVariant instance with an empty SKU list.

        Raises:
            ValueError: If name_i18n is empty.
        """
        if not name_i18n:
            raise ValueError("name_i18n must contain at least one language entry")
        return cls(
            id=variant_id or _generate_id(),
            product_id=product_id,
            name_i18n=name_i18n,
            description_i18n=description_i18n,
            sort_order=sort_order,
            default_price=default_price,
            default_currency=default_currency,
            skus=[],
        )

    _UPDATABLE_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "name_i18n",
            "description_i18n",
            "sort_order",
            "default_price",
            "default_currency",
        }
    )

    def update(self, **kwargs: Any) -> None:
        """Update mutable variant fields.

        Only fields present in ``kwargs`` are applied. Pass ``None`` for
        ``description_i18n`` or ``default_price`` to clear them.

        Raises:
            TypeError: If an unknown field name is passed.
        """
        unknown = set(kwargs) - self._UPDATABLE_FIELDS
        if unknown:
            raise TypeError(f"Cannot update immutable/unknown fields: {unknown}")

        if "name_i18n" in kwargs:
            if not kwargs["name_i18n"]:
                raise ValueError("name_i18n must contain at least one language entry")
            self.name_i18n = kwargs["name_i18n"]
        if "description_i18n" in kwargs:
            self.description_i18n = kwargs["description_i18n"]
        if "sort_order" in kwargs:
            self.sort_order = kwargs["sort_order"]
        if "default_price" in kwargs:
            self.default_price = kwargs["default_price"]
            if kwargs["default_price"] is not None:
                self.default_currency = kwargs["default_price"].currency
        if "default_currency" in kwargs:
            currency = kwargs["default_currency"]
            if not (len(currency) == 3 and currency.isascii() and currency.isupper()):
                raise ValueError("default_currency must be exactly 3 uppercase ASCII letters")
            self.default_currency = currency

        self.updated_at = datetime.now(UTC)

    def soft_delete(self) -> None:
        """Mark this variant and all its active SKUs as deleted."""
        now = datetime.now(UTC)
        self.deleted_at = now
        self.updated_at = now
        for sku in self.skus:
            if sku.deleted_at is None:
                sku.soft_delete()


# ---------------------------------------------------------------------------
# MediaAsset -- independent aggregate for product media resources
# ---------------------------------------------------------------------------


@dataclass
class MediaAsset(AggregateRoot):
    """MediaAsset aggregate -- independently addressable media resource.

    Manages the lifecycle of a single media file (image, video, 3D model,
    or document) attached to a product. Extends AggregateRoot to support
    domain event emission for the processing FSM. Has its own repository
    (IMediaAssetRepository) and is addressed independently from Product.

    Lifecycle follows a strict processing FSM:
    ``PENDING_UPLOAD`` -> ``PROCESSING`` -> ``COMPLETED`` | ``FAILED``.

    External URLs bypass the FSM entirely and are created with ``COMPLETED``
    status via the ``create_external`` factory.

    Attributes:
        id: Unique media asset identifier.
        product_id: FK to the parent Product aggregate.
        variant_id: Optional FK to a ProductVariant (for variant-specific media).
        media_type: MIME-type hint or media category (e.g. ``"image/jpeg"``).
        role: Semantic role of the asset (e.g. ``"gallery"``, ``"cover"``).
        sort_order: Display ordering among sibling assets.
        processing_status: Current state of the processing FSM, or None.
        storage_object_id: FK to the StorageObject record, if any.
        is_external: True if the media URL is hosted externally.
        external_url: URL of the externally hosted asset, if applicable.
        raw_object_key: S3 key of the raw (unprocessed) upload, if any.
        public_url: Public URL of the processed asset, set on completion.
    """

    id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID | None
    media_type: str
    role: str
    sort_order: int
    processing_status: MediaProcessingStatus | None = None
    storage_object_id: uuid.UUID | None = None
    is_external: bool = False
    external_url: str | None = None
    raw_object_key: str | None = None
    processed_object_key: str | None = None
    public_url: str | None = None

    @classmethod
    def create_upload(
        cls,
        *,
        product_id: uuid.UUID,
        media_type: str,
        role: str,
        raw_object_key: str,
        sort_order: int = 0,
        variant_id: uuid.UUID | None = None,
        media_id: uuid.UUID | None = None,
    ) -> MediaAsset:
        """Factory method for a new upload-based media asset.

        Creates the entity with ``PENDING_UPLOAD`` status so the client can
        upload the raw file to the pre-signed S3 URL.

        Args:
            product_id: UUID of the owning Product aggregate.
            media_type: MIME-type hint or media category string.
            role: Semantic role of the asset within the product listing.
            raw_object_key: S3 key where the raw file will be uploaded.
            sort_order: Display ordering among sibling assets (default: 0).
            variant_id: Optional FK to a ProductVariant (variant-specific media).
            media_id: Optional pre-generated UUID; generates uuid4 if omitted.

        Returns:
            A new MediaAsset instance in ``PENDING_UPLOAD`` state.
        """
        return cls(
            id=media_id or _generate_id(),
            product_id=product_id,
            variant_id=variant_id,
            media_type=media_type,
            role=role,
            sort_order=sort_order,
            processing_status=MediaProcessingStatus.PENDING_UPLOAD,
            is_external=False,
            raw_object_key=raw_object_key,
        )

    @classmethod
    def create_external(
        cls,
        *,
        product_id: uuid.UUID,
        media_type: str,
        role: str,
        external_url: str,
        sort_order: int = 0,
        variant_id: uuid.UUID | None = None,
        media_id: uuid.UUID | None = None,
    ) -> MediaAsset:
        """Factory method for an externally hosted media asset.

        Creates the entity with ``COMPLETED`` status; no upload or processing
        is required because the asset is served from an external URL.

        Args:
            product_id: UUID of the owning Product aggregate.
            media_type: MIME-type hint or media category string.
            role: Semantic role of the asset within the product listing.
            external_url: Public URL of the externally hosted file.
            sort_order: Display ordering among sibling assets (default: 0).
            variant_id: Optional FK to a ProductVariant (variant-specific media).
            media_id: Optional pre-generated UUID; generates uuid4 if omitted.

        Returns:
            A new MediaAsset instance in ``COMPLETED`` state with the
            ``public_url`` set to ``external_url``.
        """
        return cls(
            id=media_id or _generate_id(),
            product_id=product_id,
            variant_id=variant_id,
            media_type=media_type,
            role=role,
            sort_order=sort_order,
            processing_status=MediaProcessingStatus.COMPLETED,
            is_external=True,
            external_url=external_url,
            public_url=external_url,
        )

    def confirm_upload(self, content_type: str = "") -> None:
        """Transition FSM from PENDING_UPLOAD to PROCESSING.

        Emits a ``ProductMediaConfirmedEvent`` so the Outbox relays it to the
        AI processing service via RabbitMQ.

        Args:
            content_type: MIME type of the uploaded file (forwarded in the event).

        Raises:
            InvalidMediaStateError: If current state is not PENDING_UPLOAD.
        """
        if self.processing_status != MediaProcessingStatus.PENDING_UPLOAD:
            raise InvalidMediaStateError(
                media_id=self.id,
                current_status=str(self.processing_status) if self.processing_status else None,
                expected_status=MediaProcessingStatus.PENDING_UPLOAD.value,
            )
        self.processing_status = MediaProcessingStatus.PROCESSING

        self.add_domain_event(
            ProductMediaConfirmedEvent(
                media_id=self.id,
                product_id=self.product_id,
                object_key=self.raw_object_key or "",
                content_type=content_type,
                aggregate_id=str(self.id),
            )
        )

    def complete_processing(
        self,
        public_url: str,
        object_key: str,
        content_type: str = "",
        size_bytes: int = 0,
        storage_object_id: uuid.UUID | None = None,
    ) -> None:
        """Transition FSM from PROCESSING to COMPLETED.

        Sets the public URL and optionally records the storage object reference.

        Args:
            public_url: Public URL of the processed media file.
            object_key: Final S3 key of the processed file (stored for reference).
            content_type: MIME type of the processed file.
            size_bytes: Size of the processed file in bytes.
            storage_object_id: Optional FK to the StorageObject record.

        Raises:
            InvalidMediaStateError: If current state is not PROCESSING.
        """
        if self.processing_status != MediaProcessingStatus.PROCESSING:
            raise InvalidMediaStateError(
                media_id=self.id,
                current_status=str(self.processing_status) if self.processing_status else None,
                expected_status=MediaProcessingStatus.PROCESSING.value,
            )
        self.public_url = public_url
        self.processed_object_key = object_key
        self.storage_object_id = storage_object_id
        self.processing_status = MediaProcessingStatus.COMPLETED

        self.add_domain_event(
            ProductMediaProcessedEvent(
                media_id=self.id,
                product_id=self.product_id,
                object_key=object_key,
                content_type=content_type,
                size_bytes=size_bytes,
                aggregate_id=str(self.id),
            )
        )

    def fail_processing(self) -> None:
        """Transition FSM from PROCESSING to FAILED.

        Raises:
            InvalidMediaStateError: If current state is not PROCESSING.
        """
        if self.processing_status != MediaProcessingStatus.PROCESSING:
            raise InvalidMediaStateError(
                media_id=self.id,
                current_status=str(self.processing_status) if self.processing_status else None,
                expected_status=MediaProcessingStatus.PROCESSING.value,
            )
        self.processing_status = MediaProcessingStatus.FAILED


# ---------------------------------------------------------------------------
# Product -- aggregate root
# ---------------------------------------------------------------------------


@dataclass
class Product(AggregateRoot, _PartialUpdateMixin):
    """Product aggregate root -- central catalog entity.

    Owns ProductVariant child entities (which in turn own SKUs), enforces
    status lifecycle transitions (FSM), and computes variant hashes for
    SKU uniqueness.  Carries a ``version``
    field for optimistic locking (incremented by the repository on save)
    and supports soft-delete via ``deleted_at``.

    Emits ProductCreatedEvent on creation and ProductStatusChangedEvent on status transitions.

    Status FSM (allowed transitions)::

        DRAFT -> ENRICHING
        ENRICHING -> DRAFT | READY_FOR_REVIEW
        READY_FOR_REVIEW -> ENRICHING | PUBLISHED
        PUBLISHED -> ARCHIVED
        ARCHIVED -> DRAFT

    Attributes:
        id: Unique product identifier.
        slug: URL-safe unique identifier for routing.
        title_i18n: Multilingual product title (at least one entry required).
        description_i18n: Multilingual product description.
        status: Current lifecycle state (FSM-controlled).
        brand_id: FK to the Brand aggregate.
        primary_category_id: FK to the primary Category.
        supplier_id: FK to the Supplier, or None.
        country_of_origin: ISO 3166-1 alpha-2 country code, or None.
        tags: List of searchable tags.
        version: Optimistic locking version counter (managed by repo).
        deleted_at: Soft-delete timestamp, or None if active.
        created_at: Creation timestamp (UTC).
        updated_at: Last modification timestamp (UTC).
        published_at: Timestamp of first publication, or None.
        variants: List of owned ProductVariant child entities (includes soft-deleted).
    """

    # Class-level FSM transition table -- excluded from attrs __init__ via ClassVar.
    _ALLOWED_TRANSITIONS: ClassVar[dict[ProductStatus, set[ProductStatus]]] = {
        ProductStatus.DRAFT: {ProductStatus.ENRICHING},
        ProductStatus.ENRICHING: {ProductStatus.DRAFT, ProductStatus.READY_FOR_REVIEW},
        ProductStatus.READY_FOR_REVIEW: {
            ProductStatus.ENRICHING,
            ProductStatus.PUBLISHED,
        },
        ProductStatus.PUBLISHED: {ProductStatus.ARCHIVED},
        ProductStatus.ARCHIVED: {ProductStatus.DRAFT},
    }

    id: uuid.UUID
    slug: str
    title_i18n: dict[str, str]
    description_i18n: dict[str, str]
    status: ProductStatus
    brand_id: uuid.UUID
    primary_category_id: uuid.UUID
    supplier_id: uuid.UUID | None = None
    country_of_origin: str | None = None
    tags: list[str] = field(factory=list)
    version: int = 1
    deleted_at: datetime | None = None
    created_at: datetime = field(factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(factory=lambda: datetime.now(UTC))
    published_at: datetime | None = None
    variants: list[ProductVariant] = field(factory=list)

    # DDD-01: guard status against direct mutation
    def __setattr__(self, name: str, value: object) -> None:
        if name in _PRODUCT_GUARDED_FIELDS and getattr(self, "_Product__initialized", False):
            raise AttributeError(
                f"Cannot set '{name}' directly on Product. Use transition_status() instead."
            )
        super().__setattr__(name, value)

    def __attrs_post_init__(self) -> None:
        super().__attrs_post_init__()
        object.__setattr__(self, "_Product__initialized", True)

    @classmethod
    def create(
        cls,
        *,
        slug: str,
        title_i18n: dict[str, str],
        brand_id: uuid.UUID,
        primary_category_id: uuid.UUID,
        description_i18n: dict[str, str] | None = None,
        supplier_id: uuid.UUID | None = None,
        country_of_origin: str | None = None,
        tags: list[str] | None = None,
        product_id: uuid.UUID | None = None,
    ) -> Product:
        """Factory method to construct a new Product in DRAFT status.

        Args:
            slug: URL-safe unique identifier.
            title_i18n: Multilingual product title. At least one entry required.
            brand_id: UUID of the owning Brand aggregate.
            primary_category_id: UUID of the primary Category.
            description_i18n: Optional multilingual description.
            supplier_id: Optional UUID of the Supplier.
            country_of_origin: Optional ISO 3166-1 alpha-2 country code.
            tags: Optional list of searchable tags.
            product_id: Optional pre-generated UUID; generates uuid7/uuid4 if omitted.

        Returns:
            A new Product instance in DRAFT status with one default variant.

        Raises:
            ValueError: If ``title_i18n`` is empty.
        """
        _validate_slug(slug, "Product")
        if not title_i18n:
            raise ValueError("title_i18n must contain at least one language entry")

        product = cls(
            id=product_id or _generate_id(),
            slug=slug,
            title_i18n=title_i18n,
            description_i18n=description_i18n or {},
            status=ProductStatus.DRAFT,
            brand_id=brand_id,
            primary_category_id=primary_category_id,
            supplier_id=supplier_id,
            country_of_origin=country_of_origin,
            tags=tags or [],
            version=1,
            variants=[],
        )
        # Auto-create 1 default variant
        default_variant = ProductVariant.create(
            product_id=product.id,
            name_i18n=title_i18n,
        )
        product.variants.append(default_variant)
        product.add_domain_event(
            ProductCreatedEvent(
                product_id=product.id,
                slug=product.slug,
                aggregate_id=str(product.id),
            )
        )
        return product

    _UPDATABLE_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "title_i18n",
            "description_i18n",
            "slug",
            "brand_id",
            "primary_category_id",
            "supplier_id",
            "country_of_origin",
            "tags",
        }
    )

    def update(self, **kwargs: Any) -> None:
        """Update mutable product fields.

        Only fields present in ``kwargs`` are modified; absent fields are
        left unchanged.  Nullable fields (``supplier_id``,
        ``country_of_origin``) can be set to ``None`` to clear them.

        Args:
            **kwargs: Field-name/value pairs to update.  Supported keys:
                ``title_i18n``, ``description_i18n``, ``slug``, ``brand_id``,
                ``primary_category_id``, ``supplier_id``, ``country_of_origin``,
                ``tags``.

        Raises:
            TypeError: If an unknown/immutable field name is passed.
            ValueError: If ``title_i18n`` is provided but empty, or if
                ``brand_id`` / ``primary_category_id`` is set to None.
        """
        unknown = set(kwargs) - self._UPDATABLE_FIELDS
        if unknown:
            raise TypeError(f"Cannot update immutable/unknown fields: {unknown}")

        changed = False

        if "title_i18n" in kwargs:
            if not kwargs["title_i18n"]:
                raise ValueError("title_i18n must contain at least one language entry")
            self.title_i18n = kwargs["title_i18n"]
            changed = True

        if "description_i18n" in kwargs:
            self.description_i18n = kwargs["description_i18n"]
            changed = True

        if "slug" in kwargs:
            _validate_slug(kwargs["slug"], "Product")
            self.slug = kwargs["slug"]
            changed = True

        if "brand_id" in kwargs:
            if kwargs["brand_id"] is None:
                raise ValueError("brand_id cannot be None")
            self.brand_id = kwargs["brand_id"]
            changed = True

        if "primary_category_id" in kwargs:
            if kwargs["primary_category_id"] is None:
                raise ValueError("primary_category_id cannot be None")
            self.primary_category_id = kwargs["primary_category_id"]
            changed = True

        if "supplier_id" in kwargs:
            self.supplier_id = kwargs["supplier_id"]  # can be None
            changed = True

        if "country_of_origin" in kwargs:
            self.country_of_origin = kwargs["country_of_origin"]  # can be None
            changed = True

        if "tags" in kwargs:
            self.tags = kwargs["tags"]
            changed = True

        if changed:
            self.updated_at = datetime.now(UTC)
            self.add_domain_event(
                ProductUpdatedEvent(
                    product_id=self.id,
                    aggregate_id=str(self.id),
                )
            )

    def soft_delete(self) -> None:
        """Mark this product as deleted.

        Sets ``deleted_at`` and ``updated_at`` to the current UTC timestamp.
        Cascades soft-delete to all active variants (which in turn cascade
        to their SKUs). The record is retained in the database; queries
        must exclude non-None ``deleted_at`` when listing active products.

        Raises:
            InvalidStatusTransitionError: If the product is currently
                PUBLISHED -- it must be ARCHIVED first.
        """
        if self.deleted_at is not None:
            return
        if self.status == ProductStatus.PUBLISHED:
            raise CannotDeletePublishedProductError(
                product_id=self.id,
                current_status=self.status.value,
            )
        now = datetime.now(UTC)
        self.deleted_at = now
        self.updated_at = now
        for variant in self.variants:
            if variant.deleted_at is None:
                variant.soft_delete()

    def transition_status(self, new_status: ProductStatus) -> None:
        """Transition the product to a new lifecycle status.

        Validates the transition against the FSM table defined in
        ``_ALLOWED_TRANSITIONS``.  If transitioning to PUBLISHED, sets
        ``published_at`` to the current UTC timestamp (only set once;
        not cleared on subsequent transitions).

        Args:
            new_status: The target ProductStatus value.

        Raises:
            InvalidStatusTransitionError: If ``new_status`` is not in the
                set of allowed transitions from the current ``status``.
        """
        allowed = self._ALLOWED_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise InvalidStatusTransitionError(
                current_status=self.status,
                target_status=new_status,
                allowed_transitions=list(allowed),
            )
        if new_status in (ProductStatus.PUBLISHED, ProductStatus.READY_FOR_REVIEW):
            active_skus = [
                s
                for v in self.variants
                if v.deleted_at is None
                for s in v.skus
                if s.deleted_at is None and s.is_active
            ]
            if not active_skus:
                raise ProductNotReadyError(
                    product_id=self.id,
                    reason=f"Cannot transition to {new_status.value}: product has no active SKUs",
                )
            if new_status == ProductStatus.PUBLISHED and not any(
                s.price is not None for s in active_skus
            ):
                raise ProductNotReadyError(
                    product_id=self.id,
                    reason="Cannot publish product without at least one priced SKU",
                )
        old_status = self.status.value
        # Bypass the guard for controlled FSM mutation
        object.__setattr__(self, "status", new_status)
        if new_status == ProductStatus.PUBLISHED and self.published_at is None:
            self.published_at = datetime.now(UTC)
        self.updated_at = datetime.now(UTC)
        self.add_domain_event(
            ProductStatusChangedEvent(
                product_id=self.id,
                old_status=old_status,
                new_status=new_status.value,
                aggregate_id=str(self.id),
            )
        )

    # ------------------------------------------------------------------
    # Variant management
    # ------------------------------------------------------------------

    def add_variant(
        self,
        *,
        name_i18n: dict[str, str],
        description_i18n: dict[str, str] | None = None,
        sort_order: int = 0,
        default_price: Money | None = None,
        default_currency: str = DEFAULT_CURRENCY,
    ) -> ProductVariant:
        """Create and attach a new ProductVariant to this product.

        Args:
            name_i18n: Multilingual variant name. At least one entry required.
            description_i18n: Optional multilingual description.
            sort_order: Display ordering among sibling variants (default: 0).
            default_price: Optional default price for SKUs in this variant.
            default_currency: Default currency code (default: "RUB").

        Returns:
            The newly created and attached ProductVariant instance.
        """
        variant = ProductVariant.create(
            product_id=self.id,
            name_i18n=name_i18n,
            description_i18n=description_i18n,
            sort_order=sort_order,
            default_price=default_price,
            default_currency=default_currency,
        )
        self.variants.append(variant)
        self.add_domain_event(
            VariantAddedEvent(product_id=self.id, variant_id=variant.id, aggregate_id=str(self.id))
        )
        self.updated_at = datetime.now(UTC)
        return variant

    def find_variant(self, variant_id: uuid.UUID) -> ProductVariant | None:
        """Find an active (non-deleted) variant by its identifier.

        Args:
            variant_id: The UUID of the variant to locate.

        Returns:
            The matching ProductVariant instance, or None if not found or soft-deleted.
        """
        for variant in self.variants:
            if variant.id == variant_id and variant.deleted_at is None:
                return variant
        return None

    def remove_variant(self, variant_id: uuid.UUID) -> None:
        """Soft-delete a variant and all its SKUs from this product.

        Cannot remove the last active variant.

        Args:
            variant_id: The UUID of the variant to remove.

        Raises:
            VariantNotFoundError: If no active variant with the given ID exists.
            LastVariantRemovalError: If this is the only remaining active variant.
        """
        variant = self.find_variant(variant_id)
        if variant is None:
            raise VariantNotFoundError(variant_id=variant_id, product_id=self.id)
        active_variants = [v for v in self.variants if v.deleted_at is None]
        if len(active_variants) <= 1:
            raise LastVariantRemovalError(product_id=self.id)
        variant.soft_delete()
        self.add_domain_event(
            VariantRemovedEvent(
                product_id=self.id, variant_id=variant_id, aggregate_id=str(self.id)
            )
        )
        self.updated_at = datetime.now(UTC)

    # ------------------------------------------------------------------
    # SKU management (delegated through variants)
    # ------------------------------------------------------------------

    def add_sku(
        self,
        variant_id: uuid.UUID,
        *,
        sku_code: str,
        price: Money | None = None,
        compare_at_price: Money | None = None,
        is_active: bool = True,
        variant_attributes: list[tuple[uuid.UUID, uuid.UUID]] | None = None,
    ) -> SKU:
        """Create and attach a new SKU to a specific variant of this product.

        Computes the ``variant_hash`` from ``variant_attributes`` and checks
        it is unique among non-deleted SKUs across ALL variants.

        Args:
            variant_id: UUID of the target ProductVariant.
            sku_code: Human-readable stock-keeping code.
            price: Optional base selling price (can be None; inherits from variant).
            compare_at_price: Optional strikethrough price (must be > price).
            is_active: Whether the new SKU is immediately available.
            variant_attributes: List of (attribute_id, attribute_value_id) pairs
                that uniquely identify this variant combination.

        Returns:
            The newly created and attached SKU instance.

        Raises:
            VariantNotFoundError: If no active variant with the given ID exists.
            DuplicateVariantCombinationError: If an active SKU with the same
                variant attribute combination already exists.
        """
        variant = self.find_variant(variant_id)
        if variant is None:
            raise VariantNotFoundError(variant_id=variant_id, product_id=self.id)
        # compute hash, check uniqueness across ALL variants
        effective_attrs = variant_attributes or []
        variant_hash = self.compute_variant_hash(variant_id, effective_attrs)
        for v in self.variants:
            for existing in v.skus:
                if existing.deleted_at is None and existing.variant_hash == variant_hash:
                    raise DuplicateVariantCombinationError(
                        product_id=self.id,
                        variant_hash=variant_hash,
                    )
        sku = SKU(
            id=_generate_id(),
            product_id=self.id,
            variant_id=variant_id,
            sku_code=sku_code,
            variant_hash=variant_hash,
            price=price,
            compare_at_price=compare_at_price,
            is_active=is_active,
            variant_attributes=list(effective_attrs),
        )
        variant.skus.append(sku)
        self.add_domain_event(
            SKUAddedEvent(
                product_id=self.id,
                variant_id=variant_id,
                sku_id=sku.id,
                sku_code=sku.sku_code,
                aggregate_id=str(self.id),
            )
        )
        self.updated_at = datetime.now(UTC)
        return sku

    def find_sku(self, sku_id: uuid.UUID) -> SKU | None:
        """Find an active (non-deleted) SKU by its identifier across all variants.

        Args:
            sku_id: The UUID of the SKU to locate.

        Returns:
            The matching SKU instance, or None if not found or soft-deleted.
        """
        for variant in self.variants:
            for sku in variant.skus:
                if sku.id == sku_id and sku.deleted_at is None:
                    return sku
        return None

    def remove_sku(self, sku_id: uuid.UUID) -> None:
        """Soft-delete a SKU from this product (searches across all variants).

        Args:
            sku_id: The UUID of the SKU to remove.

        Raises:
            SKUNotFoundError: If no active SKU with the given ID exists.
        """
        for variant in self.variants:
            for sku in variant.skus:
                if sku.id == sku_id and sku.deleted_at is None:
                    sku.soft_delete()
                    self.add_domain_event(
                        SKURemovedEvent(
                            product_id=self.id,
                            variant_id=variant.id,
                            sku_id=sku_id,
                            aggregate_id=str(self.id),
                        )
                    )
                    self.updated_at = datetime.now(UTC)
                    return
        raise SKUNotFoundError(sku_id=sku_id)

    @staticmethod
    def compute_variant_hash(
        variant_id: uuid.UUID,
        variant_attributes: list[tuple[uuid.UUID, uuid.UUID]],
    ) -> str:
        """Compute a deterministic SHA-256 hash for a variant attribute combination.

        Includes ``variant_id`` in the hash so that different variants can
        each have an empty-attributes SKU without collision.  Sorts pairs
        by attribute_id (as string) before hashing so that the result is
        independent of insertion order.

        Args:
            variant_id: UUID of the owning ProductVariant.
            variant_attributes: List of (attribute_id, attribute_value_id) pairs.

        Returns:
            A 64-character lowercase hex string (SHA-256 digest).
        """
        sorted_attrs = sorted(variant_attributes, key=lambda x: str(x[0]))
        payload = str(variant_id) + ":" + "|".join(f"{a!s}:{v!s}" for a, v in sorted_attrs)
        return hashlib.sha256(payload.encode()).hexdigest()
