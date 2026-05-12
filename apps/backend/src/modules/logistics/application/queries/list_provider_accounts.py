"""Query handlers: list / get provider accounts (admin read side).

CQRS read side — reads ORM directly via the session. The bootstrap
path also reads the same table directly, but this handler returns
``ProviderAccountReadModel`` DTOs with credential fingerprinting so
secrets never leave the backend in clear text via the admin REST.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.logistics.infrastructure.models import ProviderAccountModel
from src.shared.exceptions import NotFoundError

# ---------------------------------------------------------------------------
# Read model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CredentialFingerprint:
    """Per-key fingerprint of stored credentials.

    The admin UI / API never receives raw credential values: each key's
    value is replaced by a deterministic fingerprint (first 8 hex chars
    of its SHA-256 digest) plus the value's length. Operators can verify
    "yes that's the right key" without leaking it. Empty values render
    as ``length=0`` and a stable fingerprint of the empty string so
    "missing" is visually distinct from "set but masked".
    """

    fingerprint: str
    length: int


def _fingerprint(raw: Any) -> CredentialFingerprint:
    text = "" if raw is None else str(raw)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
    return CredentialFingerprint(fingerprint=digest, length=len(text))


@dataclass(frozen=True)
class ProviderAccountReadModel:
    id: uuid.UUID
    provider_code: str
    name: str
    is_active: bool
    credential_fingerprints: dict[str, CredentialFingerprint]
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime


def _to_read_model(orm: ProviderAccountModel) -> ProviderAccountReadModel:
    creds = orm.credentials_json or {}
    return ProviderAccountReadModel(
        id=orm.id,
        provider_code=orm.provider_code,
        name=orm.name,
        is_active=bool(orm.is_active),
        credential_fingerprints={k: _fingerprint(v) for k, v in creds.items()},
        config=dict(orm.config_json or {}),
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ListProviderAccountsQuery:
    provider_code: str | None = None
    only_active: bool = False


@dataclass(frozen=True)
class ListProviderAccountsResult:
    items: list[ProviderAccountReadModel] = field(default_factory=list)


class ListProviderAccountsHandler:
    """List provider accounts with optional ``provider_code`` / active filters."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(
        self, query: ListProviderAccountsQuery
    ) -> ListProviderAccountsResult:
        stmt = select(ProviderAccountModel).order_by(
            ProviderAccountModel.provider_code, ProviderAccountModel.created_at
        )
        if query.provider_code is not None:
            stmt = stmt.where(
                ProviderAccountModel.provider_code
                == query.provider_code.strip().lower()
            )
        if query.only_active:
            stmt = stmt.where(ProviderAccountModel.is_active.is_(True))

        result = await self._session.execute(stmt)
        items = [_to_read_model(orm) for orm in result.scalars().all()]
        return ListProviderAccountsResult(items=items)


# ---------------------------------------------------------------------------
# Get
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GetProviderAccountQuery:
    account_id: uuid.UUID


class GetProviderAccountHandler:
    """Fetch a single provider account by id; raises ``NotFoundError`` when absent."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def handle(self, query: GetProviderAccountQuery) -> ProviderAccountReadModel:
        orm = await self._session.get(ProviderAccountModel, query.account_id)
        if orm is None:
            raise NotFoundError(
                message="Provider account not found",
                details={"account_id": str(query.account_id)},
            )
        return _to_read_model(orm)
