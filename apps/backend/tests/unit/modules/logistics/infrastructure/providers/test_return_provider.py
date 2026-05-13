"""
Regression tests for ``CdekReturnProvider``:

- ``register_client_return`` sends only ``tariff_code`` and surfaces
  ``entity.uuid`` as ``provider_return_id``.
- ``register_refusal`` sends *no* body and treats audit ``reason`` as
  log-only.
- ``check_reverse_availability`` translates HTTP 200 (empty body) →
  ``is_available=True`` and ``ProviderHTTPError`` 400 with an
  ``errors`` list → ``is_available=False`` with formatted reason.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from src.modules.logistics.domain.value_objects import (
    Address,
    ClientReturnRequest,
    ContactInfo,
    Money,
    Parcel,
    RefusalRequest,
    ReverseAvailabilityRequest,
    Weight,
)
from src.modules.logistics.infrastructure.providers.cdek.return_provider import (
    CdekReturnProvider,
)
from src.modules.logistics.infrastructure.providers.errors import ProviderHTTPError

pytestmark = pytest.mark.unit


def _addr() -> Address:
    return Address(country_code="RU", city="Moscow")


def _contact() -> ContactInfo:
    return ContactInfo(first_name="Ivan", last_name="Ivanov", phone="+79991234567")


def _parcel() -> Parcel:
    return Parcel(
        weight=Weight(grams=1000),
        declared_value=Money(amount=10000, currency_code="RUB"),
    )


@pytest.fixture
def cdek_client() -> AsyncMock:
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = False
    return client


class TestRegisterClientReturn:
    @pytest.mark.asyncio
    async def test_sends_only_tariff_code(self, cdek_client: AsyncMock) -> None:
        cdek_client.register_client_return.return_value = {
            "entity": {"uuid": "ret-123"},
        }
        provider = CdekReturnProvider(cdek_client)
        request = ClientReturnRequest(
            order_provider_id="order-uuid",
            tariff_code=480,
            return_address=_addr(),
            sender=_contact(),
            recipient=_contact(),
            parcels=[_parcel()],
        )

        result = await provider.register_client_return(request)

        cdek_client.register_client_return.assert_awaited_once_with(
            "order-uuid", {"tariff_code": 480}
        )
        assert result.success is True
        assert result.provider_return_id == "ret-123"

    @pytest.mark.asyncio
    async def test_returns_failure_on_http_error(self, cdek_client: AsyncMock) -> None:
        cdek_client.register_client_return.side_effect = ProviderHTTPError(
            status_code=400,
            message="invalid tariff",
            response_body='{"errors":[{"code":"v2_tariff_invalid","message":"bad"}]}',
        )
        provider = CdekReturnProvider(cdek_client)
        request = ClientReturnRequest(
            order_provider_id="order-uuid",
            tariff_code=480,
            return_address=_addr(),
            sender=_contact(),
            recipient=_contact(),
            parcels=[_parcel()],
        )

        result = await provider.register_client_return(request)

        assert result.success is False
        assert "invalid tariff" in (result.reason or "")
        assert result.provider_return_id is None


class TestRegisterRefusal:
    @pytest.mark.asyncio
    async def test_sends_none_body(self, cdek_client: AsyncMock) -> None:
        cdek_client.register_refusal.return_value = {
            "entity": {"uuid": "refuse-1"},
        }
        provider = CdekReturnProvider(cdek_client)

        result = await provider.register_refusal(
            RefusalRequest(order_provider_id="order-uuid", reason="not interested")
        )

        cdek_client.register_refusal.assert_awaited_once_with("order-uuid", None)
        assert result.success is True
        assert result.provider_return_id == "refuse-1"


class TestCheckReverseAvailability:
    @pytest.mark.asyncio
    async def test_empty_200_means_available(self, cdek_client: AsyncMock) -> None:
        cdek_client.check_reverse_availability.return_value = {}
        provider = CdekReturnProvider(cdek_client)

        result = await provider.check_reverse_availability(
            ReverseAvailabilityRequest(
                tariff_code=482,
                sender_phones=("+79991234567",),
                recipient_phones=("+79997654321",),
                from_location=_addr(),
                to_location=_addr(),
            )
        )

        assert result.is_available is True
        assert result.reason is None

    @pytest.mark.asyncio
    async def test_400_with_errors_means_unavailable(
        self, cdek_client: AsyncMock
    ) -> None:
        cdek_client.check_reverse_availability.side_effect = ProviderHTTPError(
            status_code=400,
            message="bad request",
            response_body=json.dumps(
                {
                    "errors": [
                        {"code": "v2_reverse_unavailable", "message": "no path"},
                        {"code": "v2_tariff", "message": "wrong"},
                    ]
                }
            ),
        )
        provider = CdekReturnProvider(cdek_client)

        result = await provider.check_reverse_availability(
            ReverseAvailabilityRequest(
                tariff_code=482,
                sender_phones=("+79991234567",),
                recipient_phones=("+79997654321",),
                from_location=_addr(),
                to_location=_addr(),
            )
        )

        assert result.is_available is False
        # Both errors are formatted into a single readable reason.
        assert "v2_reverse_unavailable" in (result.reason or "")
        assert "no path" in (result.reason or "")
        assert "v2_tariff" in (result.reason or "")

    @pytest.mark.asyncio
    async def test_pickup_points_short_circuit_locations(
        self, cdek_client: AsyncMock
    ) -> None:
        """When ``shipment_point`` is supplied, ``from_location`` is ignored."""
        cdek_client.check_reverse_availability.return_value = {}
        provider = CdekReturnProvider(cdek_client)

        await provider.check_reverse_availability(
            ReverseAvailabilityRequest(
                tariff_code=482,
                sender_phones=("+79991234567",),
                recipient_phones=("+79997654321",),
                from_location=_addr(),  # should be ignored
                shipment_point="MSK1",
                delivery_point="SPB2",
            )
        )

        sent_body = cdek_client.check_reverse_availability.await_args.args[0]
        assert sent_body["shipment_point"] == "MSK1"
        assert sent_body["delivery_point"] == "SPB2"
        assert "from_location" not in sent_body
        assert "to_location" not in sent_body
