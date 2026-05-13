"""
Attribute aggregate root entity -- a product characteristic definition.

An attribute describes a single product property (e.g. "Color",
"Screen Size", "Material"). It carries metadata about how it should
be stored (data type), rendered (UI type), searched, filtered, and
compared.
Part of the domain layer -- zero infrastructure imports.
"""

import uuid
from typing import Any, ClassVar

from attr import dataclass, field

from src.modules.catalog.domain.value_objects import (
    DEFAULT_SEARCH_WEIGHT,
    MAX_SEARCH_WEIGHT,
    MIN_SEARCH_WEIGHT,
    AttributeDataType,
    AttributeLevel,
    AttributeUIType,
    BehaviorFlags,
    validate_i18n_completeness,
    validate_validation_rules,
)
from src.shared.interfaces.entities import AggregateRoot

from ._common import _generate_id, _validate_i18n_values, _validate_slug

# ---------------------------------------------------------------------------
# DDD-01: Guarded fields set -- fields that may only be changed through
# explicit domain methods, never by direct attribute assignment.
# ---------------------------------------------------------------------------

_ATTRIBUTE_GUARDED_FIELDS: frozenset[str] = frozenset({"code", "slug"})


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

    def __setattr__(self, name: str, value: object) -> None:
        if name in _ATTRIBUTE_GUARDED_FIELDS and getattr(
            self, "_Attribute__initialized", False
        ):
            raise AttributeError(
                f"Cannot set '{name}' directly on Attribute. "
                f"Code and slug are immutable after creation."
            )
        super().__setattr__(name, value)

    def __attrs_post_init__(self) -> None:
        super().__attrs_post_init__()
        object.__setattr__(self, "_Attribute__initialized", True)

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
        group_id: uuid.UUID | None,
        description_i18n: dict[str, str] | None = None,
        level: AttributeLevel = AttributeLevel.PRODUCT,
        is_filterable: bool = False,
        is_searchable: bool = False,
        search_weight: int = DEFAULT_SEARCH_WEIGHT,
        is_comparable: bool = False,
        is_visible_on_card: bool = False,
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
        _validate_i18n_values(name_i18n, "name_i18n")
        validate_i18n_completeness(name_i18n, "name_i18n")

        if behavior is None:
            # Build from individual flags; BehaviorFlags validates search_weight
            behavior = BehaviorFlags(
                is_filterable=is_filterable,
                is_searchable=is_searchable,
                search_weight=search_weight,
                is_comparable=is_comparable,
                is_visible_on_card=is_visible_on_card,
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
                _validate_i18n_values(name_i18n, "name_i18n")
                validate_i18n_completeness(name_i18n, "name_i18n")
                self.name_i18n = name_i18n

        if "description_i18n" in kwargs:
            desc = kwargs["description_i18n"] or {}
            if desc:
                _validate_i18n_values(desc, "description_i18n")
            self.description_i18n = desc

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
                self.behavior = BehaviorFlags(
                    is_filterable=bool(
                        flag_updates.get("is_filterable", self.behavior.is_filterable)
                    ),
                    is_searchable=bool(
                        flag_updates.get("is_searchable", self.behavior.is_searchable)
                    ),
                    search_weight=int(
                        flag_updates.get("search_weight", self.behavior.search_weight)
                    ),
                    is_comparable=bool(
                        flag_updates.get("is_comparable", self.behavior.is_comparable)
                    ),
                    is_visible_on_card=bool(
                        flag_updates.get(
                            "is_visible_on_card", self.behavior.is_visible_on_card
                        )
                    ),
                )

        if "validation_rules" in kwargs:
            validation_rules = kwargs["validation_rules"]
            if validation_rules is not None:
                validate_validation_rules(self.data_type, validation_rules)
            self.validation_rules = validation_rules  # nullable -- None clears it
