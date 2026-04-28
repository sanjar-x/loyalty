"""Admin REST schemas for ``/admin/logistics/provider-accounts``.

Separated from ``schemas.py`` (the public Checkout-facing contract)
because the admin surface is internal — it can move faster, and we
don't want the public TypeScript client to leak admin shapes.

Credentials in responses are never raw: the read model carries
``CredentialFingerprint`` (first 8 hex of SHA-256 + length), which the
admin UI displays so operators can verify "this is the key I expect"
without ever holding the secret on the client.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CredentialFingerprintSchema(BaseModel):
    """Per-key fingerprint exposed instead of the raw credential value."""

    fingerprint: str = Field(
        description="First 8 hex chars of SHA-256(value). Stable per value."
    )
    length: int = Field(ge=0, description="Length of the original string value.")


class ProviderAccountResponse(BaseModel):
    """Read model returned by every admin provider-account endpoint."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider_code: str
    name: str
    is_active: bool
    credential_fingerprints: dict[str, CredentialFingerprintSchema]
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ProviderAccountListResponse(BaseModel):
    items: list[ProviderAccountResponse]


class CreateProviderAccountRequest(BaseModel):
    """Body for ``POST /admin/logistics/provider-accounts``.

    ``credentials`` is opaque (provider-specific) — for CDEK it must
    contain ``client_id`` + ``client_secret``; for Yandex,
    ``oauth_token``. Validation is delegated to the matching factory.
    """

    provider_code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    credentials: dict[str, Any] = Field(..., min_length=1)
    config: dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class UpdateProviderAccountRequest(BaseModel):
    """Body for ``PUT /admin/logistics/provider-accounts/{id}``.

    Every field is optional; missing fields are left unchanged. Pass
    ``replace_config=true`` to swap the entire config dict instead of
    the default shallow-merge behaviour — useful when removing keys.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    credentials: dict[str, Any] | None = Field(default=None, min_length=1)
    config: dict[str, Any] | None = None
    replace_config: bool = False


class SetProviderAccountActiveRequest(BaseModel):
    is_active: bool


class RefreshRegistryResponse(BaseModel):
    """Returned by ``POST /admin/logistics/provider-accounts/refresh``.

    Lists which provider codes ended up in the registry on this worker
    after the rebuild. Multi-worker deploys must hit refresh on every
    instance — the registry is a per-worker singleton.
    """

    registered_provider_codes: list[str]
    note: str = (
        "Registry refreshed on the worker that served this request. "
        "Other workers retain the previous registry until they receive "
        "their own refresh call or the deployment is rolled."
    )
