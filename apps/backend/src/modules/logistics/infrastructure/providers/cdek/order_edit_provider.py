"""
CDEK order-edit provider — CDEK-specific order modification.

CDEK exposes order editing via ``PATCH /v2/orders`` («Изменение
заказа»), valid only while the order has not moved off the sender
warehouse (status «Создан» / «Принят»). Unlike Yandex Delivery there is
no async edit-task pipeline — the PATCH is accepted (202) and processed
the same way order creation is, so this is intentionally **not** wired
through the carrier-agnostic ``IEditProvider`` port (whose contract is
shaped around Yandex's ``EditTaskResult`` / ``get_edit_status`` poll
loop). It is a CDEK-local capability reached from the CDEK admin router.

CDEK's ``OrderUpdateRequestDto`` requires ``type`` + ``recipient`` plus
the order identifier (``uuid`` or ``cdek_number``) on every call, even
for a one-field change — the caller assembles the full update body (the
admin schema in the presentation layer validates its shape).
"""

from __future__ import annotations

import json

import attrs
import structlog

from src.modules.logistics.domain.value_objects import PROVIDER_CDEK, ProviderCode
from src.modules.logistics.infrastructure.providers.cdek.client import CdekClient
from src.modules.logistics.infrastructure.providers.errors import ProviderHTTPError

logger = structlog.get_logger(__name__)


@attrs.define(frozen=True)
class CdekEditResult:
    """Outcome of a CDEK ``PATCH /v2/orders`` call.

    CDEK accepts the edit asynchronously (202 + ``requests[]``); ``state``
    carries the CDEK request lifecycle (``ACCEPTED`` / ``WAITING`` /
    ``SUCCESSFUL`` / ``INVALID``). ``success`` is ``False`` only when the
    request was rejected outright (``INVALID`` or an HTTP error) — an
    ``ACCEPTED`` edit is a success from the caller's point of view; the
    final result is observed by re-reading the order.
    """

    success: bool
    request_uuid: str | None = None
    state: str | None = None
    reason: str | None = None
    raw_response: str | None = None


# CDEK OrderUpdateRequestDto fields required on every call (besides the
# order identifier, checked separately).
_REQUIRED_UPDATE_FIELDS = ("type", "recipient")


class CdekOrderEditProvider:
    """CDEK-specific order-edit capability (``PATCH /v2/orders``)."""

    def __init__(self, client: CdekClient) -> None:
        self._client = client

    def provider_code(self) -> ProviderCode:
        return PROVIDER_CDEK

    async def edit_order(self, update_body: dict) -> CdekEditResult:
        """Apply a partial update to an existing CDEK order.

        ``update_body`` is a CDEK ``OrderUpdateRequestDto`` — it must
        carry the order identifier (``uuid`` or ``cdek_number``) plus
        the always-required ``type`` and ``recipient`` blocks. Raises
        ``ValueError`` when those are missing so the caller fails fast
        instead of getting an opaque CDEK 400.
        """
        if not update_body.get("uuid") and not update_body.get("cdek_number"):
            raise ValueError(
                "CDEK order edit requires 'uuid' or 'cdek_number' in update_body"
            )
        missing = [f for f in _REQUIRED_UPDATE_FIELDS if not update_body.get(f)]
        if missing:
            raise ValueError(
                "CDEK order edit requires "
                f"{', '.join(_REQUIRED_UPDATE_FIELDS)} — missing: "
                f"{', '.join(missing)}"
            )

        try:
            data = await self._client.update_order(update_body)
        except ProviderHTTPError as exc:
            logger.warning(
                "cdek_order_edit_http_error",
                order=update_body.get("uuid") or update_body.get("cdek_number"),
                error=str(exc),
            )
            return CdekEditResult(
                success=False, reason=str(exc), raw_response=exc.response_body
            )

        return _parse_update_response(data)


def _parse_update_response(data: dict) -> CdekEditResult:
    """Translate a CDEK ``PATCH /v2/orders`` 202 envelope into a result."""
    raw = json.dumps(data, ensure_ascii=False, default=str)
    requests = data.get("requests", []) if isinstance(data, dict) else []
    update_reqs = [r for r in requests if isinstance(r, dict)]

    # CDEK echoes the request history; the freshest ``UPDATE`` entry is
    # the one this call produced. Fall back to the last entry when the
    # type tag is absent.
    target: dict | None = None
    for req in update_reqs:
        if req.get("type") == "UPDATE":
            target = req
    if target is None and update_reqs:
        target = update_reqs[-1]

    if target is None:
        # No request envelope — a bare 202 + entity. Treat as accepted.
        return CdekEditResult(success=True, raw_response=raw)

    state = target.get("state")
    request_uuid = target.get("request_uuid")
    if state == "INVALID":
        errors = target.get("errors", [])
        reason = "; ".join(
            f"{e.get('code', '')}: {e.get('message', '')}"
            for e in errors
            if isinstance(e, dict)
        )
        return CdekEditResult(
            success=False,
            request_uuid=request_uuid,
            state=state,
            reason=reason or "INVALID",
            raw_response=raw,
        )
    return CdekEditResult(
        success=True,
        request_uuid=request_uuid,
        state=state,
        raw_response=raw,
    )
