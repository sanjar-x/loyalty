"""Implementation of :class:`IOriginAddressResolver`.

Reads the per-provider sender warehouse from
``ProviderAccountModel.config_json`` and materialises it as an
:class:`Address`. Configured shape (in admin UI / seed JSON):

.. code-block:: json

    {
        "default_origin": {
            "country_code": "RU",
            "city": "Москва",
            "region": "Москва",
            "postal_code": "125167",
            "street": "Ленинградский проспект",
            "house": "39",
            "latitude": 55.78,
            "longitude": 37.55,
            "metadata": {
                "cdek_pvz_code": "MSK1",
                "cdek_city_code": "44"
            }
        }
    }

For Yandex Delivery the metadata block carries ``platform_station_id``
instead. ``country_code`` and ``city`` are required; everything else is
optional and forwarded verbatim into the provider request.

A first-class lookup result is cached for the lifetime of the resolver
instance (REQUEST scope) so a single ``/rates/quote`` call doesn't hit
the DB twice when the handler also wants to compose downstream
``BookingRequest`` data.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.logistics.domain.exceptions import ProviderUnavailableError
from src.modules.logistics.domain.interfaces import IOriginAddressResolver
from src.modules.logistics.domain.value_objects import Address, ProviderCode
from src.modules.logistics.infrastructure.models import ProviderAccountModel

# Top-level config key under which the sender warehouse address lives.
ORIGIN_CONFIG_KEY = "default_origin"

logger = logging.getLogger(__name__)


class ProviderAccountOriginResolver(IOriginAddressResolver):
    """Reads ``default_origin`` from the active ``ProviderAccountModel`` row."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._cache: dict[ProviderCode, Address] = {}

    async def resolve(self, provider_code: ProviderCode) -> Address:
        if provider_code in self._cache:
            return self._cache[provider_code]

        stmt = (
            select(ProviderAccountModel.config_json)
            .where(
                ProviderAccountModel.provider_code == provider_code,
                ProviderAccountModel.is_active.is_(True),
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        config = result.scalar_one_or_none()
        if config is None:
            raise ProviderUnavailableError(
                message=f"No active ProviderAccount for '{provider_code}'",
                details={
                    "provider_code": provider_code,
                    "reason": "no active ProviderAccount row",
                },
            )
        origin_data = (config or {}).get(ORIGIN_CONFIG_KEY)
        if not origin_data:
            raise ProviderUnavailableError(
                message=(
                    f"Provider '{provider_code}' has no default_origin "
                    "configured — operator must set the sender warehouse."
                ),
                details={
                    "provider_code": provider_code,
                    "config_key": ORIGIN_CONFIG_KEY,
                },
            )
        address = _payload_to_address(provider_code, origin_data)
        self._cache[provider_code] = address
        return address


def _payload_to_address(
    provider_code: ProviderCode, payload: dict[str, Any]
) -> Address:
    country_code = payload.get("country_code")
    city = payload.get("city")
    if not country_code or not city:
        raise ProviderUnavailableError(
            message=(
                f"Provider '{provider_code}' default_origin is missing "
                "required 'country_code' or 'city'."
            ),
            details={"provider_code": provider_code},
        )
    metadata_raw = payload.get("metadata") or {}
    metadata = {
        str(k): str(v) for k, v in metadata_raw.items() if v is not None and v != ""
    }
    return Address(
        country_code=str(country_code),
        city=str(city),
        region=_optional_str(payload.get("region")),
        postal_code=_optional_str(payload.get("postal_code")),
        street=_optional_str(payload.get("street")),
        house=_optional_str(payload.get("house")),
        apartment=_optional_str(payload.get("apartment")),
        subdivision_code=_optional_str(payload.get("subdivision_code")),
        latitude=_optional_float(payload.get("latitude")),
        longitude=_optional_float(payload.get("longitude")),
        raw_address=_optional_str(payload.get("raw_address")),
        metadata=metadata,
    )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float, str)):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    return None


__all__ = ["ORIGIN_CONFIG_KEY", "ProviderAccountOriginResolver"]
