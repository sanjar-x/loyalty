"""
Phase-2 regression tests for ``CdekOrderEditProvider`` — the CDEK-local
order-edit capability over ``PATCH /v2/orders``.

Not wired through ``IEditProvider`` (CDEK has no async edit-task
pipeline); the 202 ``requests[]`` envelope is translated into a
``CdekEditResult`` where only an outright ``INVALID`` / HTTP error is a
failure — an ``ACCEPTED`` edit is a success pending order re-read.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.modules.logistics.infrastructure.providers.cdek.order_edit_provider import (
    CdekOrderEditProvider,
)
from src.modules.logistics.infrastructure.providers.errors import ProviderHTTPError

pytestmark = pytest.mark.unit


def _valid_body() -> dict:
    return {"uuid": "order-1", "type": 1, "recipient": {"name": "Иван Петров"}}


@pytest.fixture
def cdek_client() -> AsyncMock:
    return AsyncMock()


class TestEditOrder:
    @pytest.mark.asyncio
    async def test_accepted_edit_is_success(self, cdek_client: AsyncMock) -> None:
        cdek_client.update_order.return_value = {
            "requests": [
                {"type": "UPDATE", "state": "ACCEPTED", "request_uuid": "req-1"}
            ]
        }
        provider = CdekOrderEditProvider(cdek_client)

        result = await provider.edit_order(_valid_body())

        assert result.success is True
        assert result.state == "ACCEPTED"
        assert result.request_uuid == "req-1"
        cdek_client.update_order.assert_awaited_once_with(_valid_body())

    @pytest.mark.asyncio
    async def test_invalid_request_is_failure_with_reason(
        self, cdek_client: AsyncMock
    ) -> None:
        cdek_client.update_order.return_value = {
            "requests": [
                {
                    "type": "UPDATE",
                    "state": "INVALID",
                    "errors": [
                        {"code": "v2_update_forbidden", "message": "order accepted"}
                    ],
                }
            ]
        }
        provider = CdekOrderEditProvider(cdek_client)

        result = await provider.edit_order(_valid_body())

        assert result.success is False
        assert result.state == "INVALID"
        assert "v2_update_forbidden" in (result.reason or "")

    @pytest.mark.asyncio
    async def test_http_error_is_failure(self, cdek_client: AsyncMock) -> None:
        cdek_client.update_order.side_effect = ProviderHTTPError(
            status_code=400, message="bad request", response_body="{}"
        )
        provider = CdekOrderEditProvider(cdek_client)

        result = await provider.edit_order(_valid_body())

        assert result.success is False
        assert "bad request" in (result.reason or "")

    @pytest.mark.asyncio
    async def test_missing_identifier_raises(self, cdek_client: AsyncMock) -> None:
        provider = CdekOrderEditProvider(cdek_client)

        with pytest.raises(ValueError, match="uuid"):
            await provider.edit_order({"type": 1, "recipient": {"name": "X"}})
        cdek_client.update_order.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_missing_required_fields_raises(self, cdek_client: AsyncMock) -> None:
        provider = CdekOrderEditProvider(cdek_client)

        with pytest.raises(ValueError, match="recipient"):
            await provider.edit_order({"uuid": "order-1", "type": 1})

    @pytest.mark.asyncio
    async def test_picks_update_request_over_other_history(
        self, cdek_client: AsyncMock
    ) -> None:
        # Response carries mixed request history — the UPDATE entry wins.
        cdek_client.update_order.return_value = {
            "requests": [
                {"type": "CREATE", "state": "SUCCESSFUL", "request_uuid": "old"},
                {"type": "UPDATE", "state": "ACCEPTED", "request_uuid": "new"},
            ]
        }
        provider = CdekOrderEditProvider(cdek_client)

        result = await provider.edit_order(_valid_body())

        assert result.request_uuid == "new"

    @pytest.mark.asyncio
    async def test_bare_202_without_requests_is_success(
        self, cdek_client: AsyncMock
    ) -> None:
        cdek_client.update_order.return_value = {"entity": {"uuid": "order-1"}}
        provider = CdekOrderEditProvider(cdek_client)

        result = await provider.edit_order(_valid_body())

        assert result.success is True
