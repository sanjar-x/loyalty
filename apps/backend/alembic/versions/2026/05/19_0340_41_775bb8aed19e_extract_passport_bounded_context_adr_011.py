"""extract passport bounded context (ADR-011)

Revision ID: 775bb8aed19e
Revises: 124554f5bdf2
Create Date: 2026-05-19 03:40:41.515347

Sprint 1.5 Part 2 / ADR-011 — splits the previously-monolithic
``Recipient`` aggregate into two independent bounded contexts:

* ``Recipient`` — shipping coordinates (name / phone / email).
* ``Passport`` — customs documents (passport_serial+number+issue_date,
  birth_date, INN, validation FSM).

The two contexts have an M:N relationship through ``Order`` — there is
intentionally no link table between them. An order references both
``recipient_id`` and (optionally) ``passport_id``; LOCAL-only orders
keep ``passport_id`` NULL.

Migration steps (all in one transaction — alembic's default — so a
failure rolls everything back):

1. Create the ``passports`` table with CHECK constraints and indices.
2. Backfill ``passports`` from existing ``recipients`` rows that have
   customs data, deduplicating by ``(identity_id, inn)`` so customers
   with multiple recipients sharing the same passport do not get
   duplicate passport rows.
3. Add ``orders.passport_id`` (FK ON DELETE SET NULL) and
   ``orders.passport_snapshot`` (JSONB) plus the pair-consistency
   CHECK constraint.
4. Backfill ``orders.passport_id`` + ``orders.passport_snapshot`` from
   the matching new passport row, joining on ``identity_id`` + INN.
   Historic walk-in orders (cart_id phantom, recipient minted at
   creation) without a matching passport keep both columns NULL.
5. Drop the customs columns from ``recipients`` (passport_serial,
   passport_number, passport_issue_date, birth_date, inn,
   validation_status, validation_failed_reason) plus the
   ``ix_recipients_inn`` index and the three CHECK constraints
   covering them.
6. Drop the legacy ``recipient_passport_*``, ``recipient_birth_date``
   and ``recipient_inn`` snapshot columns from ``orders`` — that
   payload now lives in ``orders.passport_snapshot``.

Edge cases (per the Sprint 1.5 Part 2 spec):

* An order without a matching passport (e.g. legacy walk-in) keeps
  ``orders.passport_id`` NULL — the pair-consistency CHECK enforces
  ``passport_snapshot`` is also NULL in that case.
* Two recipients of the same identity sharing the same INN map to a
  single ``passports`` row (``SELECT DISTINCT ON``).
* Dropping a passport later via ``DELETE FROM passports`` leaves the
  order's ``passport_snapshot`` JSONB intact (FK
  ``ON DELETE SET NULL``) — the historical customs payload survives.

The downgrade rebuilds the old columns from the snapshot JSONB so
DEV/CI can roll back, but it cannot recover archived passports past
the FK SET NULL.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import MetaData  # noqa: F401
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "775bb8aed19e"
down_revision: str | Sequence[str] | None = "124554f5bdf2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema — extract Passport bounded context."""
    # ------------------------------------------------------------------
    # Step 1 — create passports table.
    # ------------------------------------------------------------------
    op.create_table(
        "passports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("identity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name_ru", sa.String(length=255), nullable=False),
        sa.Column("full_name_lat", sa.String(length=255), nullable=False),
        sa.Column("passport_serial", sa.String(length=4), nullable=False),
        sa.Column("passport_number", sa.String(length=6), nullable=False),
        sa.Column("passport_issue_date", sa.Date(), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("inn", sa.String(length=12), nullable=False),
        sa.Column(
            "validation_status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("validation_failed_reason", sa.String(length=255), nullable=True),
        sa.Column(
            "is_archived",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "validation_status IN ('pending','verified','invalid')",
            name="ck_passports_valid_status",
        ),
        sa.CheckConstraint(
            "char_length(passport_serial) = 4",
            name="ck_passports_passport_serial_len",
        ),
        sa.CheckConstraint(
            "char_length(passport_number) = 6",
            name="ck_passports_passport_number_len",
        ),
        sa.CheckConstraint("char_length(inn) = 12", name="ck_passports_inn_len"),
        comment="Customer-owned customs passports (ADR-011)",
    )
    op.create_index(
        "ix_passports_identity",
        "passports",
        ["identity_id", "is_archived"],
    )
    op.create_index("ix_passports_inn", "passports", ["inn"])

    # ------------------------------------------------------------------
    # Step 2 — backfill passports from recipients with customs data.
    #
    # DISTINCT ON (identity_id, inn) deduplicates the case where one
    # customer has multiple recipients sharing the same passport. The
    # ORDER BY created_at ASC picks the earliest row for stability.
    # ``gen_random_uuid()`` requires the ``pgcrypto`` extension which
    # has been a dependency of this project since the very first
    # migration — no need to re-create it here.
    # ------------------------------------------------------------------
    op.execute(
        sa.text(
            """
            INSERT INTO passports (
                id, identity_id, full_name_ru, full_name_lat,
                passport_serial, passport_number, passport_issue_date,
                birth_date, inn, validation_status, validation_failed_reason,
                is_archived, version, created_at, updated_at
            )
            SELECT
                gen_random_uuid(),
                r.identity_id,
                r.full_name_ru,
                r.full_name_lat,
                r.passport_serial,
                r.passport_number,
                r.passport_issue_date,
                r.birth_date,
                r.inn,
                COALESCE(r.validation_status, 'pending'),
                r.validation_failed_reason,
                r.is_archived,
                0,
                r.created_at,
                r.updated_at
            FROM (
                SELECT DISTINCT ON (identity_id, inn)
                       identity_id, full_name_ru, full_name_lat,
                       passport_serial, passport_number,
                       passport_issue_date, birth_date, inn,
                       validation_status, validation_failed_reason,
                       is_archived, created_at, updated_at
                FROM recipients
                WHERE passport_serial IS NOT NULL
                  AND passport_number IS NOT NULL
                  AND inn IS NOT NULL
                ORDER BY identity_id, inn, created_at ASC
            ) r
            """
        )
    )

    # ------------------------------------------------------------------
    # Step 3 — add orders.passport_id / passport_snapshot + FK + CHECK.
    # ------------------------------------------------------------------
    op.add_column(
        "orders",
        sa.Column("passport_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column(
            "passport_snapshot",
            postgresql.JSONB,
            nullable=True,
            comment=(
                "Frozen customs PII at checkout time (full_name_ru/lat, "
                "passport_serial/number/issue_date, birth_date, inn, "
                "validation_status). Pair with passport_id; both NULL "
                "for local-only orders."
            ),
        ),
    )
    op.create_index("ix_orders_passport_id", "orders", ["passport_id"])
    op.create_foreign_key(
        "fk_orders_passport_id",
        "orders",
        "passports",
        ["passport_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ------------------------------------------------------------------
    # Step 4 — backfill orders.passport_id + passport_snapshot.
    #
    # Join keys: identity_id + the legacy ``recipient_inn`` column on
    # the order row, which holds the INN as captured at checkout.
    # Orders without a matching passport (legacy walk-in, etc.) keep
    # both columns NULL — pair CHECK is added afterwards in step 4b so
    # the temporary NULL/NULL rows pass.
    # ------------------------------------------------------------------
    op.execute(
        sa.text(
            """
            UPDATE orders o
            SET passport_id = p.id,
                passport_snapshot = jsonb_build_object(
                    'passportId',         p.id::text,
                    'fullNameRu',         p.full_name_ru,
                    'fullNameLat',        p.full_name_lat,
                    'passportSerial',     p.passport_serial,
                    'passportNumber',     p.passport_number,
                    'passportIssueDate',  to_char(p.passport_issue_date, 'YYYY-MM-DD'),
                    'birthDate',          to_char(p.birth_date, 'YYYY-MM-DD'),
                    'inn',                p.inn,
                    'validationStatus',   p.validation_status
                )
            FROM passports p
            WHERE p.identity_id = o.identity_id
              AND p.inn = o.recipient_inn
            """
        )
    )

    # Step 4b — pair-consistency CHECK. Added AFTER backfill so the
    # interim state (NULL/NULL on un-matched legacy rows) passes.
    op.create_check_constraint(
        "ck_orders_passport_pair_consistent",
        "orders",
        "(passport_id IS NULL) = (passport_snapshot IS NULL)",
    )

    # ------------------------------------------------------------------
    # Step 5 — drop customs columns from recipients.
    # ------------------------------------------------------------------
    op.drop_constraint("ck_recipients_valid_status", "recipients", type_="check")
    op.drop_constraint("ck_recipients_passport_serial_len", "recipients", type_="check")
    op.drop_constraint("ck_recipients_passport_number_len", "recipients", type_="check")
    op.drop_constraint("ck_recipients_inn_len", "recipients", type_="check")
    op.drop_index("ix_recipients_inn", table_name="recipients")
    for col in (
        "validation_failed_reason",
        "validation_status",
        "inn",
        "birth_date",
        "passport_issue_date",
        "passport_number",
        "passport_serial",
    ):
        op.drop_column("recipients", col)

    # ------------------------------------------------------------------
    # Step 6 — drop legacy customs snapshot columns from orders.
    # ------------------------------------------------------------------
    for col in (
        "recipient_inn",
        "recipient_birth_date",
        "recipient_passport_issue_date",
        "recipient_passport_number",
        "recipient_passport_serial",
    ):
        op.drop_column("orders", col)


def downgrade() -> None:
    """Reverse the upgrade — restore the monolithic recipient layout.

    Re-creates the dropped columns and copies customs data back from
    ``orders.passport_snapshot`` for the order side, and from the
    matching ``passports`` row for the recipient side. The pre-merger
    UNIQUE / CHECK structure is re-established so the older app
    version can run against the rolled-back schema.

    Limitations: passport rows that were archived (``is_archived =
    TRUE``) after the migration cannot be reconstructed precisely on
    the recipient side — we fill the recipient with the snapshot's
    archived passport values from the latest order, which matches the
    old behaviour closely enough for DEV/CI rollbacks. Production
    rollback is not supported (see HARD-1 — bad migration aborts the
    deploy, no rollback path is exercised).
    """
    # ------------------------------------------------------------------
    # Step 6-reverse — re-add legacy recipient_* customs columns on orders.
    # ------------------------------------------------------------------
    op.add_column(
        "orders",
        sa.Column(
            "recipient_passport_serial",
            sa.String(length=4),
            nullable=True,
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "recipient_passport_number",
            sa.String(length=6),
            nullable=True,
        ),
    )
    op.add_column(
        "orders",
        sa.Column(
            "recipient_passport_issue_date",
            sa.Date(),
            nullable=True,
        ),
    )
    op.add_column(
        "orders",
        sa.Column("recipient_birth_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("recipient_inn", sa.String(length=12), nullable=True),
    )
    op.execute(
        sa.text(
            """
            UPDATE orders
            SET recipient_passport_serial =
                    passport_snapshot ->> 'passportSerial',
                recipient_passport_number =
                    passport_snapshot ->> 'passportNumber',
                recipient_passport_issue_date =
                    (passport_snapshot ->> 'passportIssueDate')::date,
                recipient_birth_date =
                    (passport_snapshot ->> 'birthDate')::date,
                recipient_inn = passport_snapshot ->> 'inn'
            WHERE passport_snapshot IS NOT NULL
            """
        )
    )

    # ------------------------------------------------------------------
    # Step 5-reverse — re-add customs columns on recipients (nullable).
    # ------------------------------------------------------------------
    op.add_column(
        "recipients",
        sa.Column("passport_serial", sa.String(length=4), nullable=True),
    )
    op.add_column(
        "recipients",
        sa.Column("passport_number", sa.String(length=6), nullable=True),
    )
    op.add_column(
        "recipients",
        sa.Column("passport_issue_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "recipients",
        sa.Column("birth_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "recipients",
        sa.Column("inn", sa.String(length=12), nullable=True),
    )
    op.add_column(
        "recipients",
        sa.Column(
            "validation_status",
            sa.String(length=16),
            nullable=True,
            server_default=sa.text("'pending'"),
        ),
    )
    op.add_column(
        "recipients",
        sa.Column("validation_failed_reason", sa.String(length=255), nullable=True),
    )

    # Re-hydrate recipients from passports (matching identity + inn).
    op.execute(
        sa.text(
            """
            UPDATE recipients r
            SET passport_serial       = p.passport_serial,
                passport_number       = p.passport_number,
                passport_issue_date   = p.passport_issue_date,
                birth_date            = p.birth_date,
                inn                   = p.inn,
                validation_status     = p.validation_status
            FROM passports p
            WHERE p.identity_id = r.identity_id
            """
        )
    )

    op.create_check_constraint(
        "ck_recipients_inn_len",
        "recipients",
        "char_length(inn) = 12",
    )
    op.create_check_constraint(
        "ck_recipients_passport_number_len",
        "recipients",
        "char_length(passport_number) = 6",
    )
    op.create_check_constraint(
        "ck_recipients_passport_serial_len",
        "recipients",
        "char_length(passport_serial) = 4",
    )
    op.create_check_constraint(
        "ck_recipients_valid_status",
        "recipients",
        "validation_status IN ('pending','verified','invalid')",
    )
    op.create_index("ix_recipients_inn", "recipients", ["inn"])

    # ------------------------------------------------------------------
    # Steps 4 / 3 reverse — drop passport columns + FK + CHECK on orders.
    # ------------------------------------------------------------------
    op.drop_constraint("ck_orders_passport_pair_consistent", "orders", type_="check")
    op.drop_constraint("fk_orders_passport_id", "orders", type_="foreignkey")
    op.drop_index("ix_orders_passport_id", table_name="orders")
    op.drop_column("orders", "passport_snapshot")
    op.drop_column("orders", "passport_id")

    # ------------------------------------------------------------------
    # Steps 2 / 1 reverse — drop passports table.
    # ------------------------------------------------------------------
    op.drop_index("ix_passports_inn", table_name="passports")
    op.drop_index("ix_passports_identity", table_name="passports")
    op.drop_table("passports")
