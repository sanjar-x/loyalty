"""
Authentication context value object.

Carries the identity and session references extracted from a validated
JWT through the FastAPI dependency chain. Contains no PII — only opaque
UUIDs. Part of the shared kernel (domain-agnostic).

Typical usage:
    from src.shared.interfaces.auth import AuthContext

    ctx = AuthContext(identity_id=..., session_id=...)
"""

import uuid
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthContext:
    """Immutable authentication context extracted from a JWT.

    Propagated through FastAPI dependencies to command/query handlers.
    Contains only identity and session references — no PII.

    Attributes:
        identity_id: UUID of the authenticated identity aggregate.
        session_id: UUID of the current active session.
        is_staff: True iff ``Identity.account_type == STAFF``. Sourced
            from the same DB lookup ``get_auth_context`` already does
            for token-version validation, so admin-role checks
            (``RequireStaffRole``) don't add a second roundtrip.
    """

    identity_id: uuid.UUID
    session_id: uuid.UUID
    is_staff: bool = False
