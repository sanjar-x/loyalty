"""DobroPost provider factory — implements ``IProviderFactory``.

Creates DobroPost capability adapters from stored credentials. Single
``DobroPostClient`` instance per (email, base_url) tuple so all
adapters share the JWT cache and httpx connection pool.

DobroPost capabilities matrix:

| Capability                  | Supported | Notes                                              |
| --------------------------- | --------- | -------------------------------------------------- |
| ``IRateProvider``           | ✗         | Tariffs are fixed contractual; manager picks ``dpTariffId``. |
| ``IBookingProvider``        | ✓         | ``POST /api/shipment``.                            |
| ``ITrackingProvider``       | ✗         | No per-shipment GET endpoint.                      |
| ``ITrackingPollProvider``   | ✓         | Polls ``GET /api/shipment`` and matches by id.     |
| ``IPickupPointProvider``    | ✗         | Customer picks ПВЗ at last-mile carrier.           |
| ``IDocumentProvider``       | ✗         | Labels printed by DobroPost itself.                |
| ``IIntakeProvider``         | ✗         | Item already in China — no courier intake.         |
| ``IDeliveryScheduleProvider``| ✗        | Not exposed by DobroPost API.                      |
| ``IReturnProvider``         | ✗         | Returns coordinated manually with DobroPost CS.    |
| ``IEditProvider``           | ✗         | Only ``PUT /api/shipment`` for passport correction (admin-side, not async). |
| ``IWebhookAdapter``         | ✓         | Two payload formats; secret + IP allow-list.       |
"""

from __future__ import annotations

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
    PROVIDER_DOBROPOST,
    ProviderCode,
)
from src.modules.logistics.infrastructure.providers.dobropost.booking_provider import (
    DobroPostBookingProvider,
)
from src.modules.logistics.infrastructure.providers.dobropost.client import (
    DobroPostClient,
)
from src.modules.logistics.infrastructure.providers.dobropost.constants import (
    DOBROPOST_PRODUCTION_URL,
)
from src.modules.logistics.infrastructure.providers.dobropost.tracking_poll_provider import (
    DobroPostTrackingPollProvider,
)
from src.modules.logistics.infrastructure.providers.dobropost.webhook_adapter import (
    DobroPostWebhookAdapter,
)


class DobroPostProviderFactory:
    """DobroPost implementation of ``IProviderFactory``.

    Expected credentials dict::

        {
            "email": "partner@example.com",
            "password": "S3cretPa$$word"
        }

    Optional config dict::

        {
            "base_url": "https://api.dobropost.com",   # default production
            "timeout_seconds": 30.0,
            "max_retries": 3,
            "webhook_secret": "...",                    # for IWebhookAdapter
            "webhook_allowed_ips": ["1.2.3.4", "10.0.0.0/24"],
        }
    """

    def __init__(self) -> None:
        self._clients: dict[str, DobroPostClient] = {}

    def provider_code(self) -> ProviderCode:
        return PROVIDER_DOBROPOST

    # ------------------------------------------------------------------ #
    # Internals                                                            #
    # ------------------------------------------------------------------ #

    def _get_or_create_client(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> DobroPostClient:
        cfg = config or {}
        base_url = cfg.get("base_url", DOBROPOST_PRODUCTION_URL)
        email = credentials["email"]
        cache_key = f"{email}:{base_url}"

        if cache_key not in self._clients:
            self._clients[cache_key] = DobroPostClient(
                base_url=base_url,
                email=email,
                password=credentials["password"],
                timeout_seconds=cfg.get("timeout_seconds", 30.0),
                max_retries=cfg.get("max_retries", 3),
            )
        return self._clients[cache_key]

    # ------------------------------------------------------------------ #
    # Capability constructors                                              #
    # ------------------------------------------------------------------ #

    def create_rate_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IRateProvider | None:
        # DobroPost intentionally absent from rate fan-out — manager
        # picks ``dpTariffId`` directly in admin UI.
        return None

    def create_booking_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IBookingProvider:
        return DobroPostBookingProvider(self._get_or_create_client(credentials, config))

    def create_tracking_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> ITrackingProvider | None:
        return None

    def create_tracking_poll_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> ITrackingPollProvider:
        return DobroPostTrackingPollProvider(
            self._get_or_create_client(credentials, config)
        )

    def create_pickup_point_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IPickupPointProvider | None:
        return None

    def create_document_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IDocumentProvider | None:
        return None

    def create_webhook_adapter(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IWebhookAdapter:
        cfg = config or {}
        return DobroPostWebhookAdapter(
            webhook_secret=cfg.get("webhook_secret"),
            allowed_ips=cfg.get("webhook_allowed_ips"),
        )

    def create_intake_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IIntakeProvider | None:
        return None

    def create_delivery_schedule_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IDeliveryScheduleProvider | None:
        return None

    def create_return_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IReturnProvider | None:
        return None

    def create_edit_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IEditProvider | None:
        # ``PUT /api/shipment`` is sync (no task pipeline). Wired
        # separately through admin command if/when needed.
        return None

    async def close(self) -> None:
        """Close all cached HTTP clients. Called at app shutdown."""
        for client in self._clients.values():
            await client.close()
        self._clients.clear()
