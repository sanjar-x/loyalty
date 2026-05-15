"""
CDEK admin service — a single facade over the CDEK-specific operations
exposed through the ``/admin/logistics/cdek`` router.

Most CDEK endpoints have no carrier-agnostic capability protocol (order
editing, delivery agreements, prealerts, fiscal receipts, COD
registries, international restriction hints, photo documents, location
lookups, the tariff catalogue, ...). Rather than widen the shared
``logistics`` domain ports for one carrier, those operations live here
as a CDEK-local facade, constructed per request from the active CDEK
``ProviderAccount``.

The service owns the lifecycle of its ``CdekClient`` — the Dishka
provider that builds it (``LogisticsCdekAdminProvider``) closes it after
the request. When no active CDEK account is configured the service is
built unconfigured and every operation raises
``ProviderUnavailableError`` so the admin API returns a clean 503 rather
than an ``AttributeError``.
"""

from __future__ import annotations

from typing import Any

from src.modules.logistics.domain.exceptions import ProviderUnavailableError
from src.modules.logistics.domain.provider_account import ProviderAccount
from src.modules.logistics.domain.value_objects import PROVIDER_CDEK, DocumentResult
from src.modules.logistics.infrastructure.providers.cdek.client import CdekClient
from src.modules.logistics.infrastructure.providers.cdek.constants import (
    CDEK_PRODUCTION_URL,
    CDEK_TEST_URL,
    CDEK_WEBHOOK_AUTO_SUBSCRIBE,
)
from src.modules.logistics.infrastructure.providers.cdek.document_provider import (
    CdekDocumentProvider,
)
from src.modules.logistics.infrastructure.providers.cdek.order_edit_provider import (
    CdekEditResult,
    CdekOrderEditProvider,
)
from src.modules.logistics.infrastructure.providers.cdek.webhook_subscriptions import (
    WebhookSyncResult,
    ensure_webhook_subscriptions,
    list_subscriptions,
)


def _build_client(credentials: dict[str, Any], config: dict[str, Any]) -> CdekClient:
    """Construct a ``CdekClient`` from a CDEK provider account's config.

    Mirrors ``CdekProviderFactory._get_or_create_client`` — test vs.
    production base URL is driven by ``config['test_mode']``.
    """
    test_mode = bool(config.get("test_mode", False))
    base_url = CDEK_TEST_URL if test_mode else CDEK_PRODUCTION_URL
    return CdekClient(
        base_url=base_url,
        client_id=credentials["client_id"],
        client_secret=credentials["client_secret"],
        timeout_seconds=config.get("timeout_seconds", 30.0),
        max_retries=config.get("max_retries", 3),
    )


class CdekAdminService:
    """Per-request facade over CDEK-specific admin operations."""

    def __init__(self, client: CdekClient | None) -> None:
        self._client = client

    @classmethod
    def from_account(cls, account: ProviderAccount | None) -> CdekAdminService:
        """Build the service from the active CDEK provider account.

        ``account`` is ``None`` (or inactive / not CDEK) when CDEK is not
        configured — the service is then built unconfigured and every
        call raises ``ProviderUnavailableError``. Malformed credentials
        (missing ``client_id`` / ``client_secret``) are treated the same
        way so a bad account never crashes the admin surface.
        """
        if (
            account is None
            or not account.is_active
            or account.provider_code != PROVIDER_CDEK
        ):
            return cls(client=None)
        try:
            client = _build_client(account.credentials, account.config)
        except KeyError:
            return cls(client=None)
        return cls(client=client)

    @property
    def is_configured(self) -> bool:
        """``True`` when a CDEK client is wired and ready."""
        return self._client is not None

    @property
    def client(self) -> CdekClient:
        """The live CDEK client, or raise if CDEK is not configured."""
        if self._client is None:
            raise ProviderUnavailableError(
                message=(
                    "CDEK provider account is not configured — add an active "
                    "CDEK account under /admin/logistics/provider-accounts first."
                ),
                error_code="CDEK_NOT_CONFIGURED",
                details={"provider": PROVIDER_CDEK},
            )
        return self._client

    async def close(self) -> None:
        """Release the underlying CDEK HTTP client (idempotent)."""
        if self._client is not None:
            await self._client.close()

    # -- Order editing -----------------------------------------------------

    async def edit_order(self, update_body: dict[str, Any]) -> CdekEditResult:
        """Apply a partial update to a CDEK order (``PATCH /v2/orders``)."""
        return await CdekOrderEditProvider(self.client).edit_order(update_body)

    async def get_order_by_params(self, params: dict[str, Any]) -> dict:
        """Look up a CDEK order by ``cdek_number`` / ``im_number``."""
        return await self.client.get_order_by_params(params)

    # -- Documents ---------------------------------------------------------

    async def get_barcode_label(self, provider_shipment_id: str) -> DocumentResult:
        """Generate + download the order barcode label (ШК места) PDF."""
        return await CdekDocumentProvider(self.client).get_barcode_label(
            provider_shipment_id
        )

    # -- Delivery agreements (договорённость о доставке) -------------------

    async def register_delivery_agreement(self, body: dict[str, Any]) -> dict:
        """Register a delivery agreement (``POST /v2/delivery``)."""
        return await self.client.register_delivery(body)

    async def get_delivery_agreement(self, agreement_uuid: str) -> dict:
        """Read a delivery agreement (``GET /v2/delivery/{uuid}``)."""
        return await self.client.get_delivery(agreement_uuid)

    # -- Prealerts ---------------------------------------------------------

    async def create_prealert(self, body: dict[str, Any]) -> dict:
        """Register a prealert (``POST /v2/prealert``)."""
        return await self.client.create_prealert(body)

    async def get_prealert(self, prealert_uuid: str) -> dict:
        """Read a prealert (``GET /v2/prealert/{uuid}``)."""
        return await self.client.get_prealert(prealert_uuid)

    # -- Fiscal receipts / COD registries ----------------------------------

    async def get_checks(self, params: dict[str, Any]) -> dict:
        """Read fiscal receipts (``GET /v2/check``)."""
        return await self.client.get_checks(params)

    async def get_registries(self, params: dict[str, Any]) -> dict:
        """Read COD payment registries (``GET /v2/registries``)."""
        return await self.client.get_registries(params)

    # -- International restriction hints -----------------------------------

    async def check_package_restrictions(self, body: dict[str, Any]) -> dict:
        """Check international order restrictions (restriction_hints)."""
        return await self.client.check_package_restrictions(body)

    # -- Photo documents ---------------------------------------------------

    async def get_ready_photos(self, body: dict[str, Any]) -> dict:
        """List orders with ready-to-download photos (``POST /v2/photoDocument``)."""
        return await self.client.get_ready_photos(body)

    # -- Order intakes / intake status -------------------------------------

    async def get_order_intakes(self, order_uuid: str) -> dict:
        """List every intake registered against a CDEK order."""
        return await self.client.get_order_intakes(order_uuid)

    async def change_intake_status(self, body: dict[str, Any]) -> dict:
        """Move an active intake to "требует обработки" (``PATCH /v2/intakes``)."""
        return await self.client.change_intake_status(body)

    # -- Tariff catalogue --------------------------------------------------

    async def list_available_tariffs(
        self, params: dict[str, Any] | None = None
    ) -> dict:
        """List the tariffs available for the contract (``GET /v2/calculator/alltariffs``)."""
        return await self.client.list_available_tariffs(params)

    # -- Location lookups --------------------------------------------------

    async def suggest_cities(self, params: dict[str, Any]) -> list[dict]:
        """City-name autocomplete (``GET /v2/location/suggest/cities``)."""
        return await self.client.suggest_cities(params)

    async def list_cities(self, params: dict[str, Any]) -> list[dict]:
        """Search CDEK cities (``GET /v2/location/cities``)."""
        return await self.client.list_cities(params)

    async def list_regions(self, params: dict[str, Any]) -> list[dict]:
        """Search CDEK regions (``GET /v2/location/regions``)."""
        return await self.client.list_regions(params)

    async def get_postal_codes(self, params: dict[str, Any]) -> list[dict]:
        """List postal codes for a CDEK city (``GET /v2/location/postalcodes``)."""
        return await self.client.get_postal_codes(params)

    async def get_location_by_coordinates(self, params: dict[str, Any]) -> list[dict]:
        """Resolve a CDEK location from lat/lng (``GET /v2/location/coordinates``)."""
        return await self.client.get_location_by_coordinates(params)

    # -- Webhook subscriptions ---------------------------------------------

    async def list_webhook_subscriptions(self) -> list[dict]:
        """List the active CDEK webhook subscriptions."""
        return await list_subscriptions(self.client)

    async def create_webhook_subscription(self, url: str, webhook_type: str) -> dict:
        """Register a single CDEK webhook subscription (``POST /v2/webhooks``)."""
        return await self.client.create_webhook(url, webhook_type)

    async def delete_webhook_subscription(self, subscription_uuid: str) -> dict:
        """Delete a CDEK webhook subscription by UUID."""
        return await self.client.delete_webhook(subscription_uuid)

    async def sync_webhook_subscriptions(
        self,
        url: str,
        types: tuple[str, ...] = CDEK_WEBHOOK_AUTO_SUBSCRIBE,
    ) -> WebhookSyncResult:
        """Idempotently ensure the webhook subscriptions for ``url``.

        Defaults to the ``CDEK_WEBHOOK_AUTO_SUBSCRIBE`` set (ORDER_STATUS
        + ORDER_MODIFIED) — the same sync the registry bootstrap runs.
        """
        return await ensure_webhook_subscriptions(self.client, url, types)
