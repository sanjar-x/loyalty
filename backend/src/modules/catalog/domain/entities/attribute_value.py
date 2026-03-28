"""
AttributeValue child entity for dictionary attributes.

Value option for a dictionary attribute (e.g. "Red", "42", "Cotton").
Not an aggregate root -- events are emitted through the parent
Attribute aggregate in command handlers.
Part of the domain layer -- zero infrastructure imports.
"""

import uuid
from typing import Any, ClassVar

from attr import dataclass

from src.modules.catalog.domain.value_objects import validate_i18n_completeness

from ._common import (
    _generate_id,
    _validate_i18n_values,
    _validate_slug,
    _validate_sort_order,
)


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
    value_group: str | None
    sort_order: int
    is_active: bool = True

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
        is_active: bool = True,
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
            is_active: Whether the value is active (default: True).
            value_id: Optional pre-generated UUID.

        Returns:
            A new AttributeValue instance.

        Raises:
            ValueError: If value_i18n is empty.
        """
        if not value_i18n:
            raise ValueError("value_i18n must contain at least one language entry")
        _validate_i18n_values(value_i18n, "value_i18n")
        validate_i18n_completeness(value_i18n, "value_i18n")
        _validate_slug(slug, "AttributeValue")
        _validate_sort_order(sort_order, "AttributeValue")

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
            is_active=is_active,
        )

    _UPDATABLE_FIELDS: ClassVar[frozenset[str]] = frozenset({
        "value_i18n",
        "search_aliases",
        "meta_data",
        "value_group",
        "sort_order",
        "is_active",
    })

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
                _validate_i18n_values(value_i18n, "value_i18n")
                validate_i18n_completeness(value_i18n, "value_i18n")
                self.value_i18n = value_i18n

        if "search_aliases" in kwargs and kwargs["search_aliases"] is not None:
            self.search_aliases = kwargs["search_aliases"]

        if "meta_data" in kwargs and kwargs["meta_data"] is not None:
            self.meta_data = kwargs["meta_data"]

        if "value_group" in kwargs:
            self.value_group = kwargs["value_group"]  # nullable -- None clears it

        if "sort_order" in kwargs and kwargs["sort_order"] is not None:
            _validate_sort_order(kwargs["sort_order"], "AttributeValue")
            self.sort_order = kwargs["sort_order"]

        if "is_active" in kwargs and kwargs["is_active"] is not None:
            self.is_active = kwargs["is_active"]
