"""backfill customers for telegram identities

Creates Customer rows for identities that registered via Telegram
but never got a Customer profile due to the missing outbox handler
for linked_account_created events.

Revision ID: c81c05190cd9
Revises: 8a1e719de582
Create Date: 2026-04-13 19:10:04.195271

"""

from collections.abc import Sequence

from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c81c05190cd9"
down_revision: str | Sequence[str] | None = "8a1e719de582"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_REFERRAL_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def upgrade() -> None:
    """Create missing Customer records for Telegram-registered identities."""
    conn = op.get_bind()

    orphans = conn.execute(
        text("""
            SELECT
                la.identity_id,
                la.provider_metadata->>'first_name' AS first_name,
                la.provider_metadata->>'last_name'  AS last_name,
                la.provider_metadata->>'username'    AS username
            FROM linked_accounts la
            LEFT JOIN customers c ON c.id = la.identity_id
            WHERE c.id IS NULL
              AND la.provider = 'telegram'
        """)
    ).fetchall()

    for row in orphans:
        referral = _generate_referral_code(conn)
        conn.execute(
            text("""
                INSERT INTO customers
                    (id, first_name, last_name, username, referral_code,
                     created_at, updated_at)
                VALUES
                    (:id, :first_name, :last_name, :username, :referral_code,
                     NOW(), NOW())
            """),
            {
                "id": row.identity_id,
                "first_name": row.first_name or "",
                "last_name": row.last_name or "",
                "username": row.username,
                "referral_code": referral,
            },
        )


def _generate_referral_code(conn, length: int = 8) -> str:
    """Generate a unique referral code (same alphabet as domain service)."""
    import secrets

    for _ in range(10):
        code = "".join(secrets.choice(_REFERRAL_ALPHABET) for _ in range(length))
        exists = conn.execute(
            text("SELECT 1 FROM customers WHERE referral_code = :code"),
            {"code": code},
        ).fetchone()
        if not exists:
            return code
    raise RuntimeError("Failed to generate unique referral code after 10 attempts")


def downgrade() -> None:
    """No-op: cannot reliably distinguish backfilled rows."""
    pass
