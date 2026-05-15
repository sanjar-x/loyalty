"""
Phase-3/4 regression tests for ``CdekAdminService`` — the per-request
facade behind the ``/admin/logistics/cdek`` router.

``from_account`` must build a *configured* service only from an active
CDEK account with usable credentials; everything else (no account,
inactive, non-CDEK, malformed creds) yields an *unconfigured* service
whose operations raise ``ProviderUnavailableError`` instead of crashing
with an ``AttributeError``.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.modules.logistics.domain.exceptions import ProviderUnavailableError
from src.modules.logistics.domain.provider_account import ProviderAccount
from src.modules.logistics.infrastructure.providers.cdek.admin_service import (
    CdekAdminService,
)

pytestmark = pytest.mark.unit


def _cdek_account(
    *,
    is_active: bool = True,
    credentials: dict[str, Any] | None = None,
    provider_code: str = "cdek",
) -> ProviderAccount:
    return ProviderAccount.create(
        provider_code=provider_code,
        name="CDEK account",
        credentials=credentials or {"client_id": "cid", "client_secret": "secret"},
        config={"test_mode": True},
        is_active=is_active,
    )


class TestFromAccount:
    def test_active_cdek_account_is_configured(self) -> None:
        service = CdekAdminService.from_account(_cdek_account())
        assert service.is_configured is True

    def test_none_account_is_unconfigured(self) -> None:
        assert CdekAdminService.from_account(None).is_configured is False

    def test_inactive_account_is_unconfigured(self) -> None:
        service = CdekAdminService.from_account(_cdek_account(is_active=False))
        assert service.is_configured is False

    def test_non_cdek_account_is_unconfigured(self) -> None:
        service = CdekAdminService.from_account(
            _cdek_account(provider_code="yandex_delivery")
        )
        assert service.is_configured is False

    def test_malformed_credentials_is_unconfigured(self) -> None:
        # Non-empty dict (passes ProviderAccount validation) but missing
        # client_id / client_secret — _build_client raises KeyError,
        # which from_account swallows into an unconfigured service.
        service = CdekAdminService.from_account(
            _cdek_account(credentials={"unexpected": "value"})
        )
        assert service.is_configured is False


class TestUnconfiguredGuard:
    def test_client_access_raises(self) -> None:
        service = CdekAdminService.from_account(None)
        with pytest.raises(ProviderUnavailableError):
            _ = service.client

    @pytest.mark.asyncio
    async def test_operation_raises(self) -> None:
        service = CdekAdminService.from_account(None)
        with pytest.raises(ProviderUnavailableError):
            await service.get_checks({"date": "2026-05-01"})

    @pytest.mark.asyncio
    async def test_close_is_safe_when_unconfigured(self) -> None:
        service = CdekAdminService.from_account(None)
        await service.close()  # no client to close — must not raise


class TestDelegation:
    @pytest.mark.asyncio
    async def test_delegates_raw_call_to_client(self) -> None:
        client = AsyncMock()
        client.get_checks.return_value = {"check_info": []}
        service = CdekAdminService(client=client)

        result = await service.get_checks({"date": "2026-05-01"})

        assert result == {"check_info": []}
        client.get_checks.assert_awaited_once_with({"date": "2026-05-01"})

    @pytest.mark.asyncio
    async def test_close_closes_the_client(self) -> None:
        client = AsyncMock()
        service = CdekAdminService(client=client)

        await service.close()

        client.close.assert_awaited_once()
