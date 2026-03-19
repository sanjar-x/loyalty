"""seed IAM roles and permissions

Revision ID: d2bb038b00e3
Revises: f788d1919523
Create Date: 2026-03-16 08:26:00.276459

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d2bb038b00e3"
down_revision: str | Sequence[str] | None = "f788d1919523"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Stable UUIDs for system roles (deterministic for idempotent seeding)
SUPER_ADMIN_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
MANAGER_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
CUSTOMER_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")

PERMISSIONS = [
    ("brands:create", "brands", "create"),
    ("brands:read", "brands", "read"),
    ("brands:update", "brands", "update"),
    ("brands:delete", "brands", "delete"),
    ("categories:create", "categories", "create"),
    ("categories:read", "categories", "read"),
    ("categories:update", "categories", "update"),
    ("categories:delete", "categories", "delete"),
    ("products:create", "products", "create"),
    ("products:read", "products", "read"),
    ("products:update", "products", "update"),
    ("products:delete", "products", "delete"),
    ("orders:create", "orders", "create"),
    ("orders:read", "orders", "read"),
    ("orders:update", "orders", "update"),
    ("users:read", "users", "read"),
    ("users:update", "users", "update"),
    ("users:delete", "users", "delete"),
    ("roles:manage", "roles", "manage"),
    ("identities:manage", "identities", "manage"),
]

# Permission codenames assigned to each role
MANAGER_PERMS = [
    "brands:create",
    "brands:read",
    "brands:update",
    "brands:delete",
    "categories:create",
    "categories:read",
    "categories:update",
    "categories:delete",
    "products:create",
    "products:read",
    "products:update",
    "products:delete",
    "orders:create",
    "orders:read",
    "orders:update",
    "users:read",
]

CUSTOMER_PERMS = [
    "brands:read",
    "categories:read",
    "products:read",
    "orders:create",
    "orders:read",
    "users:read",
    "users:update",
    "users:delete",
]


def upgrade() -> None:
    """Seed system roles, permissions, hierarchy."""
    permissions_table = sa.table(
        "permissions",
        sa.column("id", sa.UUID),
        sa.column("codename", sa.String),
        sa.column("resource", sa.String),
        sa.column("action", sa.String),
    )
    roles_table = sa.table(
        "roles",
        sa.column("id", sa.UUID),
        sa.column("name", sa.String),
        sa.column("description", sa.String),
        sa.column("is_system", sa.Boolean),
    )
    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("role_id", sa.UUID),
        sa.column("permission_id", sa.UUID),
    )
    role_hierarchy_table = sa.table(
        "role_hierarchy",
        sa.column("parent_role_id", sa.UUID),
        sa.column("child_role_id", sa.UUID),
    )

    # 1. Insert permissions (deterministic UUIDs via uuid5)
    perm_ids: dict[str, uuid.UUID] = {}
    for codename, resource, action in PERMISSIONS:
        perm_id = uuid.uuid5(uuid.NAMESPACE_DNS, f"perm.{codename}")
        perm_ids[codename] = perm_id
        op.execute(
            permissions_table.insert().values(
                id=perm_id, codename=codename, resource=resource, action=action
            )
        )

    # 2. Insert system roles
    for role_id, name, description in [
        (SUPER_ADMIN_ID, "super_admin", "Full system access"),
        (MANAGER_ID, "manager", "Catalog and order management"),
        (CUSTOMER_ID, "customer", "Basic customer access"),
    ]:
        op.execute(
            roles_table.insert().values(
                id=role_id, name=name, description=description, is_system=True
            )
        )

    # 3. Assign all permissions to super_admin
    for perm_id in perm_ids.values():
        op.execute(
            role_permissions_table.insert().values(role_id=SUPER_ADMIN_ID, permission_id=perm_id)
        )

    # 4. Assign manager permissions
    for codename in MANAGER_PERMS:
        op.execute(
            role_permissions_table.insert().values(
                role_id=MANAGER_ID, permission_id=perm_ids[codename]
            )
        )

    # 5. Assign customer permissions
    for codename in CUSTOMER_PERMS:
        op.execute(
            role_permissions_table.insert().values(
                role_id=CUSTOMER_ID, permission_id=perm_ids[codename]
            )
        )

    # 6. Role hierarchy: super_admin → manager → customer
    op.execute(
        role_hierarchy_table.insert().values(
            parent_role_id=SUPER_ADMIN_ID, child_role_id=MANAGER_ID
        )
    )
    op.execute(
        role_hierarchy_table.insert().values(parent_role_id=MANAGER_ID, child_role_id=CUSTOMER_ID)
    )


def downgrade() -> None:
    """Remove seed data."""
    op.execute("DELETE FROM role_hierarchy")
    op.execute("DELETE FROM role_permissions")
    op.execute("DELETE FROM roles WHERE is_system = true")
    op.execute("DELETE FROM permissions")
