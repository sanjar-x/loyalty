"""
Regression tests for ``CdekIntakeProvider``:

- ``get_intake`` sorts ``statuses`` by ``date_time`` before picking the
  latest (CDEK does not guarantee chronological ordering).
- ``cancel_intake`` returns ``True`` on a successful DELETE and
  ``False`` on a ``ProviderHTTPError``.
- ``create_intake`` extracts ``entity.uuid`` and reports
  ``IntakeStatus.ACCEPTED`` after a 202.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.modules.logistics.domain.value_objects import (
    Address,
    ContactInfo,
    IntakeRequest,
    IntakeStatus,
    Parcel,
    Weight,
)
from src.modules.logistics.infrastructure.providers.cdek.intake_provider import (
    CdekIntakeProvider,
)
from src.modules.logistics.infrastructure.providers.errors import ProviderHTTPError

pytestmark = pytest.mark.unit


@pytest.fixture
def cdek_client() -> AsyncMock:
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = False
    return client


def _intake_request() -> IntakeRequest:
    return IntakeRequest(
        order_provider_id="order-uuid",
        intake_date="2026-04-26",
        intake_time_from="09:00",
        intake_time_to="18:00",
        from_address=Address(country_code="RU", city="Moscow", street="Lenina"),
        sender=ContactInfo(first_name="Ivan", last_name="Ivanov", phone="+79991234567"),
        package=Parcel(weight=Weight(grams=2000)),
    )


class TestCreateIntake:
    @pytest.mark.asyncio
    async def test_returns_uuid_and_accepted_status(
        self, cdek_client: AsyncMock
    ) -> None:
        cdek_client.create_intake.return_value = {
            "entity": {"uuid": "intake-uuid"},
        }
        provider = CdekIntakeProvider(cdek_client)

        result = await provider.create_intake(_intake_request())

        assert result.provider_intake_id == "intake-uuid"
        assert result.status is IntakeStatus.ACCEPTED

    @pytest.mark.asyncio
    async def test_raises_when_no_uuid_in_response(
        self, cdek_client: AsyncMock
    ) -> None:
        cdek_client.create_intake.return_value = {"entity": {}}
        provider = CdekIntakeProvider(cdek_client)

        with pytest.raises(ProviderHTTPError):
            await provider.create_intake(_intake_request())


class TestGetIntake:
    @pytest.mark.asyncio
    async def test_picks_latest_status_by_date_time(
        self, cdek_client: AsyncMock
    ) -> None:
        # Statuses returned out of chronological order.
        cdek_client.get_intake.return_value = {
            "entity": {
                "uuid": "intake-uuid",
                "statuses": [
                    {"code": "ACCEPTED", "date_time": "2026-04-25T10:00:00+0300"},
                    {"code": "COMPLETED", "date_time": "2026-04-26T14:00:00+0300"},
                    {"code": "WAITING", "date_time": "2026-04-26T09:00:00+0300"},
                ],
            }
        }
        provider = CdekIntakeProvider(cdek_client)

        status = await provider.get_intake("intake-uuid")

        # COMPLETED has the latest date_time even though it isn't last in the list.
        assert status is IntakeStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_returns_unknown_when_statuses_empty(
        self, cdek_client: AsyncMock
    ) -> None:
        cdek_client.get_intake.return_value = {"entity": {"statuses": []}}
        provider = CdekIntakeProvider(cdek_client)

        assert await provider.get_intake("x") is IntakeStatus.UNKNOWN

    @pytest.mark.asyncio
    async def test_returns_unknown_for_unrecognised_code(
        self, cdek_client: AsyncMock
    ) -> None:
        cdek_client.get_intake.return_value = {
            "entity": {
                "statuses": [
                    {"code": "MYSTERY", "date_time": "2026-04-26T14:00:00+0300"},
                ]
            }
        }
        provider = CdekIntakeProvider(cdek_client)
        assert await provider.get_intake("x") is IntakeStatus.UNKNOWN


class TestCancelIntake:
    @pytest.mark.asyncio
    async def test_returns_true_on_success(self, cdek_client: AsyncMock) -> None:
        cdek_client.delete_intake.return_value = {"entity": {}}
        provider = CdekIntakeProvider(cdek_client)

        assert await provider.cancel_intake("intake-uuid") is True
        cdek_client.delete_intake.assert_awaited_once_with("intake-uuid")

    @pytest.mark.asyncio
    async def test_returns_false_on_http_error(self, cdek_client: AsyncMock) -> None:
        cdek_client.delete_intake.side_effect = ProviderHTTPError(
            status_code=400, message="cannot delete"
        )
        provider = CdekIntakeProvider(cdek_client)

        assert await provider.cancel_intake("intake-uuid") is False
