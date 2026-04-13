"""
CDEK provider factory — implements ``IProviderFactory``.

Creates CDEK capability adapters from stored credentials.
All adapters share the same ``CdekClient`` instance (and thus the same
OAuth2 auth manager / HTTP connection pool) per credential set.
"""

from typing import Any

from src.modules.logistics.domain.interfaces import (
    IBookingProvider,
    IDocumentProvider,
    IPickupPointProvider,
    IRateProvider,
    ITrackingPollProvider,
    ITrackingProvider,
    IWebhookAdapter,
)
from src.modules.logistics.domain.value_objects import (
    PROVIDER_CDEK,
    ProviderCode,
)
from src.modules.logistics.infrastructure.providers.cdek.booking_provider import (
    CdekBookingProvider,
)
from src.modules.logistics.infrastructure.providers.cdek.client import CdekClient
from src.modules.logistics.infrastructure.providers.cdek.constants import (
    CDEK_PRODUCTION_URL,
    CDEK_TEST_URL,
)
from src.modules.logistics.infrastructure.providers.cdek.document_provider import (
    CdekDocumentProvider,
)
from src.modules.logistics.infrastructure.providers.cdek.pickup_point_provider import (
    CdekPickupPointProvider,
)
from src.modules.logistics.infrastructure.providers.cdek.rate_provider import (
    CdekRateProvider,
)
from src.modules.logistics.infrastructure.providers.cdek.tracking_poll_provider import (
    CdekTrackingPollProvider,
)
from src.modules.logistics.infrastructure.providers.cdek.tracking_provider import (
    CdekTrackingProvider,
)
from src.modules.logistics.infrastructure.providers.cdek.webhook_adapter import (
    CdekWebhookAdapter,
)


class CdekProviderFactory:
    """CDEK implementation of ``IProviderFactory``.

    Caches a single ``CdekClient`` per (client_id, test_mode) tuple
    so all capability adapters share auth tokens and HTTP connections.

    Expected credentials dict::

        {
            "client_id": "...",
            "client_secret": "...",
        }

    Optional config dict::

        {
            "test_mode": true,          # use test environment
            "timeout_seconds": 30.0,
            "max_retries": 3,
        }
    """

    def __init__(self) -> None:
        self._clients: dict[str, CdekClient] = {}

    def provider_code(self) -> ProviderCode:
        return PROVIDER_CDEK

    def _get_or_create_client(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> CdekClient:
        cfg = config or {}
        test_mode = cfg.get("test_mode", False)
        client_id = credentials["client_id"]
        cache_key = f"{client_id}:{test_mode}"

        if cache_key not in self._clients:
            base_url = CDEK_TEST_URL if test_mode else CDEK_PRODUCTION_URL
            self._clients[cache_key] = CdekClient(
                base_url=base_url,
                client_id=client_id,
                client_secret=credentials["client_secret"],
                timeout_seconds=cfg.get("timeout_seconds", 30.0),
                max_retries=cfg.get("max_retries", 3),
            )

        return self._clients[cache_key]

    def create_rate_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IRateProvider:
        return CdekRateProvider(self._get_or_create_client(credentials, config))

    def create_booking_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IBookingProvider:
        return CdekBookingProvider(self._get_or_create_client(credentials, config))

    def create_tracking_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> ITrackingProvider:
        return CdekTrackingProvider(self._get_or_create_client(credentials, config))

    def create_tracking_poll_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> ITrackingPollProvider | None:
        return CdekTrackingPollProvider(self._get_or_create_client(credentials, config))

    def create_pickup_point_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IPickupPointProvider:
        return CdekPickupPointProvider(self._get_or_create_client(credentials, config))

    def create_document_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IDocumentProvider:
        return CdekDocumentProvider(self._get_or_create_client(credentials, config))

    def create_webhook_adapter(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IWebhookAdapter:
        return CdekWebhookAdapter()
