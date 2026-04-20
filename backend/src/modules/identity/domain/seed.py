"""System seed data for IAM roles, permissions, and hierarchy.

Single source of truth for all system-level RBAC configuration.
These constants are used by the sync command to upsert data into
the database idempotently on every deploy.

UUIDs are generated deterministically via uuid5(NAMESPACE, codename/name),
so adding a new entry only requires a codename and description.

To add a new permission or role:
1. Add it here.
2. Redeploy (sync runs automatically on startup).
"""

import uuid
from dataclasses import dataclass

# Fixed namespace for deterministic uuid5 generation.
# NEVER change this — it would regenerate all UUIDs and break FK references.
_NS_PERMISSION = uuid.UUID("a1b2c3d4-0000-4000-a000-000000000001")
_NS_ROLE = uuid.UUID("a1b2c3d4-0000-4000-a000-000000000002")


def _perm_id(codename: str) -> str:
    """Deterministic UUID for a permission codename."""
    return str(uuid.uuid5(_NS_PERMISSION, codename))


def _role_id(name: str) -> str:
    """Deterministic UUID for a role name."""
    return str(uuid.uuid5(_NS_ROLE, name))


@dataclass(frozen=True)
class SeedPermission:
    codename: str
    description: str

    @property
    def id(self) -> str:
        return _perm_id(self.codename)

    @property
    def resource(self) -> str:
        return self.codename.split(":")[0]

    @property
    def action(self) -> str:
        return self.codename.split(":")[1]


@dataclass(frozen=True)
class SeedRole:
    name: str
    description: str
    target_account_type: str | None
    permissions: list[str]  # codenames
    is_system: bool = True

    @property
    def id(self) -> str:
        return _role_id(self.name)


@dataclass(frozen=True)
class SeedHierarchy:
    parent: str  # role name
    child: str  # role name

    @property
    def parent_role_id(self) -> str:
        return _role_id(self.parent)

    @property
    def child_role_id(self) -> str:
        return _role_id(self.child)


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------

PERMISSIONS: list[SeedPermission] = [
    # ── Catalog ──────────────────────────────────────────────────────────
    SeedPermission("catalog:read", "Просмотр каталога (бренды, категории, товары)"),
    SeedPermission(
        "catalog:manage",
        "Управление каталогом (CRUD брендов, категорий, товаров, атрибутов, SKU)",
    ),
    # ── Orders ───────────────────────────────────────────────────────────
    SeedPermission("orders:read", "Просмотр заказов"),
    SeedPermission(
        "orders:manage", "Управление заказами (создание, смена статуса, отмена)"
    ),
    # ── Reviews ──────────────────────────────────────────────────────────
    SeedPermission("reviews:read", "Просмотр отзывов"),
    SeedPermission(
        "reviews:moderate", "Модерация отзывов (одобрение, отклонение, удаление)"
    ),
    # ── Returns ──────────────────────────────────────────────────────────
    SeedPermission("returns:read", "Просмотр возвратов"),
    SeedPermission("returns:manage", "Обработка возвратов"),
    # ── Profile (self-service) ───────────────────────────────────────────
    SeedPermission("profile:read", "Просмотр профиля"),
    SeedPermission("profile:update", "Редактирование профиля"),
    SeedPermission("profile:delete", "Удаление аккаунта (GDPR)"),
    # ── Admin IAM ────────────────────────────────────────────────────────
    SeedPermission("roles:manage", "Управление ролями и правами"),
    SeedPermission(
        "identities:manage",
        "Управление идентификациями (список, деактивация, назначение ролей)",
    ),
    # ── Staff ────────────────────────────────────────────────────────────
    SeedPermission(
        "staff:manage", "Управление сотрудниками (список, детали, деактивация)"
    ),
    SeedPermission("staff:invite", "Приглашение новых сотрудников"),
    # ── Customers ────────────────────────────────────────────────────────
    SeedPermission("customers:read", "Просмотр списка клиентов"),
    SeedPermission(
        "customers:manage", "Управление клиентами (деактивация, реактивация)"
    ),
    # ── Geo ──────────────────────────────────────────────────────────────
    SeedPermission(
        "geo:manage", "Управление гео-справочниками (страны, валюты, языки, регионы)"
    ),
    # ── Pricing ──────────────────────────────────────────────────────────
    SeedPermission(
        "pricing:read",
        "Просмотр pricing-профилей товаров и настроек ценообразования",
    ),
    SeedPermission(
        "pricing:manage",
        "Управление pricing-профилями товаров (upsert/delete product pricing inputs, category settings, freeze/unfreeze)",
    ),
    SeedPermission(
        "pricing:admin",
        "Администрирование pricing: CRUD контекстов/переменных, формулы, SupplierPricingSettings, SupplierTypeContextMapping (BR-17)",
    ),
]

PERMISSION_BY_CODENAME: dict[str, SeedPermission] = {p.codename: p for p in PERMISSIONS}
ALL_PERMISSION_CODENAMES: list[str] = [p.codename for p in PERMISSIONS]

# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

ROLES: list[SeedRole] = [
    SeedRole(
        name="admin",
        description="Администратор — полный доступ ко всем модулям системы",
        target_account_type="STAFF",
        permissions=ALL_PERMISSION_CODENAMES,
    ),
    SeedRole(
        name="manager",
        description="Менеджер — каталог, заказы, клиенты, отзывы, возвраты",
        target_account_type="STAFF",
        permissions=[
            "catalog:read",
            "catalog:manage",
            "orders:read",
            "orders:manage",
            "reviews:read",
            "reviews:moderate",
            "returns:read",
            "returns:manage",
            "profile:read",
            "customers:read",
            "customers:manage",
            "staff:manage",
            "staff:invite",
            "pricing:read",
            "pricing:manage",
        ],
    ),
    SeedRole(
        name="customer",
        description="Клиент — каталог, заказы, профиль, отзывы",
        target_account_type="CUSTOMER",
        permissions=[
            "catalog:read",
            "orders:read",
            "reviews:read",
            "profile:read",
            "profile:update",
            "profile:delete",
        ],
    ),
]

ROLE_BY_NAME: dict[str, SeedRole] = {r.name: r for r in ROLES}

# ---------------------------------------------------------------------------
# Role hierarchy
#   admin
#     └── manager
#           └── customer
# ---------------------------------------------------------------------------

ROLE_HIERARCHY: list[SeedHierarchy] = [
    SeedHierarchy(parent="admin", child="manager"),
    SeedHierarchy(parent="manager", child="customer"),
]
