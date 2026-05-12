"""Provider account aggregate — credentials + config for one logistics carrier.

Backs the ``provider_accounts`` table. Stored as a simple aggregate without
domain events: account state is configuration, not business behaviour, so
nothing downstream subscribes to changes. Mutations are recorded only via
``updated_at`` (set by the ORM ``onupdate`` clock).

Credentials and config are opaque ``dict[str, Any]`` payloads — the shape is
provider-specific and validated by the matching factory at registry
bootstrap time, not by this entity. The aggregate itself enforces only the
small set of invariants common to every provider:

* ``provider_code`` non-empty, lowercase, max 50 chars (matches the ORM
  column constraint).
* ``name`` non-empty, max 255 chars.
* ``credentials`` non-empty dict — a row with empty credentials would
  crash ``bootstrap_registry`` on the next app start.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import attrs

from src.modules.logistics.domain.value_objects import ProviderCode
from src.shared.exceptions import ValidationError
from src.shared.interfaces.entities import AggregateRoot

_MAX_PROVIDER_CODE = 50
_MAX_NAME = 255


def _validate_provider_code(value: str) -> str:
    code = (value or "").strip().lower()
    if not code:
        raise ValidationError("provider_code must be non-empty")
    if len(code) > _MAX_PROVIDER_CODE:
        raise ValidationError(f"provider_code length must be <= {_MAX_PROVIDER_CODE}")
    return code


def _validate_name(value: str) -> str:
    name = (value or "").strip()
    if not name:
        raise ValidationError("name must be non-empty")
    if len(name) > _MAX_NAME:
        raise ValidationError(f"name length must be <= {_MAX_NAME}")
    return name


def _validate_credentials(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or not value:
        raise ValidationError("credentials must be a non-empty dict")
    return dict(value)


@attrs.define
class ProviderAccount(AggregateRoot):
    """Logistics provider credentials + configuration aggregate."""

    id: uuid.UUID
    provider_code: ProviderCode
    name: str
    is_active: bool
    credentials: dict[str, Any]
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        provider_code: str,
        name: str,
        credentials: dict[str, Any],
        config: dict[str, Any] | None = None,
        is_active: bool = True,
        account_id: uuid.UUID | None = None,
    ) -> ProviderAccount:
        now = datetime.now(UTC)
        return cls(
            id=account_id or uuid.uuid4(),
            provider_code=_validate_provider_code(provider_code),
            name=_validate_name(name),
            is_active=is_active,
            credentials=_validate_credentials(credentials),
            config=dict(config or {}),
            created_at=now,
            updated_at=now,
        )

    def rename(self, new_name: str) -> None:
        self.name = _validate_name(new_name)
        self.updated_at = datetime.now(UTC)

    def replace_credentials(self, credentials: dict[str, Any]) -> None:
        self.credentials = _validate_credentials(credentials)
        self.updated_at = datetime.now(UTC)

    def merge_config(self, partial: dict[str, Any]) -> None:
        if not isinstance(partial, dict):
            raise ValidationError("config patch must be a dict")
        self.config = {**self.config, **partial}
        self.updated_at = datetime.now(UTC)

    def replace_config(self, config: dict[str, Any]) -> None:
        if not isinstance(config, dict):
            raise ValidationError("config must be a dict")
        self.config = dict(config)
        self.updated_at = datetime.now(UTC)

    def activate(self) -> None:
        if not self.is_active:
            self.is_active = True
            self.updated_at = datetime.now(UTC)

    def deactivate(self) -> None:
        if self.is_active:
            self.is_active = False
            self.updated_at = datetime.now(UTC)
