"""DobroPost HTTP client — typed wrapper around BaseProviderClient.

Covers the 5 endpoints documented in
``docs/dobropost_shipment_api/reference.md``:

* ``POST /api/shipment``         — create shipment
* ``GET /api/shipment``          — list shipments (paged + status filter)
* ``PUT /api/shipment``          — update shipment (passport correction)
* ``DELETE /api/shipment/{id}``  — delete shipment (not used in production)

Auth is delegated to ``DobroPostAuthManager`` (email/password → 12h JWT).
"""

from __future__ import annotations

from typing import Any

from src.modules.logistics.infrastructure.providers.base_client import (
    BaseProviderClient,
    ProviderClientConfig,
)
from src.modules.logistics.infrastructure.providers.dobropost.auth import (
    DobroPostAuthManager,
)
from src.modules.logistics.infrastructure.providers.dobropost.constants import (
    DOBROPOST_SHIPMENT_PATH,
)


class DobroPostClient:
    """DobroPost API client.

    Composes ``BaseProviderClient`` for retry / timeout / structured
    logging, and exposes typed methods per endpoint.
    """

    def __init__(
        self,
        base_url: str,
        email: str,
        password: str,
        *,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self._auth = DobroPostAuthManager(
            base_url=base_url, email=email, password=password
        )
        self._provider_client = BaseProviderClient(
            auth_manager=self._auth,
            config=ProviderClientConfig(
                base_url=base_url,
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
            ),
        )

    async def __aenter__(self) -> DobroPostClient:
        await self._provider_client.__aenter__()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self._provider_client.__aexit__(*exc)

    async def close(self) -> None:
        """Release the underlying httpx connection pool. Idempotent."""
        await self._provider_client.close()

    # ------------------------------------------------------------------ #
    # Shipments                                                           #
    # ------------------------------------------------------------------ #

    async def create_shipment(self, body: dict[str, Any]) -> dict[str, Any]:
        """POST /api/shipment — create a new shipment.

        Non-idempotent (no client-supplied key on DobroPost side); base
        client will NOT retry 5xx — caller must surface the failure.
        """
        resp = await self._provider_client.request(
            "POST", DOBROPOST_SHIPMENT_PATH, json=body
        )
        return resp.json()

    async def list_shipments(self, params: dict[str, Any]) -> dict[str, Any]:
        """GET /api/shipment — paged list filtered by ``statusId``.

        Returns the raw envelope ``{content: [...], total, ...}``.
        """
        resp = await self._provider_client.request(
            "GET", DOBROPOST_SHIPMENT_PATH, params=params
        )
        return resp.json()

    async def update_shipment(self, body: dict[str, Any]) -> dict[str, Any]:
        """PUT /api/shipment — update an existing shipment.

        Identification is by ``incomingDeclaration`` (China track) per
        DobroPost contract — body shape identical to ``create_shipment``.
        Idempotent on contract — base client retries 5xx for PUT.
        """
        resp = await self._provider_client.request(
            "PUT", DOBROPOST_SHIPMENT_PATH, json=body
        )
        return resp.json()

    async def delete_shipment(self, shipment_id: int) -> dict[str, Any] | None:
        """DELETE /api/shipment/{id} — cancel/delete a shipment.

        Loyality does NOT use this in production (cancellation lives in
        Order ``CANCELLED + REFUND`` flow). Kept for completeness and
        admin diagnostic tooling.

        Returns ``None`` when the carrier replies with an empty body
        (typical for ``204 No Content``); a structured response is
        returned verbatim otherwise.
        """
        resp = await self._provider_client.request(
            "DELETE", f"{DOBROPOST_SHIPMENT_PATH}/{shipment_id}"
        )
        if not resp.content:
            return None
        return resp.json()
