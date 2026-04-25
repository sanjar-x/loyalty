"""Idempotent sync of system roles, permissions, and hierarchy.

Reads the single source of truth from ``identity.management.seed_data`` and
upserts into the database using ``INSERT ... ON CONFLICT DO UPDATE``.

Safe to run on every deploy — if nothing changed, nothing is written.

Usage:
    # Standalone
    python -m src.modules.identity.management.sync_system_roles

    # Called from application lifespan (see bootstrap/web.py)
    await sync_system_roles(session_factory)
"""

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.modules.identity.management.seed_data import (
    PERMISSIONS,
    ROLE_HIERARCHY,
    ROLES,
    SeedPermission,
    SeedRole,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# SQL — PostgreSQL ON CONFLICT upsert
# ---------------------------------------------------------------------------

_UPSERT_PERMISSION = text("""
    INSERT INTO permissions (id, codename, resource, action, description)
    VALUES (:id, :codename, :resource, :action, :description)
    ON CONFLICT (id) DO UPDATE SET
        codename    = EXCLUDED.codename,
        resource    = EXCLUDED.resource,
        action      = EXCLUDED.action,
        description = EXCLUDED.description
""")

_UPSERT_ROLE = text("""
    INSERT INTO roles (id, name, description, is_system, target_account_type)
    VALUES (:id, :name, :description, :is_system, :target_account_type)
    ON CONFLICT (id) DO UPDATE SET
        name                = EXCLUDED.name,
        description         = EXCLUDED.description,
        is_system           = EXCLUDED.is_system,
        target_account_type = EXCLUDED.target_account_type
""")

_UPSERT_ROLE_PERMISSION = text("""
    INSERT INTO role_permissions (role_id, permission_id)
    VALUES (:role_id, :permission_id)
    ON CONFLICT (role_id, permission_id) DO NOTHING
""")

_DELETE_STALE_ROLE_PERMISSIONS = text("""
    DELETE FROM role_permissions
    WHERE role_id = :role_id
      AND permission_id NOT IN (
          SELECT unnest(cast(:permission_ids AS uuid[]))
      )
""")

_UPSERT_HIERARCHY = text("""
    INSERT INTO role_hierarchy (parent_role_id, child_role_id)
    VALUES (:parent_role_id, :child_role_id)
    ON CONFLICT (parent_role_id, child_role_id) DO NOTHING
""")

_DELETE_STALE_HIERARCHY = text("""
    DELETE FROM role_hierarchy
    WHERE (parent_role_id, child_role_id) NOT IN (
        SELECT unnest(cast(:parents AS uuid[])),
               unnest(cast(:children AS uuid[]))
    )
""")


# ---------------------------------------------------------------------------
# Core sync logic
# ---------------------------------------------------------------------------


def _perm_params(p: SeedPermission) -> dict:
    return {
        "id": p.id,
        "codename": p.codename,
        "resource": p.resource,
        "action": p.action,
        "description": p.description,
    }


def _role_params(r: SeedRole) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "description": r.description,
        "is_system": r.is_system,
        "target_account_type": r.target_account_type,
    }


async def sync_system_roles(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Upsert all system permissions, roles, role-permissions, and hierarchy.

    This function is idempotent: running it multiple times produces the
    same database state. It also removes stale role_permissions and
    hierarchy rows that no longer match the seed data.
    """
    perm_by_codename = {p.codename: p for p in PERMISSIONS}

    async with session_factory() as session, session.begin():
        # 1. Upsert permissions
        for permission in PERMISSIONS:
            await session.execute(_UPSERT_PERMISSION, _perm_params(permission))

        # 2. Upsert roles
        for role in ROLES:
            await session.execute(_UPSERT_ROLE, _role_params(role))

        # 3. Upsert role ↔ permission mappings + prune stale
        for role in ROLES:
            perm_ids = [perm_by_codename[codename].id for codename in role.permissions]

            for perm_id in perm_ids:
                await session.execute(
                    _UPSERT_ROLE_PERMISSION,
                    {"role_id": role.id, "permission_id": perm_id},
                )

            # Remove permissions no longer in the seed for this role
            await session.execute(
                _DELETE_STALE_ROLE_PERMISSIONS,
                {"role_id": role.id, "permission_ids": perm_ids},
            )

        # 4. Upsert hierarchy + prune stale
        for h in ROLE_HIERARCHY:
            await session.execute(
                _UPSERT_HIERARCHY,
                {
                    "parent_role_id": h.parent_role_id,
                    "child_role_id": h.child_role_id,
                },
            )

        parents = [h.parent_role_id for h in ROLE_HIERARCHY]
        children = [h.child_role_id for h in ROLE_HIERARCHY]
        await session.execute(
            _DELETE_STALE_HIERARCHY,
            {"parents": parents, "children": children},
        )

    logger.info(
        "system_roles.synced",
        permissions=len(PERMISSIONS),
        roles=len(ROLES),
        hierarchy=len(ROLE_HIERARCHY),
    )


# ---------------------------------------------------------------------------
# Standalone entry point: python -m src.modules.identity.management.sync_system_roles
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.bootstrap.container import create_container
    from src.bootstrap.logger import setup_logging

    setup_logging()

    async def main() -> None:
        container = create_container()
        async with container() as app_scope:
            factory = await app_scope.get(async_sessionmaker[AsyncSession])
            await sync_system_roles(factory)
        await container.close()
        print("Seed sync complete.")

    asyncio.run(main())
