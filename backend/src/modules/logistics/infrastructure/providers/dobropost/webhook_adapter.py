"""DobroPost webhook adapter — implements ``IWebhookAdapter``.

DobroPost posts webhooks to a single URL but in **two distinct payload
formats** (see ``docs/dobropost_shipment_api/webhooks.md``):

* **Format №1 — passport validation:** carries
  ``passportValidationStatus: bool``. Currently NOT routed through
  ``IngestTrackingHandler`` — adapter returns ``[]`` and emits a
  warning log so the failed-passport flow can be wired through a
  dedicated consumer when the customer-service module is built. The
  webhook router still ACKs to avoid retry storms.

* **Format №2 — status update:** carries ``DPTrackNumber`` + ``status``
  string. Adapter resolves ``status`` text → numeric ``status_id`` and
  produces a unified ``TrackingEvent``. Information-only ids (270/271/
  272 — edit-shipment workflow) are filtered out at the mapper.

Authentication: DobroPost does not sign payloads; the adapter relies on
shared-secret in ``X-Webhook-Secret`` header (or ``secret`` query param)
plus optional IP allow-list — same pattern as ``CdekWebhookAdapter``.
"""

from __future__ import annotations

import hmac
import ipaddress
import json
import logging
from typing import Any

from src.modules.logistics.domain.value_objects import (
    PROVIDER_DOBROPOST,
    ProviderCode,
    TrackingEvent,
)
from src.modules.logistics.infrastructure.providers.dobropost.mappers import (
    parse_status_update_event,
)

logger = logging.getLogger(__name__)


class DobroPostWebhookAdapter:
    """DobroPost implementation of ``IWebhookAdapter``."""

    def __init__(
        self,
        *,
        webhook_secret: str | None = None,
        allowed_ips: list[str] | None = None,
    ) -> None:
        self._webhook_secret = webhook_secret or ""
        self._allowed_ips = list(allowed_ips or [])
        self._allow_all_ips = "*" in self._allowed_ips
        self._allowed_networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        for entry in self._allowed_ips:
            if entry == "*":
                continue
            try:
                self._allowed_networks.append(ipaddress.ip_network(entry, strict=False))
            except ValueError:
                continue

    def provider_code(self) -> ProviderCode:
        return PROVIDER_DOBROPOST

    async def validate_signature(
        self,
        headers: dict[str, str],
        body: bytes,
    ) -> bool:
        """Validate via shared secret OR IP allow-list (same shape as CDEK).

        Returns ``False`` when no auth source is configured — operators
        must explicitly opt out via ``allowed_ips=["*"]``.
        """
        if not self._webhook_secret and not self._allowed_ips:
            return False

        if self._webhook_secret and not self._validate_secret(headers):
            return False
        return not (self._allowed_ips and not self._validate_ip(headers))

    async def parse_events(
        self,
        body: bytes,
    ) -> list[tuple[str, list[TrackingEvent]]]:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError, ValueError:
            logger.warning(
                "DobroPost webhook: malformed JSON body (%d bytes)", len(body)
            )
            return []

        if not isinstance(payload, dict):
            logger.warning("DobroPost webhook: top-level payload is not a JSON object")
            return []

        # Format №1 — passport validation
        if "passportValidationStatus" in payload:
            self._handle_passport_validation(payload)
            return []

        # Format №2 — status update
        if "DPTrackNumber" in payload and "status" in payload:
            return self._handle_status_update(payload)

        logger.warning(
            "DobroPost webhook: unrecognised payload shape (keys=%s)",
            sorted(payload.keys()),
        )
        return []

    # ------------------------------------------------------------------ #
    # Internals                                                            #
    # ------------------------------------------------------------------ #

    def _handle_passport_validation(self, payload: dict[str, Any]) -> None:
        """Surface passport-validation outcome via structured log.

        Adapter cannot mutate the ``Shipment`` directly here — it has
        no DB session (APP scope). Persistence happens through
        :class:`HandleDobroPostPassportValidationHandler`, dispatched
        by the webhook router after the adapter detects this payload
        shape (see :py:meth:`is_passport_validation_payload` and the
        router's special-cased branch).

        The structured log below stays as a low-level audit trail —
        the operator-visible action is driven by the
        :class:`ShipmentPassportValidationFailedEvent` outbox event
        emitted from the handler.
        """
        shipment_id = payload.get("shipmentId")
        is_valid = bool(payload.get("passportValidationStatus"))
        if is_valid:
            logger.info(
                "DobroPost passport validation passed",
                extra={
                    "dp_id": shipment_id,
                    "status_date": payload.get("statusDate"),
                },
            )
            return
        logger.error(
            "DobroPost passport validation FAILED",
            extra={
                "dp_id": shipment_id,
                "status_date": payload.get("statusDate"),
            },
        )

    def _handle_status_update(
        self, payload: dict[str, Any]
    ) -> list[tuple[str, list[TrackingEvent]]]:
        shipment_id = payload.get("shipmentId")
        if shipment_id is None:
            logger.warning("DobroPost status webhook missing 'shipmentId'")
            return []
        event = parse_status_update_event(payload)
        if event is None:
            return []
        return [(str(shipment_id), [event])]

    def _validate_secret(self, headers: dict[str, Any]) -> bool:
        if not self._webhook_secret:
            return True
        normalized = {k.lower(): v for k, v in headers.items()}
        candidate = (
            normalized.get("x-webhook-secret")
            or normalized.get("x-dobropost-secret")
            or ""
        )
        if not isinstance(candidate, str):
            return False
        return hmac.compare_digest(candidate, self._webhook_secret)

    def _validate_ip(self, headers: dict[str, Any]) -> bool:
        if not self._allowed_ips:
            return True
        if self._allow_all_ips:
            return True
        client_ip = self._extract_client_ip(headers)
        if client_ip is None:
            return False
        try:
            parsed = ipaddress.ip_address(client_ip)
        except ValueError:
            return False
        return any(parsed in network for network in self._allowed_networks)

    @staticmethod
    def _extract_client_ip(headers: dict[str, Any]) -> str | None:
        normalized = {k.lower(): v for k, v in headers.items()}
        for key in ("x-forwarded-for", "x-real-ip", "x-original-forwarded-for"):
            raw = normalized.get(key)
            if not raw:
                continue
            first = str(raw).split(",", 1)[0].strip()
            if first:
                return first
        return None
