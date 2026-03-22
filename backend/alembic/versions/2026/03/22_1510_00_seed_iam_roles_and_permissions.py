"""Seed IAM roles and permissions.

Revision ID: a0seed00rbac
Revises: dbba35b3bf99
Create Date: 2026-03-22 15:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a0seed00rbac"
down_revision: str = "dbba35b3bf99"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# ---------------------------------------------------------------------------
# Permission UUIDs — uuid5(NAMESPACE_DNS, "perm.<codename>")
# ---------------------------------------------------------------------------
PERMISSIONS: list[tuple[str, str, str, str, str]] = [
    # (id, codename, resource, action, description)
    # ── Catalog ──────────────────────────────────────────────────────────
    ("0123cb88-a31d-5e5a-88fc-2b18c896f01d", "catalog:read", "catalog", "read", "Просмотр каталога (бренды, категории, товары)"),
    ("125a6f40-d2ff-5511-a5cb-deb9d2dc6907", "catalog:manage", "catalog", "manage", "Управление каталогом (CRUD брендов, категорий, товаров, атрибутов, SKU)"),
    # ── Orders ───────────────────────────────────────────────────────────
    ("ad342625-eac5-591f-bddb-f86ab35d8c63", "orders:read", "orders", "read", "Просмотр заказов"),
    ("e72eae9b-68c9-51d3-b41f-62924ed1df0e", "orders:manage", "orders", "manage", "Управление заказами (создание, смена статуса, отмена)"),
    # ── Reviews ──────────────────────────────────────────────────────────
    ("7eefa86f-4c88-57ec-aa01-197b4173decf", "reviews:read", "reviews", "read", "Просмотр отзывов"),
    ("e52c8926-4eaa-56c6-839d-9b8de565d955", "reviews:moderate", "reviews", "moderate", "Модерация отзывов (одобрение, отклонение, удаление)"),
    # ── Returns ──────────────────────────────────────────────────────────
    ("260ef83b-06b3-5e31-b60f-07dbd0666711", "returns:read", "returns", "read", "Просмотр возвратов"),
    ("7501bd14-845d-51de-a70c-335eb179ecdb", "returns:manage", "returns", "manage", "Обработка возвратов"),
    # ── Users (self-service) ─────────────────────────────────────────────
    ("12833502-d3f2-5eba-83ae-95a40cd06153", "users:read", "users", "read", "Просмотр профиля"),
    ("4acf2608-e539-5057-9373-8c935b18aeaf", "users:update", "users", "update", "Редактирование профиля"),
    ("8eadaeaf-ba4a-5747-b1f2-b360df386bca", "users:delete", "users", "delete", "Удаление аккаунта (GDPR)"),
    # ── Admin IAM ────────────────────────────────────────────────────────
    ("4236b6ca-8b53-5b65-9a66-b492351a07c1", "roles:manage", "roles", "manage", "Управление ролями и правами"),
    ("ab498b82-5aa9-5732-b724-4b1caf68b539", "identities:manage", "identities", "manage", "Управление идентификациями (список, деактивация, назначение ролей)"),
    # ── Staff ────────────────────────────────────────────────────────────
    ("b1000000-0000-0000-0000-000000000001", "staff:manage", "staff", "manage", "Управление сотрудниками (список, детали, деактивация)"),
    ("b1000000-0000-0000-0000-000000000002", "staff:invite", "staff", "invite", "Приглашение новых сотрудников"),
    # ── Customers ────────────────────────────────────────────────────────
    ("b1000000-0000-0000-0000-000000000003", "customers:read", "customers", "read", "Просмотр списка клиентов"),
    ("b1000000-0000-0000-0000-000000000004", "customers:manage", "customers", "manage", "Управление клиентами (деактивация, реактивация)"),
]

# ---------------------------------------------------------------------------
# Role UUIDs — deterministic, well-known
# ---------------------------------------------------------------------------
ROLE_ADMIN = "00000000-0000-0000-0000-000000000001"
ROLE_MANAGER = "00000000-0000-0000-0000-000000000002"
ROLE_CUSTOMER = "00000000-0000-0000-0000-000000000003"

ROLES: list[tuple[str, str, str, bool, str | None]] = [
    # (id, name, description, is_system, target_account_type)
    (ROLE_ADMIN, "admin", "Администратор — полный доступ ко всем модулям системы", True, "STAFF"),
    (ROLE_MANAGER, "manager", "Менеджер — каталог, заказы, клиенты, отзывы, возвраты", True, "STAFF"),
    (ROLE_CUSTOMER, "customer", "Клиент — каталог, заказы, профиль, отзывы", True, "CUSTOMER"),
]

# ---------------------------------------------------------------------------
# Role → Permission mapping
# ---------------------------------------------------------------------------
ROLE_PERMISSIONS: dict[str, list[str]] = {
    # admin: ВСЕ permissions
    ROLE_ADMIN: [p[1] for p in PERMISSIONS],
    # manager: операционное управление (без IAM)
    ROLE_MANAGER: [
        # catalog
        "catalog:read",
        "catalog:manage",
        # orders
        "orders:read",
        "orders:manage",
        # reviews
        "reviews:read",
        "reviews:moderate",
        # returns
        "returns:read",
        "returns:manage",
        # users (read-only для просмотра профилей)
        "users:read",
        # customers
        "customers:read",
        "customers:manage",
        # staff (просмотр + приглашение, но не управление ролями)
        "staff:manage",
        "staff:invite",
    ],
    # customer: только свой профиль + чтение каталога/заказов
    ROLE_CUSTOMER: [
        "catalog:read",
        "orders:read",
        "reviews:read",
        "users:read",
        "users:update",
        "users:delete",
    ],
}

# ---------------------------------------------------------------------------
# Role hierarchy (parent inherits all child permissions via recursive CTE)
#
#   admin
#     └── manager
#           └── customer
#
# Effective permissions:
#   admin    = own(17) + manager + customer = ALL 17
#   manager  = own(14) + customer(6)        = 14 unique
#   customer = own(6)                       = 6
# ---------------------------------------------------------------------------
ROLE_HIERARCHY: list[tuple[str, str]] = [
    # (parent_role_id, child_role_id)
    (ROLE_ADMIN, ROLE_MANAGER),
    (ROLE_MANAGER, ROLE_CUSTOMER),
]


def _perm_id(codename: str) -> str:
    """Look up permission UUID by codename."""
    for p in PERMISSIONS:
        if p[1] == codename:
            return p[0]
    msg = f"Unknown permission: {codename}"
    raise ValueError(msg)


def upgrade() -> None:
    # ── Permissions ──────────────────────────────────────────────────────
    op.bulk_insert(
        sa.table(
            "permissions",
            sa.column("id", sa.Uuid),
            sa.column("codename", sa.String),
            sa.column("resource", sa.String),
            sa.column("action", sa.String),
            sa.column("description", sa.String),
        ),
        [
            {
                "id": p[0],
                "codename": p[1],
                "resource": p[2],
                "action": p[3],
                "description": p[4],
            }
            for p in PERMISSIONS
        ],
    )

    # ── Roles ────────────────────────────────────────────────────────────
    op.bulk_insert(
        sa.table(
            "roles",
            sa.column("id", sa.Uuid),
            sa.column("name", sa.String),
            sa.column("description", sa.String),
            sa.column("is_system", sa.Boolean),
            sa.column("target_account_type", sa.String),
        ),
        [
            {
                "id": r[0],
                "name": r[1],
                "description": r[2],
                "is_system": r[3],
                "target_account_type": r[4],
            }
            for r in ROLES
        ],
    )

    # ── Role-Permission assignments ──────────────────────────────────────
    role_perm_rows = []
    for role_id, codenames in ROLE_PERMISSIONS.items():
        for codename in codenames:
            role_perm_rows.append({"role_id": role_id, "permission_id": _perm_id(codename)})

    op.bulk_insert(
        sa.table(
            "role_permissions",
            sa.column("role_id", sa.Uuid),
            sa.column("permission_id", sa.Uuid),
        ),
        role_perm_rows,
    )

    # ── Role hierarchy ───────────────────────────────────────────────────
    op.bulk_insert(
        sa.table(
            "role_hierarchy",
            sa.column("parent_role_id", sa.Uuid),
            sa.column("child_role_id", sa.Uuid),
        ),
        [{"parent_role_id": h[0], "child_role_id": h[1]} for h in ROLE_HIERARCHY],
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM role_hierarchy"))
    conn.execute(sa.text("DELETE FROM role_permissions"))
    conn.execute(sa.text("DELETE FROM roles WHERE is_system = true"))
    conn.execute(sa.text("DELETE FROM permissions"))
