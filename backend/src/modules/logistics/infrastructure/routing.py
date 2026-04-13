"""
Provider routing / eligibility policy.

Determines which providers are eligible to handle a given
origin → destination route with specific parcel constraints.
"""

from src.modules.logistics.domain.interfaces import IShippingProviderRegistry
from src.modules.logistics.domain.value_objects import (
    Address,
    Parcel,
    ProviderCode,
)


class DefaultProviderRoutingPolicy:
    """Default routing policy — returns all registered rate providers.

    This baseline implementation makes all registered providers eligible.
    Extend or replace it to add filtering by:
    - country pair (domestic / international)
    - weight / dimension limits per provider
    - supplier preferences
    - delivery type restrictions
    """

    def __init__(self, registry: IShippingProviderRegistry) -> None:
        self._registry = registry

    async def get_eligible_providers(
        self,
        origin: Address,
        destination: Address,
        parcels: list[Parcel],
    ) -> list[ProviderCode]:
        rate_providers = self._registry.list_rate_providers()
        return [p.provider_code() for p in rate_providers]
