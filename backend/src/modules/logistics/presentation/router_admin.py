"""Admin REST router for logistics provider accounts.

Surface: ``/admin/logistics/provider-accounts`` — full CRUD plus an
explicit refresh endpoint that rebuilds the in-memory provider registry
on the worker that serves the request. All endpoints require the
``logistics:admin`` permission, which is granted only to the ``admin``
system role (not to ``manager``) — provider credentials are sensitive.

Security note: ``credentials`` are accepted in plaintext on the request
body but **never returned** in responses. Read models replace each
credential value with a ``CredentialFingerprint`` (SHA-256 prefix +
length) so operators can verify identity without leaking the secret.
"""

from __future__ import annotations

import uuid

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Query, status

from src.modules.identity.presentation.dependencies import RequirePermission
from src.modules.logistics.application.commands.manage_provider_accounts import (
    CreateProviderAccountCommand,
    CreateProviderAccountHandler,
    DeleteProviderAccountCommand,
    DeleteProviderAccountHandler,
    SetProviderAccountActiveCommand,
    SetProviderAccountActiveHandler,
    UpdateProviderAccountCommand,
    UpdateProviderAccountHandler,
)
from src.modules.logistics.application.queries.list_provider_accounts import (
    GetProviderAccountHandler,
    GetProviderAccountQuery,
    ListProviderAccountsHandler,
    ListProviderAccountsQuery,
    ProviderAccountReadModel,
)
from src.modules.logistics.infrastructure.services.registry_refresh import (
    ProviderRegistryRefresher,
)
from src.modules.logistics.presentation.schemas_admin import (
    CreateProviderAccountRequest,
    CredentialFingerprintSchema,
    ProviderAccountListResponse,
    ProviderAccountResponse,
    RefreshRegistryResponse,
    SetProviderAccountActiveRequest,
    UpdateProviderAccountRequest,
)
from src.shared.exceptions import NotFoundError

_LOGISTICS_ADMIN = [Depends(RequirePermission(codename="logistics:admin"))]

logistics_admin_router = APIRouter(
    prefix="/admin/logistics/provider-accounts",
    tags=["Logistics Admin"],
    route_class=DishkaRoute,
    dependencies=_LOGISTICS_ADMIN,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_model_to_response(rm: ProviderAccountReadModel) -> ProviderAccountResponse:
    """Convert the application-layer read model to the API response shape.

    Pydantic's ``ConfigDict(from_attributes=True)`` would handle this
    almost automatically, but ``CredentialFingerprint`` is a frozen
    dataclass and the inline conversion makes the contract explicit
    when reviewing routes side-by-side with their schemas.
    """
    return ProviderAccountResponse(
        id=rm.id,
        provider_code=rm.provider_code,
        name=rm.name,
        is_active=rm.is_active,
        credential_fingerprints={
            k: CredentialFingerprintSchema(fingerprint=v.fingerprint, length=v.length)
            for k, v in rm.credential_fingerprints.items()
        },
        config=rm.config,
        created_at=rm.created_at,
        updated_at=rm.updated_at,
    )


async def _get_read_model(
    handler: GetProviderAccountHandler, account_id: uuid.UUID
) -> ProviderAccountReadModel:
    return await handler.handle(GetProviderAccountQuery(account_id=account_id))


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@logistics_admin_router.get(
    "",
    response_model=ProviderAccountListResponse,
    summary="List provider accounts",
)
async def list_provider_accounts(
    handler: FromDishka[ListProviderAccountsHandler],
    provider_code: str | None = Query(default=None),
    only_active: bool = Query(default=False),
) -> ProviderAccountListResponse:
    result = await handler.handle(
        ListProviderAccountsQuery(
            provider_code=provider_code,
            only_active=only_active,
        )
    )
    return ProviderAccountListResponse(
        items=[_read_model_to_response(item) for item in result.items]
    )


@logistics_admin_router.get(
    "/{account_id}",
    response_model=ProviderAccountResponse,
    summary="Get a provider account",
)
async def get_provider_account(
    account_id: uuid.UUID,
    handler: FromDishka[GetProviderAccountHandler],
) -> ProviderAccountResponse:
    rm = await _get_read_model(handler, account_id)
    return _read_model_to_response(rm)


@logistics_admin_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ProviderAccountResponse,
    summary="Create a provider account",
)
async def create_provider_account(
    request: CreateProviderAccountRequest,
    create_handler: FromDishka[CreateProviderAccountHandler],
    get_handler: FromDishka[GetProviderAccountHandler],
) -> ProviderAccountResponse:
    result = await create_handler.handle(
        CreateProviderAccountCommand(
            provider_code=request.provider_code,
            name=request.name,
            credentials=request.credentials,
            config=request.config,
            is_active=request.is_active,
        )
    )
    # Round-trip through the read model so the response carries
    # fingerprints rather than raw credentials.
    rm = await _get_read_model(get_handler, result.account.id)
    return _read_model_to_response(rm)


@logistics_admin_router.put(
    "/{account_id}",
    response_model=ProviderAccountResponse,
    summary="Update a provider account (partial)",
)
async def update_provider_account(
    account_id: uuid.UUID,
    request: UpdateProviderAccountRequest,
    update_handler: FromDishka[UpdateProviderAccountHandler],
    get_handler: FromDishka[GetProviderAccountHandler],
) -> ProviderAccountResponse:
    await update_handler.handle(
        UpdateProviderAccountCommand(
            account_id=account_id,
            name=request.name,
            credentials=request.credentials,
            config=request.config,
            replace_config=request.replace_config,
        )
    )
    rm = await _get_read_model(get_handler, account_id)
    return _read_model_to_response(rm)


@logistics_admin_router.post(
    "/{account_id}/active",
    response_model=ProviderAccountResponse,
    summary="Activate or deactivate a provider account",
)
async def set_provider_account_active(
    account_id: uuid.UUID,
    request: SetProviderAccountActiveRequest,
    set_active_handler: FromDishka[SetProviderAccountActiveHandler],
    get_handler: FromDishka[GetProviderAccountHandler],
) -> ProviderAccountResponse:
    await set_active_handler.handle(
        SetProviderAccountActiveCommand(
            account_id=account_id,
            is_active=request.is_active,
        )
    )
    rm = await _get_read_model(get_handler, account_id)
    return _read_model_to_response(rm)


@logistics_admin_router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a provider account",
)
async def delete_provider_account(
    account_id: uuid.UUID,
    handler: FromDishka[DeleteProviderAccountHandler],
) -> None:
    removed = await handler.handle(DeleteProviderAccountCommand(account_id=account_id))
    if not removed:
        raise NotFoundError(
            message="Provider account not found",
            details={"account_id": str(account_id)},
        )


# ---------------------------------------------------------------------------
# Registry refresh
# ---------------------------------------------------------------------------


@logistics_admin_router.post(
    "/refresh",
    response_model=RefreshRegistryResponse,
    summary="Refresh the in-memory provider registry on this worker",
)
async def refresh_provider_registry(
    refresher: FromDishka[ProviderRegistryRefresher],
) -> RefreshRegistryResponse:
    result = await refresher.refresh()
    return RefreshRegistryResponse(
        registered_provider_codes=list(result.registered_provider_codes),
    )
