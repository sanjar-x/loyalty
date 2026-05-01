"""Provider-specific input validators for ``ProviderAccount`` admin CRUD.

Surfaces hard requirements that the underlying ``IProviderFactory``
would otherwise hit only at request time. Called from
``CreateProviderAccountHandler`` / ``UpdateProviderAccountHandler`` so
the operator sees a clean ``ValidationError`` (HTTP 400) at admin
time rather than a 500 on the next request that touches the carrier.

Each validator is keyed by ``provider_code`` and gets the merged
``credentials`` + ``config`` dict. Returning ``None`` means OK; raise
``ValidationError`` to reject.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.modules.logistics.domain.value_objects import PROVIDER_DOBROPOST
from src.shared.exceptions import ValidationError


def _validate_dobropost(credentials: dict[str, Any], config: dict[str, Any]) -> None:
    """DobroPost-specific guards.

    * ``email`` / ``password`` mandatory — ``DobroPostAuthManager``
      raises ``KeyError`` on missing fields, which would surface as
      500 to the admin rather than a clean 400.
    * Either ``webhook_secret`` OR ``webhook_allowed_ips`` must be
      set: ``DobroPostWebhookAdapter.validate_signature`` rejects
      *every* inbound payload when both are blank (intentionally
      fail-closed), which would silently kill the inbound channel
      after DobroPost's retry budget exhausts.
    """
    if not credentials.get("email"):
        raise ValidationError(
            message="DobroPost credentials require non-empty 'email'",
            error_code="DOBROPOST_CREDENTIALS_INVALID",
        )
    if not credentials.get("password"):
        raise ValidationError(
            message="DobroPost credentials require non-empty 'password'",
            error_code="DOBROPOST_CREDENTIALS_INVALID",
        )

    secret = config.get("webhook_secret")
    allowed_ips = config.get("webhook_allowed_ips") or []
    if not secret and not allowed_ips:
        raise ValidationError(
            message=(
                "DobroPost config must define at least one of "
                "'webhook_secret' or 'webhook_allowed_ips' — otherwise "
                "every inbound webhook is rejected with 401 and the "
                "endpoint becomes dead-on-arrival."
            ),
            error_code="DOBROPOST_WEBHOOK_AUTH_REQUIRED",
        )


_PROVIDER_VALIDATORS: dict[str, Callable[[dict[str, Any], dict[str, Any]], None]] = {
    PROVIDER_DOBROPOST: _validate_dobropost,
}


def validate_provider_account_input(
    provider_code: str,
    credentials: dict[str, Any],
    config: dict[str, Any] | None,
) -> None:
    """Run the validator registered for ``provider_code`` (no-op if absent).

    Unknown provider codes pass through silently — the bootstrap path
    already logs a warning when no factory is registered for the
    provider, and operators may legitimately pre-create rows for
    integrations that ship later.
    """
    validator = _PROVIDER_VALIDATORS.get(provider_code.strip().lower())
    if validator is None:
        return
    validator(credentials, config or {})
