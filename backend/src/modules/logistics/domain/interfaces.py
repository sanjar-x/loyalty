"""
Logistics domain interfaces (ports).

Capability protocols for provider adapters, plus registry, routing,
webhook, polling, factory, and repository ports.
Part of the domain layer — zero framework imports.
"""

import uuid
from typing import Any, Protocol

from src.modules.logistics.domain.entities import Shipment
from src.modules.logistics.domain.provider_account import ProviderAccount
from src.modules.logistics.domain.value_objects import (
    ActualDeliveryInfo,
    Address,
    BookingRequest,
    BookingResult,
    CancelResult,
    ClientReturnRequest,
    DeliveryInterval,
    DeliveryQuote,
    DocumentResult,
    EditItemMarking,
    EditItemRemoval,
    EditOrderRequest,
    EditPackage,
    EditTaskResult,
    EditTaskStatus,
    IntakeRequest,
    IntakeResult,
    IntakeStatus,
    IntakeWindow,
    Parcel,
    PickupPoint,
    PickupPointQuery,
    ProviderCode,
    RefusalRequest,
    ReturnResult,
    ReverseAvailabilityRequest,
    ReverseAvailabilityResult,
    TrackingEvent,
)

# ---------------------------------------------------------------------------
# Capability protocols — one per logistics operation category
# ---------------------------------------------------------------------------


class IRateProvider(Protocol):
    """Calculates shipping rates / tariffs for a given route and parcels.

    Returns ``DeliveryQuote`` objects so that each provider can embed
    opaque booking data (``provider_payload``) and expiry times.
    """

    def provider_code(self) -> ProviderCode: ...

    async def calculate_rates(
        self,
        origin: Address,
        destination: Address,
        parcels: list[Parcel],
    ) -> list[DeliveryQuote]: ...


class IBookingProvider(Protocol):
    """Creates and cancels shipment bookings with a logistics provider."""

    def provider_code(self) -> ProviderCode: ...

    async def book_shipment(self, request: BookingRequest) -> BookingResult: ...

    async def cancel_shipment(self, provider_shipment_id: str) -> CancelResult: ...


class ITrackingProvider(Protocol):
    """Retrieves tracking events for a booked shipment."""

    def provider_code(self) -> ProviderCode: ...

    async def get_tracking(self, provider_shipment_id: str) -> list[TrackingEvent]: ...


class ITrackingPollProvider(Protocol):
    """Batch-polls tracking events for multiple shipments.

    Used by background sync tasks for providers without webhooks
    (e.g. Russian Post). Each provider adapter maps native statuses
    to unified ``TrackingEvent`` objects.
    """

    def provider_code(self) -> ProviderCode: ...

    async def poll_tracking_batch(
        self, provider_shipment_ids: list[str]
    ) -> dict[str, list[TrackingEvent]]: ...


class IPickupPointProvider(Protocol):
    """Lists pickup / delivery points from a logistics provider."""

    def provider_code(self) -> ProviderCode: ...

    async def list_pickup_points(
        self, query: PickupPointQuery
    ) -> list[PickupPoint]: ...


class IDocumentProvider(Protocol):
    """Generates shipping labels and documents."""

    def provider_code(self) -> ProviderCode: ...

    async def get_label(self, provider_shipment_id: str) -> DocumentResult: ...


class IIntakeProvider(Protocol):
    """Manages courier-pickup intakes (CDEK ``/v2/intakes``).

    Workflow:
    1. ``get_available_days`` — list dates the courier can collect from
       the sender's address.
    2. ``create_intake`` — register a pickup request for one of those dates.
    3. ``get_intake`` — poll status (ACCEPTED → WAITING → COMPLETED).
    4. ``cancel_intake`` — cancel before the courier arrives.
    """

    def provider_code(self) -> ProviderCode: ...

    async def get_available_days(
        self,
        from_address: Address,
        until: str | None = None,
    ) -> list[IntakeWindow]: ...

    async def create_intake(self, request: IntakeRequest) -> IntakeResult: ...

    async def get_intake(self, provider_intake_id: str) -> IntakeStatus: ...

    async def cancel_intake(self, provider_intake_id: str) -> bool: ...


class IDeliveryScheduleProvider(Protocol):
    """Returns available delivery time-slots for a shipment.

    CDEK exposes two endpoints:
    - ``/v2/delivery/intervals`` — slots for an *existing* booked order.
    - ``/v2/delivery/estimatedIntervals`` — pre-booking estimate (used
      by the storefront before the user confirms the cart).

    Yandex additionally surfaces ``/request/actual_info`` which returns
    the carrier-confirmed window (date + interval) for an in-flight
    shipment — exposed via :py:meth:`get_actual_delivery_info`. CDEK
    has no equivalent and the adapter returns ``None``.
    """

    def provider_code(self) -> ProviderCode: ...

    async def get_intervals(
        self,
        provider_shipment_id: str,
    ) -> list[DeliveryInterval]: ...

    async def get_estimated_intervals(
        self,
        origin: Address,
        destination: Address,
        tariff_code: int,
    ) -> list[DeliveryInterval]: ...

    async def get_actual_delivery_info(
        self,
        provider_shipment_id: str,
    ) -> ActualDeliveryInfo | None: ...


class IReturnProvider(Protocol):
    """Handles client returns, refusals, and reverse-shipment validation.

    - ``register_client_return`` — recipient sends the order back.
    - ``register_refusal`` — recipient refuses delivery on the doorstep.
    - ``check_reverse_availability`` — pre-flight check whether a reverse
      shipment route is feasible for the given direction / tariff /
      contacts. Run *before* the original order is created to surface
      "no reverse path" early in the checkout flow.
    """

    def provider_code(self) -> ProviderCode: ...

    async def register_client_return(
        self,
        request: ClientReturnRequest,
    ) -> ReturnResult: ...

    async def register_refusal(self, request: RefusalRequest) -> ReturnResult: ...

    async def check_reverse_availability(
        self,
        request: ReverseAvailabilityRequest,
    ) -> ReverseAvailabilityResult: ...


class IEditProvider(Protocol):
    """Edits an existing provider order via async edit-task workflow.

    Yandex Delivery exposes four mutation endpoints + one status
    endpoint:

    - ``POST /request/edit`` — recipient / destination / package swap.
    - ``POST /request/places/edit`` — full replacement of package layout.
    - ``POST /request/items-instances/edit`` — per-item article + marking.
    - ``POST /request/items/remove`` — reduce / remove items.
    - ``POST /request/edit/status`` — poll an editing task by id.

    All mutation endpoints return an ``EditTaskResult`` (a ticket); the
    caller polls :py:meth:`get_edit_status` until the task reaches a
    terminal status (``SUCCESS`` / ``FAILURE``). CDEK has no equivalent
    workflow and its factory returns ``None``.
    """

    def provider_code(self) -> ProviderCode: ...

    async def edit_order(self, request: EditOrderRequest) -> EditTaskResult: ...

    async def edit_packages(
        self,
        order_provider_id: str,
        packages: list[EditPackage],
    ) -> EditTaskResult: ...

    async def edit_items_instances(
        self,
        order_provider_id: str,
        items: list[EditItemMarking],
    ) -> EditTaskResult: ...

    async def remove_items(
        self,
        order_provider_id: str,
        items: list[EditItemRemoval],
    ) -> EditTaskResult: ...

    async def get_edit_status(self, task_id: str) -> EditTaskStatus: ...


# ---------------------------------------------------------------------------
# Webhook adapter — provider-specific payload parsing + verification
# ---------------------------------------------------------------------------


class IWebhookAdapter(Protocol):
    """Parses and verifies inbound webhooks from a logistics provider.

    Each provider has its own webhook format and signature scheme.
    The adapter validates authenticity and extracts unified tracking
    events that can be fed into ``IngestTrackingHandler``.
    """

    def provider_code(self) -> ProviderCode: ...

    async def validate_signature(
        self,
        headers: dict[str, str],
        body: bytes,
    ) -> bool:
        """Return True if the webhook payload signature is valid."""
        ...

    async def parse_events(
        self,
        body: bytes,
    ) -> list[tuple[str, list[TrackingEvent]]]:
        """Parse the webhook body into (provider_shipment_id, events) pairs.

        Returns a list of tuples, each mapping a provider shipment ID
        to the tracking events extracted from the payload. One webhook
        may carry updates for multiple shipments.
        """
        ...


# ---------------------------------------------------------------------------
# Provider factory — creates account-bound adapters from stored config
# ---------------------------------------------------------------------------


class IProviderFactory(Protocol):
    """Creates provider adapters bound to a specific account/credentials.

    Each logistics provider ships a factory that knows how to wire up
    auth managers, HTTP clients, and adapter implementations from the
    stored ``ProviderAccountConfig``.

    Not all capabilities need to be supported — unsupported ones return
    ``None``.
    """

    def provider_code(self) -> ProviderCode: ...

    def create_rate_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IRateProvider | None: ...

    def create_booking_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IBookingProvider | None: ...

    def create_tracking_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> ITrackingProvider | None: ...

    def create_tracking_poll_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> ITrackingPollProvider | None: ...

    def create_pickup_point_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IPickupPointProvider | None: ...

    def create_document_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IDocumentProvider | None: ...

    def create_webhook_adapter(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IWebhookAdapter | None: ...

    def create_intake_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IIntakeProvider | None: ...

    def create_delivery_schedule_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IDeliveryScheduleProvider | None: ...

    def create_return_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IReturnProvider | None: ...

    def create_edit_provider(
        self, credentials: dict[str, Any], config: dict[str, Any] | None = None
    ) -> IEditProvider | None: ...

    async def close(self) -> None:
        """Close all cached HTTP clients held by this factory.

        Called at app shutdown so ``httpx.AsyncClient`` connection pools
        are released cleanly. Idempotent — subsequent calls are no-ops.
        """
        ...


# ---------------------------------------------------------------------------
# Registry — stores and retrieves provider adapters by ProviderCode
# ---------------------------------------------------------------------------


class IShippingProviderRegistry(Protocol):
    """Registry of logistics provider adapters, keyed by ProviderCode."""

    def get_rate_provider(self, code: ProviderCode) -> IRateProvider: ...

    def get_booking_provider(self, code: ProviderCode) -> IBookingProvider: ...

    def get_tracking_provider(self, code: ProviderCode) -> ITrackingProvider: ...

    def get_tracking_poll_provider(
        self, code: ProviderCode
    ) -> ITrackingPollProvider: ...

    def get_pickup_point_provider(self, code: ProviderCode) -> IPickupPointProvider: ...

    def get_document_provider(self, code: ProviderCode) -> IDocumentProvider: ...

    def get_webhook_adapter(self, code: ProviderCode) -> IWebhookAdapter: ...

    def has_webhook_adapter(self, code: ProviderCode) -> bool: ...

    def list_rate_providers(self) -> list[IRateProvider]: ...

    def list_pickup_point_providers(self) -> list[IPickupPointProvider]: ...

    def list_tracking_poll_providers(self) -> list[ITrackingPollProvider]: ...

    def get_intake_provider(self, code: ProviderCode) -> IIntakeProvider: ...

    def get_delivery_schedule_provider(
        self, code: ProviderCode
    ) -> IDeliveryScheduleProvider: ...

    def get_return_provider(self, code: ProviderCode) -> IReturnProvider: ...

    def get_edit_provider(self, code: ProviderCode) -> IEditProvider: ...

    @property
    def registered_provider_codes(self) -> set[ProviderCode]: ...

    async def reset(self) -> None:
        """Tear down every registered provider and clear all dicts.

        Used by the admin refresh path so the same APP-scoped registry
        instance can be repopulated against the current DB state.
        """
        ...


# ---------------------------------------------------------------------------
# Routing policy — determines eligible providers for a given route
# ---------------------------------------------------------------------------


class IProviderRoutingPolicy(Protocol):
    """Determines which providers can serve a given route + parcels."""

    async def get_eligible_providers(
        self,
        origin: Address,
        destination: Address,
        parcels: list[Parcel],
    ) -> list[ProviderCode]: ...


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------


class IShipmentRepository(Protocol):
    """Persistence port for Shipment aggregates."""

    async def add(self, shipment: Shipment) -> Shipment: ...

    async def get_by_id(self, shipment_id: uuid.UUID) -> Shipment | None: ...

    async def get_by_provider_shipment_id(
        self,
        provider_code: ProviderCode,
        provider_shipment_id: str,
    ) -> Shipment | None: ...

    async def update(self, shipment: Shipment) -> Shipment: ...

    async def list_with_pending_edit_tasks(
        self, *, limit: int = 100
    ) -> list[Shipment]: ...

    """Return shipments that have at least one outstanding edit task.

    Used by the edit-task poller to discover work — much cheaper than
    scanning every shipment when only a handful are mid-mutation.
    """


class IDeliveryQuoteRepository(Protocol):
    """Persistence port for server-side delivery quotes.

    Quotes are stored after rate calculation and looked up when
    creating a shipment to ensure price/payload integrity.
    """

    async def add(self, quote: DeliveryQuote) -> DeliveryQuote: ...

    async def get_by_id(self, quote_id: uuid.UUID) -> DeliveryQuote | None: ...

    async def delete_expired(self) -> int: ...


class IProviderAccountRepository(Protocol):
    """Persistence port for ``ProviderAccount`` aggregates.

    Backs the admin CRUD endpoints under ``/admin/logistics/provider-accounts``.
    Bootstrap-time loads (``bootstrap_registry``) read the ORM directly
    for performance — this port is only used by write paths and read
    queries that need domain-level invariants.
    """

    async def add(self, account: ProviderAccount) -> ProviderAccount: ...

    async def get_by_id(self, account_id: uuid.UUID) -> ProviderAccount | None: ...

    async def get_active_by_provider_code(
        self, provider_code: ProviderCode
    ) -> ProviderAccount | None:
        """Return the single active row for ``provider_code``, if any.

        Multiple inactive rows are allowed (for staging credential
        rotations), so callers must distinguish "no active row" from
        "no rows at all".
        """
        ...

    async def list_all(self) -> list[ProviderAccount]: ...

    async def update(self, account: ProviderAccount) -> ProviderAccount: ...

    async def delete(self, account_id: uuid.UUID) -> bool: ...


# ---------------------------------------------------------------------------
# SKU weight resolver (anti-corruption port → catalog + pricing)
# ---------------------------------------------------------------------------


class IPickupPointResolver(Protocol):
    """Resolve a previously-listed pickup point back to its full ``PickupPoint``.

    Checkout flow needs this when the user clicks a marker on the map:
    the frontend only knows ``(provider_code, external_id)`` and asks the
    backend to compute a delivery quote against that point. Re-fetching
    the entire province-wide pickup list per click would melt the
    provider's API, so the implementation caches a recent ``/pickup-points``
    response (typically Redis with a 24 h TTL) and reads from it.

    Returns ``None`` when the cache holds no record for the
    ``(provider_code, external_id)`` pair — callers should respond with a
    400/404 explaining that the point must be listed via ``/pickup-points``
    first (the frontend always does this before letting the user click).
    """

    async def resolve(
        self,
        provider_code: ProviderCode,
        external_id: str,
    ) -> PickupPoint | None: ...

    async def remember_many(self, points: list[PickupPoint]) -> None:
        """Persist a list of points so subsequent ``resolve`` lookups hit.

        Called from ``ListPickupPointsHandler`` after a successful provider
        fan-out. Implementations swallow backend failures so a Redis
        outage does not break pickup-point listing — quotes against any
        cached-but-now-expired point will fall back to a re-fetch path.
        """
        ...


class IOriginAddressResolver(Protocol):
    """Resolve the sender warehouse address for a given provider.

    The marketplace ships from a fixed RF warehouse, so per-provider
    origin parameters (CDEK ``cdek_pvz_code`` / ``cdek_city_code`` /
    ``fias_guid``, Yandex ``platform_station_id``) are configured once
    on ``ProviderAccountModel.config_json`` and reused for every quote.

    Raises ``ProviderUnavailableError`` (or returns ``None``) when the
    provider has no configured origin — the operator forgot to fill it
    in admin and the entire provider is unusable for outbound shipments.
    """

    async def resolve(self, provider_code: ProviderCode) -> Address: ...


class ISkuWeightResolver(Protocol):
    """Resolve estimated per-unit weight (in grams) for a list of SKUs.

    The marketplace dropships from China — actual physical weight is
    unknown until parcels arrive at the RF warehouse. To still let the
    customer see a delivery price during checkout, we fall back to a
    *category-level* average weight, configured in the pricing module
    (``CategoryPricingSettings.values["weight_g"]``).

    Implementations are infrastructure-only (read-side adapter), allowed
    by the boundary-test whitelist to JOIN catalog + pricing ORM. The
    domain depends on this protocol so ``CalculateRatesHandler`` can
    build ``Parcel`` objects without leaking module internals.
    """

    async def resolve_weight_grams(
        self, sku_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, int]:
        """Return per-SKU weight in grams.

        Resolution order, per SKU:
        1. ``CategoryPricingSettings.values["weight_g"]`` for the SKU's
           ``Product.primary_category_id`` and the active pricing context.
        2. ``Variable[code="weight_g"].default_value`` (system fallback,
           ``500`` g per the seed).

        Missing SKUs (deleted / never existed) are simply omitted from
        the result map — callers decide whether to error or skip.
        """
        ...
