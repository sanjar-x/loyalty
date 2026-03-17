"""Shared ORM models for cross-cutting infrastructure concerns.

Contains models that do not belong to a single bounded-context module
(e.g., OutboxMessage, FailedTask).
"""

from src.infrastructure.database.models.outbox import OutboxMessage

__all__ = ["OutboxMessage"]
