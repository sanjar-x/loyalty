"""
Category aggregate root entity supporting hierarchical trees.

Categories form a tree with a maximum depth of ``MAX_CATEGORY_DEPTH``.
Each category maintains a materialized ``full_slug`` path for efficient
URL resolution and descendant queries.
Part of the domain layer -- zero infrastructure imports.
"""

import uuid
from typing import ClassVar

from attr import dataclass

from src.modules.catalog.domain.exceptions import (
    CategoryHasChildrenError,
    CategoryHasProductsError,
    CategoryMaxDepthError,
)
from src.modules.catalog.domain.value_objects import validate_i18n_completeness
from src.shared.interfaces.entities import AggregateRoot

from ._common import (
    _generate_id,
    _validate_i18n_values,
    _validate_slug,
    _validate_sort_order,
)

MAX_CATEGORY_DEPTH = 3
"""Maximum allowed nesting depth for the category tree."""

# ---------------------------------------------------------------------------
# DDD-01: Guarded fields set -- fields that may only be changed through
# explicit domain methods, never by direct attribute assignment.
# ---------------------------------------------------------------------------

_CATEGORY_GUARDED_FIELDS: frozenset[str] = frozenset({"slug"})


@dataclass
class Category(AggregateRoot):
    """Category aggregate root supporting hierarchical trees.

    Categories form a tree with a maximum depth of ``MAX_CATEGORY_DEPTH``.
    Each category maintains a materialized ``full_slug`` path for efficient
    URL resolution and descendant queries.

    Attributes:
        id: Unique category identifier (uuid7 when available, uuid4 fallback).
        parent_id: UUID of the parent category, or None for root categories.
        name_i18n: Multilingual display name.
        slug: URL-safe identifier, unique within the same parent level.
        full_slug: Materialized path (e.g. ``"electronics/phones/android"``).
        level: Depth in the tree (0 = root).
        sort_order: Display ordering within the same parent.
    """

    id: uuid.UUID
    parent_id: uuid.UUID | None
    name_i18n: dict[str, str]
    slug: str
    full_slug: str
    level: int
    sort_order: int
    template_id: uuid.UUID | None = None
    effective_template_id: uuid.UUID | None = None

    # DDD-01: guard slug against direct mutation
    def __setattr__(self, name: str, value: object) -> None:
        if name in _CATEGORY_GUARDED_FIELDS and getattr(
            self, "_Category__initialized", False
        ):
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
        name_i18n: dict[str, str],
        slug: str,
        sort_order: int = 0,
        template_id: uuid.UUID | None = None,
    ) -> Category:
        """Create a top-level (root) category.

        Args:
            name_i18n: Multilingual display name.
            slug: URL-safe identifier.
            sort_order: Display ordering among root categories.
            template_id: Optional FK to an AttributeTemplate.

        Returns:
            A new root Category with level=0.
        """
        _validate_slug(slug, "Category")
        if not name_i18n:
            raise ValueError("name_i18n must contain at least one language entry")
        _validate_i18n_values(name_i18n, "name_i18n")
        validate_i18n_completeness(name_i18n, "name_i18n")
        _validate_sort_order(sort_order, "Category")
        return cls(
            id=_generate_id(),
            parent_id=None,
            name_i18n=name_i18n,
            slug=slug,
            full_slug=slug,
            level=0,
            sort_order=sort_order,
            template_id=template_id,
            effective_template_id=template_id,
        )

    @classmethod
    def create_child(
        cls,
        name_i18n: dict[str, str],
        slug: str,
        parent: Category,
        sort_order: int = 0,
        template_id: uuid.UUID | None = None,
    ) -> Category:
        """Create a child category under the given parent.

        Args:
            name_i18n: Multilingual display name.
            slug: URL-safe identifier (unique within parent's children).
            parent: Parent category aggregate.
            sort_order: Display ordering among siblings.
            template_id: Optional FK to an AttributeTemplate.

        Returns:
            A new child Category with level = parent.level + 1.

        Raises:
            CategoryMaxDepthError: If the parent is already at max depth.
        """
        _validate_slug(slug, "Category")
        if not name_i18n:
            raise ValueError("name_i18n must contain at least one language entry")
        _validate_i18n_values(name_i18n, "name_i18n")
        validate_i18n_completeness(name_i18n, "name_i18n")
        _validate_sort_order(sort_order, "Category")
        if parent.level >= MAX_CATEGORY_DEPTH:
            raise CategoryMaxDepthError(
                max_depth=MAX_CATEGORY_DEPTH, current_level=parent.level
            )

        return cls(
            id=_generate_id(),
            parent_id=parent.id,
            name_i18n=name_i18n,
            slug=slug,
            full_slug=f"{parent.full_slug}/{slug}",
            level=parent.level + 1,
            sort_order=sort_order,
            template_id=template_id,
            effective_template_id=template_id or parent.effective_template_id,
        )

    _UPDATABLE_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "name_i18n",
            "slug",
            "sort_order",
            "template_id",
        }
    )

    def update(
        self,
        name_i18n: dict[str, str] | None = None,
        slug: str | None = None,
        sort_order: int | None = None,
        template_id: uuid.UUID | None = ...,  # type: ignore[assignment]
        parent_effective_template_id: uuid.UUID | None = ...,  # type: ignore[assignment]
    ) -> str | None:
        """Update category details and recompute full_slug if slug changed.

        Args:
            name_i18n: New multilingual name, or None to keep current.
            slug: New URL-safe slug, or None to keep current.
            sort_order: New sort position, or None to keep current.
            template_id: New template FK, None to clear, or ``...`` (default) to keep current.

        Returns:
            The old ``full_slug`` if slug was changed (caller must cascade
            to descendants), or None if slug was unchanged.
        """
        old_full_slug: str | None = None

        if name_i18n is not None:
            if not name_i18n:
                raise ValueError("name_i18n must contain at least one language entry")
            _validate_i18n_values(name_i18n, "name_i18n")
            validate_i18n_completeness(name_i18n, "name_i18n")
            self.name_i18n = name_i18n

        if sort_order is not None:
            _validate_sort_order(sort_order, "Category")
            self.sort_order = sort_order

        if template_id is not ...:
            self.template_id = template_id
            if template_id is not None:
                self.effective_template_id = template_id
            elif parent_effective_template_id is not ...:
                self.effective_template_id = parent_effective_template_id
            else:
                self.effective_template_id = None

        if slug is not None and slug != self.slug:
            _validate_slug(slug, "Category")
            old_full_slug = self.full_slug
            # Bypass the guard for controlled mutation via domain method
            object.__setattr__(self, "slug", slug)
            # Recompute own full_slug by replacing the last path segment
            if self.parent_id is None:
                self.full_slug = slug
            else:
                parts = self.full_slug.rsplit("/", 1)
                parent_prefix = parts[0] if len(parts) > 1 else ""
                self.full_slug = f"{parent_prefix}/{slug}" if parent_prefix else slug

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

    def set_effective_template_id(self, value: uuid.UUID | None) -> None:
        """Set the computed effective_template_id (used by propagation logic)."""
        self.effective_template_id = value
