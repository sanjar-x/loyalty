"""add_activity_user_activity_events

Revision ID: 7b21e0a9c401
Revises: 36a91fa612cd
Create Date: 2026-04-21 10:00:00.000000

"""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7b21e0a9c401"
down_revision: str | Sequence[str] | None = "36a91fa612cd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _month_range(anchor: datetime) -> tuple[str, str, str]:
    """Return (start_iso, end_iso, suffix) for the month containing anchor."""
    start = anchor.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start.isoformat(), end.isoformat(), start.strftime("%Y%m")


def upgrade() -> None:
    """Create the partitioned user_activity_events table and initial partitions."""
    # Partitioned parent table.  Composite PK (id, created_at) is required
    # because the partition key must participate in the primary key.
    op.execute(
        """
        CREATE TABLE user_activity_events (
            id UUID NOT NULL,
            event_type VARCHAR(64) NOT NULL,
            actor_id UUID,
            session_id VARCHAR(128),
            product_id UUID,
            category_id UUID,
            search_query TEXT,
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (id, created_at)
        ) PARTITION BY RANGE (created_at)
        """
    )

    # Indexes — defined on parent table, automatically propagated to all
    # partitions (Postgres 11+).
    op.execute(
        "CREATE INDEX ix_user_activity_events_created_brin "
        "ON user_activity_events USING BRIN (created_at)"
    )
    op.execute(
        "CREATE INDEX ix_user_activity_events_actor_created "
        "ON user_activity_events (actor_id, created_at DESC) "
        "WHERE actor_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX ix_user_activity_events_product_type "
        "ON user_activity_events (product_id, event_type) "
        "WHERE product_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX ix_user_activity_events_payload_gin "
        "ON user_activity_events USING GIN (payload jsonb_path_ops)"
    )

    # Initial monthly partitions — current + next 3 months, so we have
    # several months of runway before the TaskIQ partition-provisioning
    # job kicks in.
    now = datetime.now(UTC)
    anchors = [now + timedelta(days=31 * i) for i in range(4)]
    seen: set[str] = set()
    for anchor in anchors:
        start, end, suffix = _month_range(anchor)
        if suffix in seen:
            continue
        seen.add(suffix)
        op.execute(
            f'CREATE TABLE IF NOT EXISTS "user_activity_events_{suffix}" '
            f"PARTITION OF user_activity_events "
            f"FOR VALUES FROM ('{start}') TO ('{end}')"
        )


def downgrade() -> None:
    """Drop the partitioned table and all its partitions."""
    op.execute("DROP TABLE IF EXISTS user_activity_events CASCADE")
