# src/shared/interfaces/auth.py
import uuid
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthContext:
    """
    Immutable authentication context extracted from JWT.
    Propagated through FastAPI dependency chain.
    Contains ONLY identity reference + session reference — no PII.
    """

    identity_id: uuid.UUID
    session_id: uuid.UUID
