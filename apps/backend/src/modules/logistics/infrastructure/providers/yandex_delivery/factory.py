"""
Yandex Delivery provider factory — implements ``IProviderFactory``.

Creates Yandex Delivery capability adapters from stored credentials.
All adapters share the same ``YandexDeliveryClient`` instance per
credential set.
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
    PROVIDER_YANDEX_DELIVERY,
    ProviderCode,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.booking_provider import (
    YandexDeliveryBookingProvider,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.client import (
    YandexDeliveryClient,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.constants import (
    YANDEX_PRODUCTION_URL,
    YANDEX_TEST_URL,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.delivery_schedule_provider import (
    YandexDeliveryDeliveryScheduleProvider,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.document_provider import (
    YandexDeliveryDocumentProvider,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.edit_provider import (
    YandexDeliveryEditProvider,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.pickup_point_provider import (
    YandexDeliveryPickupPointProvider,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.rate_provider import (
    YandexDeliveryRateProvider,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.tracking_poll_provider import (
    YandexDeliveryTrackingPollProvider,
)
from src.modules.logistics.infrastructure.providers.yandex_delivery.tracking_provider import (
    YandexDeliveryTrackingProvider,
)


class YandexDeliveryProviderFactory:
    """Yandex Delivery implementation of ``IProviderFactory``.

    Caches a single ``YandexDeliveryClient`` per (oauth_token, test_mode)
    tuple so all capability adapters share HTTP connections.

    Expected credentials dict::

        {
            "oauth_token": "...",
        }

    Optional config dict::

        {
            "test_mode": true,
            "platform_station_id": "...",
            "default_inn": "9715386101",
            "default_nds": 0,
            "payment_method": "already_paid",
            "timeout_seconds": 30.0,
            "max_retries": 3,
        }
    """

    def __init__(self) -> None:
        self._clients: dict[str, YandexDeliveryClient] = {}

    def provider_code(self) -> ProviderCode:
        return PROVIDER_YANDEX_DELIVERY

    def _get_or_create_client(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> YandexDeliveryClient:
        cfg = config or {}
        test_mode = cfg.get("test_mode", False)
        oauth_token = credentials["oauth_token"]
        cache_key = f"{oauth_token[:8]}:{test_mode}"

        if cache_key not in self._clients:
            base_url = YANDEX_TEST_URL if test_mode else YANDEX_PRODUCTION_URL
            self._clients[cache_key] = YandexDeliveryClient(
                base_url=base_url,
                oauth_token=oauth_token,
                timeout_seconds=cfg.get("timeout_seconds", 30.0),
                max_retries=cfg.get("max_retries", 3),
            )

        return self._clients[cache_key]

    def _get_config(self, config: dict[str, Any] | None) -> dict[str, Any]:
        return config or {}

    def create_rate_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IRateProvider:
        return YandexDeliveryRateProvider(
            self._get_or_create_client(credentials, config),
            self._get_config(config),
        )

    def create_booking_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IBookingProvider:
        return YandexDeliveryBookingProvider(
            self._get_or_create_client(credentials, config),
            self._get_config(config),
        )

    def create_tracking_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> ITrackingProvider:
        return YandexDeliveryTrackingProvider(
            self._get_or_create_client(credentials, config),
        )

    def create_tracking_poll_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> ITrackingPollProvider:
        return YandexDeliveryTrackingPollProvider(
            self._get_or_create_client(credentials, config),
        )

    def create_pickup_point_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IPickupPointProvider:
        return YandexDeliveryPickupPointProvider(
            self._get_or_create_client(credentials, config),
        )

    def create_document_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IDocumentProvider:
        return YandexDeliveryDocumentProvider(
            self._get_or_create_client(credentials, config),
        )

    def create_webhook_adapter(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IWebhookAdapter | None:
        # Yandex Delivery API does not support webhook registration
        return None

    def create_intake_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IIntakeProvider | None:
        # Yandex Delivery does not expose courier-intake scheduling.
        return None

    def create_delivery_schedule_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IDeliveryScheduleProvider | None:
        return YandexDeliveryDeliveryScheduleProvider(
            self._get_or_create_client(credentials, config),
            self._get_config(config),
        )

    def create_return_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IReturnProvider | None:
        # Yandex Delivery handles returns via standard order cancellation.
        return None

    def create_edit_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IEditProvider | None:
        return YandexDeliveryEditProvider(
            self._get_or_create_client(credentials, config)
        )

    async def close(self) -> None:
        """Close all cached HTTP clients.

        Called once at app shutdown via the registry's lifecycle hook.
        """
        for client in self._clients.values():
            await client.close()
        self._clients.clear()
