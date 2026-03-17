# tests/factories/builders.py
"""Fluent Test Data Builders for complex aggregate construction."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from src.modules.catalog.domain.entities import Category
from src.modules.identity.domain.entities import Role, Session


class RoleBuilder:
    """Fluent builder for Role entities with sensible defaults."""

    def __init__(self) -> None:
        self._id = uuid.uuid4()
        self._name = "test-role"
        self._description: str | None = "Test role"
        self._is_system = False

    def with_name(self, name: str) -> RoleBuilder:
        self._name = name
        return self

    def with_description(self, description: str | None) -> RoleBuilder:
        self._description = description
        return self

    def as_system_role(self) -> RoleBuilder:
        self._is_system = True
        return self

    def build(self) -> Role:
        return Role(
            id=self._id,
            name=self._name,
            description=self._description,
            is_system=self._is_system,
        )


class SessionBuilder:
    """Fluent builder for Session entities."""

    def __init__(self) -> None:
        self._identity_id = uuid.uuid4()
        self._refresh_token = f"refresh-{uuid.uuid4().hex}"
        self._ip_address = "127.0.0.1"
        self._user_agent = "TestAgent/1.0"
        self._role_ids: list[uuid.UUID] = []
        self._expires_days = 30
        self._is_revoked = False
        self._expired = False

    def with_identity(self, identity_id: uuid.UUID) -> SessionBuilder:
        self._identity_id = identity_id
        return self

    def with_roles(self, role_ids: list[uuid.UUID]) -> SessionBuilder:
        self._role_ids = role_ids
        return self

    def expired(self) -> SessionBuilder:
        self._expired = True
        return self

    def revoked(self) -> SessionBuilder:
        self._is_revoked = True
        return self

    def build(self) -> tuple[Session, str]:
        """Returns (session, raw_refresh_token)."""
        session = Session.create(
            identity_id=self._identity_id,
            refresh_token=self._refresh_token,
            ip_address=self._ip_address,
            user_agent=self._user_agent,
            role_ids=self._role_ids,
            expires_days=self._expires_days,
        )
        if self._expired:
            session.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        if self._is_revoked:
            session.revoke()
        return session, self._refresh_token


class CategoryBuilder:
    """Fluent builder for Category tree construction."""

    def __init__(self) -> None:
        self._name = "Test Category"
        self._slug: str | None = None
        self._sort_order = 0
        self._parent: Category | None = None

    def with_name(self, name: str) -> CategoryBuilder:
        self._name = name
        return self

    def with_slug(self, slug: str) -> CategoryBuilder:
        self._slug = slug
        return self

    def under(self, parent: Category) -> CategoryBuilder:
        self._parent = parent
        return self

    def build(self) -> Category:
        slug = (
            self._slug
            or f"{self._name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}"
        )
        if self._parent is None:
            return Category.create_root(
                name=self._name, slug=slug, sort_order=self._sort_order
            )
        return Category.create_child(
            name=self._name, slug=slug, parent=self._parent, sort_order=self._sort_order
        )
