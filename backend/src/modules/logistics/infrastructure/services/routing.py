"""
Provider routing / eligibility policy.

Determines which providers are eligible to handle a given
origin → destination route with specific parcel constraints.
"""

from src.modules.logistics.domain.interfaces import IShippingProviderRegistry
from src.modules.logistics.domain.value_objects import (
    PROVIDER_CDEK,
    PROVIDER_RUSSIAN_POST,
    PROVIDER_YANDEX_DELIVERY,
    Address,
    Parcel,
    ProviderCode,
)

# Country coverage per provider. Source: CDEK and Yandex Delivery
# documentation. The list is intentionally conservative — adding a
# country here is cheaper than handling a "No delivery options" error
# for every quote in production.
_PROVIDER_COVERAGE: dict[ProviderCode, frozenset[str]] = {
    PROVIDER_CDEK: frozenset({
        "RU", "KZ", "BY", "AM", "KG", "UZ", "AZ", "GE",
        "TR", "CN", "MN", "TH", "AE", "KR", "PL", "JP",
    }),
    # Yandex Delivery "Other Day" is currently RU-only.
    PROVIDER_YANDEX_DELIVERY: frozenset({"RU"}),
    # Russian Post — domestic + international from RU.
    PROVIDER_RUSSIAN_POST: frozenset({"RU"}),
}


class DefaultProviderRoutingPolicy:
    """Default routing policy with country-coverage pre-filtering.

    Filters out providers that cannot serve the destination country
    before fanning out to ``calculate_rates``. Reduces wasted API calls
    and noise in the per-provider error map.

    For unknown providers (not in ``_PROVIDER_COVERAGE``) the policy
    falls back to "eligible" — keeps the door open for new integrations
    that haven't been added to the coverage table yet.
    """

    def __init__(self, registry: IShippingProviderRegistry) -> None:
        self._registry = registry

    async def get_eligible_providers(
        self,
        origin: Address,
        destination: Address,
        parcels: list[Parcel],
    ) -> list[ProviderCode]:
        destination_country = (destination.country_code or "").upper()
        result: list[ProviderCode] = []
        for provider in self._registry.list_rate_providers():
            code = provider.provider_code()
            coverage = _PROVIDER_COVERAGE.get(code)
            if coverage is None or destination_country in coverage:
                result.append(code)
        return result
