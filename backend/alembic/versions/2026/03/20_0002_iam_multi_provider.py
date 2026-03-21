"""IAM multi-provider schema changes + telegram_credentials data migration.

Revision ID: 20_0002
Revises: 20_0001
Create Date: 2026-03-20
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "20_0002"
down_revision = "20_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Identity: add token_version
    op.add_column("identities", sa.Column("token_version", sa.Integer(), server_default="1", nullable=False))

    # 2. LinkedAccount: add new columns
    op.add_column("linked_accounts", sa.Column("email_verified", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("linked_accounts", sa.Column("provider_metadata", JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False))
    op.add_column("linked_accounts", sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False))
    op.add_column("linked_accounts", sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False))

    # 3. Session: idle timeout columns
    op.add_column("sessions", sa.Column("last_active_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False))
    op.add_column("sessions", sa.Column("idle_expires_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False))
    # Backfill: set idle_expires_at = expires_at for existing sessions (preserve lifetimes)
    op.execute("UPDATE sessions SET idle_expires_at = expires_at WHERE NOT is_revoked")

    # 4. Customer: username
    op.add_column("customers", sa.Column("username", sa.String(100), nullable=True))

    # 5. Rename identities.type -> primary_auth_method
    op.alter_column("identities", "type", new_column_name="primary_auth_method")

    # 6. Migrate telegram_credentials -> linked_accounts
    op.execute("""
        INSERT INTO linked_accounts (id, identity_id, provider, provider_sub_id, provider_email, email_verified, provider_metadata, created_at, updated_at)
        SELECT gen_random_uuid(), identity_id, 'telegram', telegram_id::text,
               NULL, false,
               jsonb_build_object(
                 'first_name', first_name,
                 'last_name', last_name,
                 'username', username,
                 'language_code', language_code,
                 'is_premium', is_premium,
                 'photo_url', photo_url,
                 'allows_write_to_pm', allows_write_to_pm
               ),
               created_at, updated_at
        FROM telegram_credentials
        ON CONFLICT (provider, provider_sub_id) DO NOTHING
    """)

    # 7. Backfill customer usernames from migrated linked_accounts
    op.execute("""
        UPDATE customers c
        SET username = (la.provider_metadata->>'username')
        FROM linked_accounts la
        WHERE la.identity_id = c.id
          AND la.provider = 'telegram'
          AND la.provider_metadata->>'username' IS NOT NULL
    """)


def downgrade() -> None:
    op.alter_column("identities", "primary_auth_method", new_column_name="type")
    op.drop_column("customers", "username")
    op.drop_column("sessions", "idle_expires_at")
    op.drop_column("sessions", "last_active_at")
    op.drop_column("linked_accounts", "updated_at")
    op.drop_column("linked_accounts", "created_at")
    op.drop_column("linked_accounts", "provider_metadata")
    op.drop_column("linked_accounts", "email_verified")
    op.drop_column("identities", "token_version")
