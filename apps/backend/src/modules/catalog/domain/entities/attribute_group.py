"""
AttributeGroup aggregate root entity.

Groups provide visual and semantic grouping of attributes in the admin UI
and on the product card (e.g. "Physical characteristics", "Technical",
"Marketing"). The "general" group always exists and cannot be deleted.
Part of the domain layer -- zero infrastructure imports.
"""

import uuid

from attr import dataclass

from src.modules.catalog.domain.value_objects import validate_i18n_completeness
from src.shared.interfaces.entities import AggregateRoot

from ._common import _generate_id, _validate_i18n_values, _validate_sort_order

# ---------------------------------------------------------------------------
# DDD-01: Guarded fields set -- fields that may only be changed through
# explicit domain methods, never by direct attribute assignment.
# ---------------------------------------------------------------------------

_ATTRIBUTE_GROUP_GUARDED_FIELDS: frozenset[str] = frozenset({"code"})


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

    # DDD-01: guard code against direct mutation
    def __setattr__(self, name: str, value: object) -> None:
        if name in _ATTRIBUTE_GROUP_GUARDED_FIELDS and getattr(
            self, "_AttributeGroup__initialized", False
        ):
            raise AttributeError(f"Cannot set '{name}' directly on AttributeGroup.")
        super().__setattr__(name, value)

    def __attrs_post_init__(self) -> None:
        super().__attrs_post_init__()
        object.__setattr__(self, "_AttributeGroup__initialized", True)

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
        _validate_i18n_values(name_i18n, "name_i18n")
        validate_i18n_completeness(name_i18n, "name_i18n")
        _validate_sort_order(sort_order, "AttributeGroup")

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
            _validate_i18n_values(name_i18n, "name_i18n")
            validate_i18n_completeness(name_i18n, "name_i18n")
            self.name_i18n = name_i18n

        if sort_order is not None:
            _validate_sort_order(sort_order, "AttributeGroup")
            self.sort_order = sort_order
