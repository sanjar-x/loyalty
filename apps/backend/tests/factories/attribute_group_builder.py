# tests/factories/attribute_group_builder.py
"""Fluent Builder for the AttributeGroup domain entity."""

from __future__ import annotations

import uuid

from src.modules.catalog.domain.entities import AttributeGroup


class AttributeGroupBuilder:
    """Fluent builder for AttributeGroup entities with sensible defaults.

    Usage:
        group = AttributeGroupBuilder().build()
        group = (
            AttributeGroupBuilder()
            .with_code("physical")
            .with_name_i18n({"en": "Physical", "ru": "Физические"})
            .build()
        )
    """

    def __init__(self) -> None:
        self._code: str | None = None
        self._name_i18n: dict[str, str] = {
            "en": "Test Group",
            "ru": "Тестовая группа",
        }
        self._sort_order: int = 0

    def with_code(self, code: str) -> AttributeGroupBuilder:
        self._code = code
        return self

    def with_name_i18n(self, name_i18n: dict[str, str]) -> AttributeGroupBuilder:
        self._name_i18n = name_i18n
        return self

    def with_sort_order(self, sort_order: int) -> AttributeGroupBuilder:
        self._sort_order = sort_order
        return self

    def build(self) -> AttributeGroup:
        """Build an AttributeGroup via AttributeGroup.create() factory method."""
        code = self._code or f"group-{uuid.uuid4().hex[:6]}"
        return AttributeGroup.create(
            code=code,
            name_i18n=self._name_i18n,
            sort_order=self._sort_order,
        )
