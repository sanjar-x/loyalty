"""
CDEK provider factory — implements ``IProviderFactory``.

Creates CDEK capability adapters from stored credentials.
All adapters share the same ``CdekClient`` instance (and thus the same
OAuth2 auth manager / HTTP connection pool) per credential set.
"""

from typing import Any

from src.modules.logistics.domain.interfaces import (
    IBookingProvider,
    IDeliveryScheduleProvider,
    IDocumentProvider,
    IEditProvider,
    IIntakeProvider,
    IPickupPointProvider,
    IRateProvider,
    IReturnProvider,
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
from src.modules.logistics.infrastructure.providers.cdek.delivery_schedule_provider import (
    CdekDeliveryScheduleProvider,
)
from src.modules.logistics.infrastructure.providers.cdek.document_provider import (
    CdekDocumentProvider,
)
from src.modules.logistics.infrastructure.providers.cdek.intake_provider import (
    CdekIntakeProvider,
)
from src.modules.logistics.infrastructure.providers.cdek.order_edit_provider import (
    CdekOrderEditProvider,
)
from src.modules.logistics.infrastructure.providers.cdek.pickup_point_provider import (
    CdekPickupPointProvider,
)
from src.modules.logistics.infrastructure.providers.cdek.rate_provider import (
    CdekRateProvider,
)
from src.modules.logistics.infrastructure.providers.cdek.return_provider import (
    CdekReturnProvider,
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
        cfg = config or {}
        return CdekWebhookAdapter(
            webhook_secret=cfg.get("webhook_secret"),
            allowed_ips=cfg.get("webhook_allowed_ips"),
        )

    def create_intake_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IIntakeProvider | None:
        return CdekIntakeProvider(self._get_or_create_client(credentials, config))

    def create_delivery_schedule_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IDeliveryScheduleProvider | None:
        return CdekDeliveryScheduleProvider(
            self._get_or_create_client(credentials, config)
        )

    def create_return_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IReturnProvider | None:
        return CdekReturnProvider(self._get_or_create_client(credentials, config))

    def create_edit_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IEditProvider | None:
        # CDEK's PATCH /v2/orders has no async edit-task pipeline, so it
        # does not fit the ``IEditProvider`` contract (shaped around
        # Yandex's ``EditTaskResult`` / ``get_edit_status`` poll loop).
        # CDEK order editing is exposed as a CDEK-local capability via
        # ``create_order_edit_provider`` instead, reached by the CDEK
        # admin router rather than the carrier-agnostic registry.
        return None

    def create_order_edit_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> CdekOrderEditProvider:
        """Create the CDEK-specific order-edit provider (``PATCH /v2/orders``).

        Not part of ``IProviderFactory`` — CDEK order editing is a
        CDEK-local capability (see :meth:`create_edit_provider`).
        """
        return CdekOrderEditProvider(self._get_or_create_client(credentials, config))

    def get_client(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> CdekClient:
        """Return the cached ``CdekClient`` for these credentials.

        Public accessor over the per-credential client cache — used by
        registry bootstrap to run the idempotent webhook-subscription
        sync on the same client the capability adapters share.
        """
        return self._get_or_create_client(credentials, config)

    async def close(self) -> None:
        """Close all cached HTTP clients.

        Called once at app shutdown via the registry's lifecycle hook.
        """
        for client in self._clients.values():
            await client.close()
        self._clients.clear()
