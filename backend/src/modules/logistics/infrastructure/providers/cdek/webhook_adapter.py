"""
CDEK webhook adapter — implements ``IWebhookAdapter``.

CDEK does NOT sign webhook payloads with HMAC. Authenticity is enforced
through two complementary mechanisms, configured at factory time:

1. **Shared secret in URL or header.** Configure ``webhook_secret`` in
   the provider account config; the adapter expects the same value in
   either the ``X-Webhook-Secret`` HTTP header or the ``secret`` query
   parameter (whichever is more convenient to register on CDEK side).
   Comparison is constant-time to prevent timing attacks.

2. **Optional IP whitelist.** Provide ``allowed_ips`` (list of CIDR
   strings or exact IPs) in the config to restrict the source. The
   adapter checks the first entry of ``X-Forwarded-For`` (or the
   ``X-Real-Ip`` header), falling back to ``X-Original-Forwarded-For``.

When neither secret nor whitelist is configured the adapter rejects all
webhooks — explicit opt-out (e.g. for local testing) requires setting
``webhook_secret = ""`` AND ``allowed_ips = ["*"]``, signalling that
the operator has consciously disabled authentication.
"""

from __future__ import annotations

import hmac
import ipaddress
from typing import Any

from src.modules.logistics.domain.value_objects import (
    PROVIDER_CDEK,
    ProviderCode,
    TrackingEvent,
)
from src.modules.logistics.infrastructure.providers.cdek.mappers import (
    parse_webhook_body,
)


class CdekWebhookAdapter:
    """CDEK implementation of ``IWebhookAdapter``."""

    def __init__(
        self,
        *,
        webhook_secret: str | None = None,
        allowed_ips: list[str] | None = None,
    ) -> None:
        self._webhook_secret = webhook_secret or ""
        self._allowed_ips = list(allowed_ips or [])
        self._allow_all_ips = "*" in self._allowed_ips
        # Pre-parse CIDR networks once for fast lookup.
        self._allowed_networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        for entry in self._allowed_ips:
            if entry == "*":
                continue
            try:
                self._allowed_networks.append(ipaddress.ip_network(entry, strict=False))
            except ValueError:
                # Skip malformed entries — log via the calling layer.
                continue

    def provider_code(self) -> ProviderCode:
        return PROVIDER_CDEK

    async def validate_signature(
        self,
        headers: dict[str, str],
        body: bytes,
    ) -> bool:
        """Validate webhook authenticity via shared secret and/or IP whitelist.

        Returns ``True`` only when at least one configured authentication
        signal (secret or IP whitelist) succeeds. Empty configuration is
        treated as a failed check — operators must explicitly opt out by
        setting ``allowed_ips=["*"]``.
        """
        secret_ok = self._validate_secret(headers)
        ip_ok = self._validate_ip(headers)

        if not self._webhook_secret and not self._allowed_ips:
            return False

        if self._webhook_secret and not secret_ok:
            return False
        return not (self._allowed_ips and not ip_ok)

    async def parse_events(
        self,
        body: bytes,
    ) -> list[tuple[str, list[TrackingEvent]]]:
        return parse_webhook_body(body)

    # ------------------------------------------------------------------ #
    # Internals                                                            #
    # ------------------------------------------------------------------ #

    def _validate_secret(self, headers: dict[str, Any]) -> bool:
        if not self._webhook_secret:
            return True  # not configured → caller decides via _allowed_ips
        normalized = {k.lower(): v for k, v in headers.items()}
        candidate = (
            normalized.get("x-webhook-secret")
            or normalized.get("x-cdek-secret")
            or ""
        )
        if not isinstance(candidate, str):
            return False
        return hmac.compare_digest(candidate, self._webhook_secret)

    def _validate_ip(self, headers: dict[str, Any]) -> bool:
        if not self._allowed_ips:
            return True  # not configured
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
            # X-Forwarded-For may carry "client, proxy1, proxy2"
            first = str(raw).split(",", 1)[0].strip()
            if first:
                return first
        return None
