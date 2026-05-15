"""
Phase-3 regression tests for the ``/admin/logistics/cdek`` router
helpers — the logic the thin passthrough endpoints all funnel through.

* ``_cdek_call`` translates the CDEK client's bare provider exceptions
  onto the shared error hierarchy: a CDEK 4xx → 422, a 5xx / status-0 /
  timeout / auth failure → 503.
* ``CdekJsonResponse.from_raw`` wraps a CDEK payload, lifting its
  ``errors`` / ``warnings`` arrays out for uniform surfacing.
"""

from __future__ import annotations

import pytest

from src.modules.logistics.domain.exceptions import ProviderUnavailableError
from src.modules.logistics.infrastructure.providers.errors import (
    ProviderAuthError,
    ProviderHTTPError,
    ProviderTimeoutError,
)
from src.modules.logistics.presentation.router_admin_cdek import _cdek_call
from src.modules.logistics.presentation.schemas_cdek_admin import CdekJsonResponse
from src.shared.exceptions import UnprocessableEntityError

pytestmark = pytest.mark.unit


async def _ok() -> dict:
    return {"ok": True}


async def _raise(exc: Exception) -> dict:
    raise exc


class TestCdekCall:
    @pytest.mark.asyncio
    async def test_passes_through_success(self) -> None:
        assert await _cdek_call(_ok()) == {"ok": True}

    @pytest.mark.asyncio
    async def test_provider_4xx_becomes_422(self) -> None:
        with pytest.raises(UnprocessableEntityError):
            await _cdek_call(
                _raise(ProviderHTTPError(status_code=400, message="bad request"))
            )

    @pytest.mark.asyncio
    async def test_provider_5xx_becomes_503(self) -> None:
        with pytest.raises(ProviderUnavailableError):
            await _cdek_call(_raise(ProviderHTTPError(status_code=503, message="down")))

    @pytest.mark.asyncio
    async def test_provider_status_zero_becomes_503(self) -> None:
        # status_code 0 is the client's "no HTTP response" sentinel.
        with pytest.raises(ProviderUnavailableError):
            await _cdek_call(
                _raise(ProviderHTTPError(status_code=0, message="poll timeout"))
            )

    @pytest.mark.asyncio
    async def test_timeout_becomes_503(self) -> None:
        with pytest.raises(ProviderUnavailableError):
            await _cdek_call(_raise(ProviderTimeoutError()))

    @pytest.mark.asyncio
    async def test_auth_error_becomes_503(self) -> None:
        with pytest.raises(ProviderUnavailableError):
            await _cdek_call(_raise(ProviderAuthError()))


class TestCdekJsonResponse:
    def test_from_raw_dict_lifts_errors_and_warnings(self) -> None:
        raw = {
            "entity": {"uuid": "x"},
            "errors": [{"code": "e1", "message": "bad"}],
            "warnings": [{"code": "w1", "message": "heads up"}],
        }

        env = CdekJsonResponse.from_raw(raw)

        assert env.data == raw
        assert env.errors == [{"code": "e1", "message": "bad"}]
        assert env.warnings == [{"code": "w1", "message": "heads up"}]

    def test_from_raw_list_has_no_errors(self) -> None:
        env = CdekJsonResponse.from_raw([{"a": 1}, {"b": 2}])
        assert env.data == [{"a": 1}, {"b": 2}]
        assert env.errors is None
        assert env.warnings is None

    def test_from_raw_plain_dict_without_errors(self) -> None:
        env = CdekJsonResponse.from_raw({"entity": {"uuid": "x"}})
        assert env.data == {"entity": {"uuid": "x"}}
        assert env.errors is None
        assert env.warnings is None
