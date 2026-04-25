"""
Regression tests for ``CdekClient._poll_print_document``:

CDEK terminal codes for print forms are ``READY``, ``INVALID`` and
``REMOVED`` — the previous code looked for the non-existent ``FAILED``
status. Statuses also need to be sorted by ``date_time`` because CDEK
does not document the array order.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.modules.logistics.infrastructure.providers.cdek.client import CdekClient
from src.modules.logistics.infrastructure.providers.errors import ProviderHTTPError

pytestmark = pytest.mark.unit


def _client() -> CdekClient:
    # Bypass auth + HTTP wiring — _poll_print_document only uses the
    # async helpers we pass in.
    client = CdekClient.__new__(CdekClient)
    return client


class TestPrintPolling:
    @pytest.mark.asyncio
    async def test_downloads_when_latest_status_ready(self) -> None:
        status_fn = AsyncMock(
            return_value={
                "entity": {
                    "statuses": [
                        {"code": "ACCEPTED", "date_time": "2026-04-25T10:00:00+0300"},
                        {"code": "READY", "date_time": "2026-04-25T10:05:00+0300"},
                    ]
                }
            }
        )
        download_fn = AsyncMock(return_value=b"PDF")

        result = await _client()._poll_print_document(
            status_fn, download_fn, max_attempts=2, poll_interval=0.0
        )

        assert result == b"PDF"
        download_fn.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_picks_latest_status_when_unsorted(self) -> None:
        status_fn = AsyncMock(
            return_value={
                "entity": {
                    "statuses": [
                        {"code": "READY", "date_time": "2026-04-25T10:05:00+0300"},
                        # ``REMOVED`` is later — must win.
                        {"code": "REMOVED", "date_time": "2026-04-25T10:10:00+0300"},
                    ]
                }
            }
        )
        download_fn = AsyncMock(return_value=b"PDF")

        with pytest.raises(ProviderHTTPError) as exc_info:
            await _client()._poll_print_document(
                status_fn, download_fn, max_attempts=1, poll_interval=0.0
            )

        assert "removed" in str(exc_info.value).lower()
        download_fn.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_raises_on_invalid_terminal(self) -> None:
        status_fn = AsyncMock(
            return_value={
                "entity": {
                    "statuses": [
                        {
                            "code": "INVALID",
                            "name": "broken order_uuid",
                            "date_time": "2026-04-25T10:00:00+0300",
                        }
                    ]
                }
            }
        )
        download_fn = AsyncMock()

        with pytest.raises(ProviderHTTPError) as exc_info:
            await _client()._poll_print_document(
                status_fn, download_fn, max_attempts=1, poll_interval=0.0
            )

        assert "invalid" in str(exc_info.value).lower()
        download_fn.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_times_out_when_never_terminal(self) -> None:
        status_fn = AsyncMock(
            return_value={
                "entity": {
                    "statuses": [
                        {"code": "ACCEPTED", "date_time": "2026-04-25T10:00:00+0300"}
                    ]
                }
            }
        )
        download_fn = AsyncMock()

        with pytest.raises(ProviderHTTPError) as exc_info:
            await _client()._poll_print_document(
                status_fn, download_fn, max_attempts=2, poll_interval=0.0
            )

        assert "timed out" in str(exc_info.value).lower()
        download_fn.assert_not_awaited()
