"""add_pricing_context_global_values_set_at

Revision ID: d4f7e2a91c83
Revises: a91c4f2d8e51
Create Date: 2026-04-25 17:30:00.000000

ADR-005 — sidecar JSONB column tracking the timestamp at which each
``global_values`` key was last set. The pricing recompute service uses
these timestamps to enforce FX‑rate freshness: when a formula references
an ``is_fx_rate`` variable older than its ``max_age_days`` window, the
SKU transitions to ``stale_fx`` instead of being priced with a stale
rate.

Format:

    {"fx_cny_rub": "2026-04-25T15:00:00+00:00", ...}

Stored separately from ``global_values`` so existing readers and the
``set_global_value`` API surface keep their shape; admins observing
``global_values`` directly see the same Decimal map they always have.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "d4f7e2a91c83"
down_revision: str | Sequence[str] | None = "a91c4f2d8e51"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pricing_contexts",
        sa.Column(
            "global_values_set_at",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
            comment=(
                "Per-key UTC ISO timestamps marking when each "
                "``global_values`` entry was last set; consumed by the "
                "FX-rate staleness gate in the SKU recompute pipeline "
                "(ADR-005)."
            ),
        ),
    )


def downgrade() -> None:
    op.drop_column("pricing_contexts", "global_values_set_at")
