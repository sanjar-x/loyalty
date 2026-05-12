"""Logistics carrier-provider HTTP client (REC-033 + REC-035).

Concrete logistics-domain layer over the shared kernel's
:class:`shared.infrastructure.http.client.BaseClient`. The
"provider" vocabulary lives here — shared kernel itself stays
domain-agnostic so payment / notification / future integrations can
sit on the same ``BaseClient`` without inheriting carrier semantics.

Today the subclass is purely nominal: it adds no methods or fields
beyond the shared base. It exists to:

* Give the architecture a clear hook for logistics-specific
  extensions (per-carrier circuit breakers, structured tags,
  carrier-error mapping) without re-spreading them across every
  CDEK / Yandex / DobroPost client.
* Preserve the existing import surface — every provider client
  already imports ``BaseProviderClient`` /``ProviderClientConfig``
  from this module, so no call-site churn.
"""

from __future__ import annotations

from shared.infrastructure.http.client import BaseClient, HttpClientConfig


class ProviderClientConfig(HttpClientConfig):
    """Logistics-flavoured alias for :class:`HttpClientConfig`.

    Inherits ``base_url`` / ``timeout_seconds`` / ``max_retries`` /
    ``retry_base_delay`` from shared. Carrier-specific knobs (e.g.
    per-provider rate-limit ceilings) extend this class going
    forward.
    """


class BaseProviderClient(BaseClient):
    """Logistics-flavoured HTTP client for carrier integrations.

    Concrete carriers (CDEK / Yandex Delivery / DobroPost) compose
    this base rather than the generic shared :class:`BaseClient` so
    the architecture has one canonical place to add carrier-wide
    cross-cutting concerns.
    """


__all__ = ["BaseProviderClient", "ProviderClientConfig"]
