"""Recipient read-models (post-Sprint-1.5 Part 2 — shipping-only)."""

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RecipientReadModel:
    recipient_id: uuid.UUID
    full_name_ru: str
    full_name_lat: str
    phone: str
    email: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    version: int = 0
    """Optimistic-locking counter — surfaced as ``ETag: "v{N}"`` on
    GET so the front-end can echo it as ``If-Match`` on the next
    PATCH/DELETE (D0.3)."""


@dataclass(frozen=True)
class RecipientListPage:
    items: list[RecipientReadModel]
