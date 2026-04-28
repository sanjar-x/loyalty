"""Command handlers for ``ProviderAccount`` admin CRUD.

Backs the ``/admin/logistics/provider-accounts`` admin REST surface.
Each handler owns one transactional boundary via ``IUnitOfWork`` —
``ProviderAccount`` does not raise domain events so the UoW commit
just flushes the SQL transaction; ``register_aggregate`` is a no-op
that we still call for consistency with the rest of the module.

Hot-reload is **not** automatic: the in-memory ``IShippingProviderRegistry``
is constructed at app startup (Dishka APP scope) from the DB rows, so
mutations made through these handlers only take effect after either
(a) restarting the worker, or (b) hitting the
``POST /admin/logistics/provider-accounts/refresh`` endpoint, which
rebuilds the registry against the current DB state. Multi-worker
deploys must refresh every worker — pick whichever instance the
operator targets, then trigger a rolling restart for the rest.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.exc import IntegrityError

from src.modules.logistics.domain.interfaces import IProviderAccountRepository
from src.modules.logistics.domain.provider_account import ProviderAccount
from src.shared.exceptions import ConflictError, NotFoundError
from src.shared.interfaces.logger import ILogger
from src.shared.interfaces.uow import IUnitOfWork

# Postgres constraint name from the
# ``uq_provider_accounts_active_code`` partial unique index. Surfaced
# in ``IntegrityError.orig`` so we can distinguish the "duplicate active
# row" race from any other integrity failure.
_ACTIVE_PROVIDER_CONSTRAINT = "uq_provider_accounts_active_code"


def _is_active_provider_conflict(exc: IntegrityError) -> bool:
    """Did ``IntegrityError`` originate from the partial unique index?

    Catches the race where two concurrent Create/Activate calls passed
    their pre-check before either committed. asyncpg surfaces the
    constraint name in ``__cause__.constraint_name``; falling back to
    the raw error string keeps the handler robust across asyncpg versions.
    """
    cause = getattr(exc, "orig", None)
    constraint = getattr(cause, "constraint_name", None) if cause else None
    if constraint == _ACTIVE_PROVIDER_CONSTRAINT:
        return True
    return _ACTIVE_PROVIDER_CONSTRAINT in str(exc)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CreateProviderAccountCommand:
    provider_code: str
    name: str
    credentials: dict[str, Any]
    config: dict[str, Any] = field(default_factory=dict)
    is_active: bool = True


@dataclass(frozen=True)
class ProviderAccountResult:
    """Lightweight result DTO returned by every write handler."""

    account: ProviderAccount


class CreateProviderAccountHandler:
    """Create a new ``provider_accounts`` row.

    Rejects the create when an active account already exists for the
    same ``provider_code``: ``bootstrap_registry`` is single-active per
    provider, so a second active row would silently shadow the first.
    Operators must deactivate or delete the existing one first.
    """

    def __init__(
        self,
        repo: IProviderAccountRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._repo = repo
        self._uow = uow
        self._logger = logger.bind(handler="CreateProviderAccountHandler")

    async def handle(
        self, command: CreateProviderAccountCommand
    ) -> ProviderAccountResult:
        try:
            async with self._uow:
                existing = await self._repo.get_active_by_provider_code(
                    command.provider_code.strip().lower()
                )
                # Conflict rule mirrors the partial unique index: only the
                # combination "new is_active AND existing is_active" is
                # forbidden. Adding an inactive backup row alongside the
                # live one is fine — it's how operators stage a credential
                # rotation: insert inactive, deactivate live, activate
                # backup.
                if existing is not None and existing.is_active and command.is_active:
                    raise ConflictError(
                        message=(
                            f"Active provider account for "
                            f"{command.provider_code!r} already exists; "
                            "deactivate or delete it before creating "
                            "another active one."
                        ),
                        details={"existing_account_id": str(existing.id)},
                    )

                account = ProviderAccount.create(
                    provider_code=command.provider_code,
                    name=command.name,
                    credentials=command.credentials,
                    config=command.config,
                    is_active=command.is_active,
                )
                account = await self._repo.add(account)
                self._uow.register_aggregate(account)
                await self._uow.commit()
        except IntegrityError as exc:
            # Race-loser path: another concurrent Create/Activate slipped
            # past its own pre-check and committed first; the partial
            # unique index ``uq_provider_accounts_active_code`` catches us.
            if _is_active_provider_conflict(exc):
                raise ConflictError(
                    message=(
                        f"Active provider account for "
                        f"{command.provider_code!r} already exists "
                        "(concurrent admin write)."
                    ),
                ) from exc
            raise

        self._logger.info(
            "Provider account created",
            account_id=str(account.id),
            provider_code=account.provider_code,
        )
        return ProviderAccountResult(account=account)


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UpdateProviderAccountCommand:
    """Partial update — every field is optional.

    ``credentials`` (when provided) **replaces** the stored payload —
    we don't support shallow merges because nothing guarantees that
    leftover keys are still valid for the new key set.

    ``config`` is **shallow-merged** by default so operators can change
    a single setting (e.g. ``test_mode``) without re-supplying the rest.
    Pass ``replace_config=True`` for a destructive replacement.
    """

    account_id: uuid.UUID
    name: str | None = None
    credentials: dict[str, Any] | None = None
    config: dict[str, Any] | None = None
    replace_config: bool = False


class UpdateProviderAccountHandler:
    """Apply a partial update to an existing provider account."""

    def __init__(
        self,
        repo: IProviderAccountRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._repo = repo
        self._uow = uow
        self._logger = logger.bind(handler="UpdateProviderAccountHandler")

    async def handle(
        self, command: UpdateProviderAccountCommand
    ) -> ProviderAccountResult:
        async with self._uow:
            account = await self._repo.get_by_id(command.account_id)
            if account is None:
                raise NotFoundError(
                    message="Provider account not found",
                    details={"account_id": str(command.account_id)},
                )

            if command.name is not None:
                account.rename(command.name)
            if command.credentials is not None:
                account.replace_credentials(command.credentials)
            if command.config is not None:
                if command.replace_config:
                    account.replace_config(command.config)
                else:
                    account.merge_config(command.config)

            account = await self._repo.update(account)
            self._uow.register_aggregate(account)
            await self._uow.commit()

        self._logger.info(
            "Provider account updated",
            account_id=str(account.id),
            provider_code=account.provider_code,
        )
        return ProviderAccountResult(account=account)


# ---------------------------------------------------------------------------
# Activate / Deactivate
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SetProviderAccountActiveCommand:
    account_id: uuid.UUID
    is_active: bool


class SetProviderAccountActiveHandler:
    """Toggle the ``is_active`` flag on a provider account.

    Activating a second account for the same ``provider_code`` is
    rejected the same way ``Create`` rejects duplicates, for the same
    reason: ``bootstrap_registry`` only takes the first active row.
    """

    def __init__(
        self,
        repo: IProviderAccountRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._repo = repo
        self._uow = uow
        self._logger = logger.bind(handler="SetProviderAccountActiveHandler")

    async def handle(
        self, command: SetProviderAccountActiveCommand
    ) -> ProviderAccountResult:
        try:
            async with self._uow:
                account = await self._repo.get_by_id(command.account_id)
                if account is None:
                    raise NotFoundError(
                        message="Provider account not found",
                        details={"account_id": str(command.account_id)},
                    )

                if command.is_active and not account.is_active:
                    # ``get_active_by_provider_code`` filters by
                    # ``is_active = true`` so anything it returns is
                    # already a conflict — we can't be looking at our
                    # own row here because ``account`` is currently
                    # inactive (we just checked).
                    conflict = await self._repo.get_active_by_provider_code(
                        account.provider_code
                    )
                    if conflict is not None:
                        raise ConflictError(
                            message=(
                                f"Another active provider account exists for "
                                f"{account.provider_code!r}; deactivate it first."
                            ),
                            details={"conflicting_account_id": str(conflict.id)},
                        )
                    account.activate()
                elif not command.is_active and account.is_active:
                    account.deactivate()
                else:
                    # Idempotent — return the current state without flushing.
                    return ProviderAccountResult(account=account)

                account = await self._repo.update(account)
                self._uow.register_aggregate(account)
                await self._uow.commit()
        except IntegrityError as exc:
            if _is_active_provider_conflict(exc):
                raise ConflictError(
                    message=(
                        "Another active provider account exists for the same "
                        "provider_code (concurrent admin write)."
                    ),
                ) from exc
            raise

        self._logger.info(
            "Provider account active flag toggled",
            account_id=str(account.id),
            is_active=account.is_active,
        )
        return ProviderAccountResult(account=account)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DeleteProviderAccountCommand:
    account_id: uuid.UUID


class DeleteProviderAccountHandler:
    """Hard-delete a provider account row.

    Soft delete would just be ``is_active=false``; ``DELETE`` is meant
    to physically remove the row when an integration is retired or a
    seed-error needs cleaning. Returns silently when no row matched —
    the caller already confirmed the resource via ``GET``.
    """

    def __init__(
        self,
        repo: IProviderAccountRepository,
        uow: IUnitOfWork,
        logger: ILogger,
    ) -> None:
        self._repo = repo
        self._uow = uow
        self._logger = logger.bind(handler="DeleteProviderAccountHandler")

    async def handle(self, command: DeleteProviderAccountCommand) -> bool:
        async with self._uow:
            removed = await self._repo.delete(command.account_id)
            await self._uow.commit()
        if removed:
            self._logger.info(
                "Provider account deleted",
                account_id=str(command.account_id),
            )
        return removed
