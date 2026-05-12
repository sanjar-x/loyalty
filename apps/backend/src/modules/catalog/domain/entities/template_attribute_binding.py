"""
TemplateAttributeBinding aggregate root entity.

Binding between a template and an attribute with governance settings.
Controls which attributes apply to a template, their display order,
requirement level, and per-template filter settings.
Part of the domain layer -- zero infrastructure imports.
"""

import uuid
from typing import Any, ClassVar

from attr import dataclass

from src.modules.catalog.domain.value_objects import RequirementLevel
from src.shared.interfaces.entities import AggregateRoot

from ._common import _generate_id, _validate_filter_settings, _validate_sort_order


@dataclass
class TemplateAttributeBinding(AggregateRoot):
    """Binding between a template and an attribute with governance settings.

    Controls which attributes apply to a template, their display order,
    requirement level, and per-template filter settings.
    Standalone aggregate with its own event lifecycle.

    Attributes:
        id: Unique binding identifier.
        template_id: FK to the AttributeTemplate aggregate.
        attribute_id: FK to the Attribute aggregate.
        sort_order: Display ordering of the attribute within the template.
        requirement_level: Required / recommended / optional.
        filter_settings: Optional per-template filter configuration.
    """

    id: uuid.UUID
    template_id: uuid.UUID
    attribute_id: uuid.UUID
    sort_order: int
    requirement_level: RequirementLevel
    filter_settings: dict[str, Any] | None
    """Opaque frontend configuration for filter UI rendering.

    Stored as-is, never interpreted by the backend. Passed through to
    storefront filter responses for frontend consumption.

    Expected shape (to be formalized when frontend is implemented)::

        {
            "widget": "range_slider" | "checkbox_list" | "color_swatch",
            "min": number | null,
            "max": number | null,
            "step": number | null,
            "unit": string | null,
            "collapsed": bool
        }

    Size limit: enforced by ``BoundedJsonDict`` schema (max 10 KB, max depth 4).
    """

    @classmethod
    def create(
        cls,
        *,
        template_id: uuid.UUID,
        attribute_id: uuid.UUID,
        sort_order: int = 0,
        requirement_level: RequirementLevel | None = None,
        filter_settings: dict[str, Any] | None = None,
        binding_id: uuid.UUID | None = None,
    ) -> TemplateAttributeBinding:
        """Factory method to construct a new TemplateAttributeBinding."""
        _validate_sort_order(sort_order, "TemplateAttributeBinding")
        _validate_filter_settings(filter_settings)
        return cls(
            id=binding_id or _generate_id(),
            template_id=template_id,
            attribute_id=attribute_id,
            sort_order=sort_order,
            requirement_level=RequirementLevel.OPTIONAL
            if requirement_level is None
            else requirement_level,
            filter_settings=filter_settings,
        )

    _UPDATABLE_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {
            "sort_order",
            "requirement_level",
            "filter_settings",
        }
    )

    def update(self, **kwargs: Any) -> None:
        """Update mutable binding fields. template_id and attribute_id are immutable."""
        unknown = set(kwargs) - self._UPDATABLE_FIELDS
        if unknown:
            raise TypeError(f"Cannot update immutable/unknown fields: {unknown}")

        if "sort_order" in kwargs and kwargs["sort_order"] is not None:
            _validate_sort_order(kwargs["sort_order"], "TemplateAttributeBinding")
            self.sort_order = kwargs["sort_order"]
        if "requirement_level" in kwargs and kwargs["requirement_level"] is not None:
            self.requirement_level = kwargs["requirement_level"]
        if "filter_settings" in kwargs:
            _validate_filter_settings(kwargs["filter_settings"])
            self.filter_settings = kwargs["filter_settings"]
