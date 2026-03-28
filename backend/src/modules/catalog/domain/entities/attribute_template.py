"""
AttributeTemplate aggregate root entity.

Defines a flat template of attributes for products assigned to categories
referencing this template.
Part of the domain layer -- zero infrastructure imports.
"""

import uuid
from typing import Any, ClassVar

from attr import dataclass

from src.modules.catalog.domain.exceptions import (
    AttributeTemplateHasCategoryReferencesError,
)
from src.modules.catalog.domain.value_objects import validate_i18n_completeness
from src.shared.interfaces.entities import AggregateRoot

from ._common import _generate_id, _validate_i18n_values, _validate_sort_order

# ---------------------------------------------------------------------------
# DDD-01: Guarded fields set -- fields that may only be changed through
# explicit domain methods, never by direct attribute assignment.
# ---------------------------------------------------------------------------

_TEMPLATE_GUARDED_FIELDS: frozenset[str] = frozenset({"code"})


@dataclass
class AttributeTemplate(AggregateRoot):
    """Standalone aggregate defining a flat template of attributes for products.

    Each template is a top-level template that governs which attributes apply
    to products assigned to categories referencing this template.

    Attributes:
        id: Unique template identifier.
        code: Machine-readable code, globally unique. Immutable.
        name_i18n: Multilingual display name.
        description_i18n: Multilingual description.
        sort_order: Display ordering among templates.
    """

    id: uuid.UUID
    code: str
    name_i18n: dict[str, str]
    description_i18n: dict[str, str]
    sort_order: int

    _UPDATABLE_FIELDS: ClassVar[frozenset[str]] = frozenset({
        "name_i18n",
        "description_i18n",
        "sort_order",
    })

    def __setattr__(self, name: str, value: object) -> None:
        if name in _TEMPLATE_GUARDED_FIELDS and getattr(
            self, "_AttributeTemplate__initialized", False
        ):
            raise AttributeError(
                f"Cannot set '{name}' directly on AttributeTemplate. "
                f"Use the appropriate method instead."
            )
        super().__setattr__(name, value)

    def __attrs_post_init__(self) -> None:
        super().__attrs_post_init__()
        object.__setattr__(self, "_AttributeTemplate__initialized", True)

    @classmethod
    def create(
        cls,
        *,
        code: str,
        name_i18n: dict[str, str],
        description_i18n: dict[str, str] | None = None,
        sort_order: int = 0,
    ) -> AttributeTemplate:
        """Create a new attribute template (flat template)."""
        if not name_i18n:
            raise ValueError("name_i18n must contain at least one entry")
        _validate_i18n_values(name_i18n, "name_i18n")
        validate_i18n_completeness(name_i18n, "name_i18n")
        _validate_sort_order(sort_order, "AttributeTemplate")
        return cls(
            id=_generate_id(),
            code=code,
            name_i18n=name_i18n,
            description_i18n=description_i18n or {},
            sort_order=sort_order,
        )

    def update(self, **kwargs: Any) -> None:
        """Update mutable template fields.

        Only fields in ``_UPDATABLE_FIELDS`` are accepted.

        Raises:
            TypeError: If an unknown field name is passed.
        """
        unknown = set(kwargs) - self._UPDATABLE_FIELDS
        if unknown:
            raise TypeError(f"Cannot update immutable/unknown fields: {unknown}")

        if "name_i18n" in kwargs and kwargs["name_i18n"] is not None:
            if not kwargs["name_i18n"]:
                raise ValueError("name_i18n must contain at least one entry")
            _validate_i18n_values(kwargs["name_i18n"], "name_i18n")
            validate_i18n_completeness(kwargs["name_i18n"], "name_i18n")
            self.name_i18n = kwargs["name_i18n"]
        if "description_i18n" in kwargs:
            self.description_i18n = kwargs["description_i18n"] or {}
        if "sort_order" in kwargs and kwargs["sort_order"] is not None:
            _validate_sort_order(kwargs["sort_order"], "AttributeTemplate")
            self.sort_order = kwargs["sort_order"]

    def validate_deletable(self, *, has_category_refs: bool) -> None:
        """Validate that this template can be safely deleted.

        Raises:
            AttributeTemplateHasCategoryReferencesError: If categories reference it.
        """
        if has_category_refs:
            raise AttributeTemplateHasCategoryReferencesError(template_id=self.id)
