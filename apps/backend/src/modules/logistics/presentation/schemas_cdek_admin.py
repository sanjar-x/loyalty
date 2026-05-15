"""
Admin REST schemas for the CDEK-specific surface
(``/admin/logistics/cdek``).

Kept separate from ``schemas_admin.py`` (provider accounts) and
``schemas.py`` (the carrier-agnostic checkout contract): these endpoints
are a thin operator-facing proxy over CDEK's own API, whose request /
response DTOs are CDEK's contract — not ours. Rather than mirror ~50
CDEK DTOs (which would drift from CDEK's spec), the bodies are passed
through under a single ``payload`` envelope and responses are wrapped in
``CdekJsonResponse`` with CDEK's ``errors`` / ``warnings`` lifted out for
visibility. The shapes inside ``payload`` / ``data`` follow the CDEK API
v2 documentation verbatim.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from src.shared.schemas import CamelModel


class CdekRawPayloadRequest(CamelModel):
    """Generic body wrapper for CDEK passthrough endpoints.

    ``payload`` is a CDEK API request body (``OrderUpdateRequestDto``,
    ``ScheduleDto``, ``RegisterPrealertRequestDto``,
    ``RestrictionHintsRequestDto``, ``PhotoRequestDto``,
    ``IntakeChangeStatusDto``, ...) forwarded verbatim. The admin UI
    builds it from the CDEK documentation; backend does not re-validate
    CDEK's schema — CDEK is the source of truth and returns structured
    errors of its own.
    """

    payload: dict[str, Any] = Field(
        description="CDEK API request body, forwarded to CDEK verbatim.",
    )


class CdekJsonResponse(CamelModel):
    """Generic envelope for CDEK JSON responses.

    CDEK's ``errors`` / ``warnings`` arrays (when present) are lifted out
    of the raw payload so the admin UI can surface them uniformly; the
    rest of the response stays under ``data`` exactly as CDEK returned
    it. For list-returning endpoints (location lookups) ``data`` is the
    list and ``errors`` / ``warnings`` are ``None``.
    """

    data: Any = Field(description="CDEK response payload, as returned by CDEK.")
    errors: list[dict[str, Any]] | None = Field(
        default=None, description="CDEK error entries, if any."
    )
    warnings: list[dict[str, Any]] | None = Field(
        default=None, description="CDEK warning entries, if any."
    )

    @classmethod
    def from_raw(cls, raw: Any) -> CdekJsonResponse:
        """Wrap a raw CDEK response, lifting out ``errors`` / ``warnings``."""
        if isinstance(raw, dict):
            errors = raw.get("errors")
            warnings = raw.get("warnings")
            return cls(
                data=raw,
                errors=errors if isinstance(errors, list) else None,
                warnings=warnings if isinstance(warnings, list) else None,
            )
        return cls(data=raw, errors=None, warnings=None)


class CdekEditOrderResponse(CamelModel):
    """Result of a CDEK ``PATCH /v2/orders`` edit.

    CDEK accepts the edit asynchronously — ``state`` carries the CDEK
    request lifecycle (``ACCEPTED`` / ``WAITING`` / ``SUCCESSFUL`` /
    ``INVALID``). ``success`` is ``False`` only on outright rejection;
    an ``ACCEPTED`` edit is a success pending an order re-read.
    """

    success: bool
    state: str | None = None
    request_uuid: str | None = None
    reason: str | None = None


class CdekWebhookSubscriptionRequest(CamelModel):
    """Body for ``POST /admin/logistics/cdek/webhooks`` — one subscription.

    ``type`` must be one of the CDEK ``WebhookDto`` enum values; the
    router validates it against ``CDEK_WEBHOOK_TYPES``.
    """

    url: str = Field(min_length=1, description="Client URL CDEK will POST events to.")
    type: str = Field(min_length=1, description="CDEK webhook event type.")


class CdekWebhookSyncRequest(CamelModel):
    """Body for ``POST /admin/logistics/cdek/webhooks/sync``.

    Idempotently ensures the auto-subscribe webhook types (ORDER_STATUS
    + ORDER_MODIFIED) are registered for ``url``, never exceeding CDEK's
    2-subscription cap.
    """

    url: str = Field(min_length=1, description="Client URL CDEK will POST events to.")


class CdekWebhookSyncResponse(CamelModel):
    """Outcome of an idempotent webhook-subscription sync."""

    existing: list[dict[str, Any]] = Field(
        description="Subscriptions CDEK reported before the sync."
    )
    created: list[str] = Field(description="Webhook types newly registered.")
    already_present: list[str] = Field(
        description="Requested types that were already subscribed."
    )
    not_created: list[str] = Field(
        description="Types skipped — registering them would exceed CDEK's "
        "2-subscription cap. Free a slot first."
    )
