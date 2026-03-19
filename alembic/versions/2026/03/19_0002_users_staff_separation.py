"""Users/Staff separation: account_type, customers, staff_members, staff_invitations.

Revision ID: 19_0002
Revises: 19_0001
Create Date: 2026-03-19
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID

from alembic import op

revision = "19_0002"
down_revision = "19_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add account_type to identities
    op.add_column(
        "identities",
        sa.Column(
            "account_type",
            sa.String(10),
            nullable=False,
            server_default="CUSTOMER",
        ),
    )
    op.create_index("ix_identities_account_type", "identities", ["account_type"])

    # 2. Create customers table (new, separate from users)
    op.create_table(
        "customers",
        sa.Column("id", UUID(as_uuid=True), sa.ForeignKey("identities.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("profile_email", sa.String(320), nullable=True),
        sa.Column("first_name", sa.String(100), nullable=False, server_default=""),
        sa.Column("last_name", sa.String(100), nullable=False, server_default=""),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("referral_code", sa.String(12), nullable=True, unique=True),
        sa.Column("referred_by", UUID(as_uuid=True), sa.ForeignKey("customers.id"), nullable=True),
        sa.Column("created_at", TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        comment="Customer profiles with referral data (GDPR-isolated)",
    )
    op.create_index("ix_customers_referral_code", "customers", ["referral_code"])
    op.create_index("ix_customers_referred_by", "customers", ["referred_by"])

    # 3. Create staff_members table
    op.create_table(
        "staff_members",
        sa.Column("id", UUID(as_uuid=True), sa.ForeignKey("identities.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("first_name", sa.String(100), nullable=False, server_default=""),
        sa.Column("last_name", sa.String(100), nullable=False, server_default=""),
        sa.Column("profile_email", sa.String(320), nullable=True),
        sa.Column("position", sa.String(100), nullable=True),
        sa.Column("department", sa.String(100), nullable=True),
        sa.Column("invited_by", UUID(as_uuid=True), sa.ForeignKey("identities.id"),
                  nullable=False),
        sa.Column("created_at", TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        comment="Staff member profiles",
    )

    # 4. Create staff_invitations table
    op.create_table(
        "staff_invitations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("invited_by", UUID(as_uuid=True), sa.ForeignKey("identities.id"),
                  nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default="PENDING"),
        sa.Column("created_at", TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("expires_at", TIMESTAMP(timezone=True), nullable=False),
        sa.Column("accepted_at", TIMESTAMP(timezone=True), nullable=True),
        sa.Column("accepted_identity_id", UUID(as_uuid=True),
                  sa.ForeignKey("identities.id"), nullable=True),
        sa.CheckConstraint(
            "status IN ('PENDING', 'ACCEPTED', 'EXPIRED', 'REVOKED')",
            name="chk_invitation_status",
        ),
        comment="Staff member invitations with token-based acceptance",
    )
    op.create_index("ix_staff_invitations_email", "staff_invitations", ["email"])
    op.create_index("ix_staff_invitations_status", "staff_invitations", ["status"])

    # 5. Create staff_invitation_roles table
    op.create_table(
        "staff_invitation_roles",
        sa.Column("invitation_id", UUID(as_uuid=True),
                  sa.ForeignKey("staff_invitations.id", ondelete="CASCADE"),
                  primary_key=True),
        sa.Column("role_id", UUID(as_uuid=True),
                  sa.ForeignKey("roles.id"),
                  primary_key=True),
    )

    # 6. Add new permissions
    op.execute("""
        INSERT INTO permissions (id, codename, resource, action, description) VALUES
            ('b1000000-0000-0000-0000-000000000001', 'staff:manage',     'staff',     'manage',  'Управление сотрудниками'),
            ('b1000000-0000-0000-0000-000000000002', 'staff:invite',     'staff',     'invite',  'Приглашение сотрудников'),
            ('b1000000-0000-0000-0000-000000000003', 'customers:read',   'customers', 'read',    'Просмотр клиентов'),
            ('b1000000-0000-0000-0000-000000000004', 'customers:manage', 'customers', 'manage',  'Управление клиентами')
        ON CONFLICT (codename) DO NOTHING
    """)

    # Admin gets all new permissions
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT '00000000-0000-0000-0000-000000000001', id
        FROM permissions WHERE codename IN ('staff:manage', 'staff:invite', 'customers:read', 'customers:manage')
        ON CONFLICT DO NOTHING
    """)

    # Staff roles get customers:read
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r, permissions p
        WHERE r.name IN ('content_manager', 'order_manager', 'support_specialist', 'review_moderator')
          AND p.codename = 'customers:read'
        ON CONFLICT DO NOTHING
    """)

    # 7. Backfill account_type for existing staff identities
    op.execute("""
        UPDATE identities SET account_type = 'STAFF'
        WHERE id IN (
            SELECT DISTINCT ir.identity_id
            FROM identity_roles ir
            JOIN roles r ON r.id = ir.role_id
            WHERE r.name IN ('admin', 'content_manager', 'order_manager',
                             'support_specialist', 'review_moderator')
        )
    """)


def downgrade() -> None:
    op.drop_table("staff_invitation_roles")
    op.drop_table("staff_invitations")
    op.drop_table("staff_members")
    op.drop_index("ix_customers_referred_by", table_name="customers")
    op.drop_index("ix_customers_referral_code", table_name="customers")
    op.drop_table("customers")
    op.drop_index("ix_identities_account_type", table_name="identities")
    op.drop_column("identities", "account_type")

    # Remove new permissions
    op.execute("""
        DELETE FROM role_permissions WHERE permission_id IN (
            SELECT id FROM permissions WHERE codename IN (
                'staff:manage', 'staff:invite', 'customers:read', 'customers:manage'
            )
        )
    """)
    op.execute("""
        DELETE FROM permissions WHERE codename IN (
            'staff:manage', 'staff:invite', 'customers:read', 'customers:manage'
        )
    """)
