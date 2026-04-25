"""add_shipment_edit_intake_return_state

Revision ID: c3f9b1d4e7a2
Revises: a91c4f2d8e51
Create Date: 2026-04-25 20:00:00.000000

H5 — UoW + Shipment mutators for edit / intake / return.

Adds three JSONB columns to ``shipments`` so the aggregate can
persist its newly-introduced state:

* ``pending_edit_tasks_json`` — list of outstanding async edit tasks
  (Yandex 3.06 / 3.12 / 3.14 / 3.15) awaiting status-poller resolution.
* ``scheduled_intake_json`` — currently-active courier intake (CDEK).
* ``registered_returns_json`` — append-only audit of returns / refusals.

Existing shipments are backfilled with empty containers so the new
columns are NOT NULL except for the optional ``scheduled_intake_json``.
Reversible — ``downgrade()`` drops the columns.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3f9b1d4e7a2"
down_revision: str | None = "a91c4f2d8e51"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "shipments",
        sa.Column(
            "pending_edit_tasks_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
            comment=(
                "In-flight edit tasks: [{task_id, kind, submitted_at, initial_status}]"
            ),
        ),
    )
    op.add_column(
        "shipments",
        sa.Column(
            "scheduled_intake_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Active intake: {provider_intake_id, status, scheduled_at}",
        ),
    )
    op.add_column(
        "shipments",
        sa.Column(
            "registered_returns_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
            comment=("Returns: [{kind, provider_return_id, reason, registered_at}]"),
        ),
    )


def downgrade() -> None:
    op.drop_column("shipments", "registered_returns_json")
    op.drop_column("shipments", "scheduled_intake_json")
    op.drop_column("shipments", "pending_edit_tasks_json")
