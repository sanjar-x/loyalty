"""Tests for the idempotent seed sync command."""

import uuid

from src.modules.identity.management.seed_data import (
    _NS_PERMISSION,
    _NS_ROLE,
    ALL_PERMISSION_CODENAMES,
    PERMISSION_BY_CODENAME,
    PERMISSIONS,
    ROLE_BY_NAME,
    ROLE_HIERARCHY,
    ROLES,
)


class TestSeedDataIntegrity:
    """Validate the seed data itself — catches typos before they hit the DB."""

    def test_all_permissions_have_unique_ids(self):
        ids = [p.id for p in PERMISSIONS]
        assert len(ids) == len(set(ids))

    def test_all_permissions_have_unique_codenames(self):
        codenames = [p.codename for p in PERMISSIONS]
        assert len(codenames) == len(set(codenames))

    def test_all_codenames_follow_resource_action_format(self):
        for p in PERMISSIONS:
            assert ":" in p.codename, f"{p.codename} missing colon"
            resource, action = p.codename.split(":", 1)
            assert p.resource == resource
            assert p.action == action

    def test_permission_ids_are_deterministic_uuid5(self):
        for p in PERMISSIONS:
            expected = str(uuid.uuid5(_NS_PERMISSION, p.codename))
            assert p.id == expected, f"{p.codename}: expected {expected}, got {p.id}"

    def test_all_roles_have_unique_ids(self):
        ids = [r.id for r in ROLES]
        assert len(ids) == len(set(ids))

    def test_all_roles_have_unique_names(self):
        names = [r.name for r in ROLES]
        assert len(names) == len(set(names))

    def test_role_ids_are_deterministic_uuid5(self):
        for r in ROLES:
            expected = str(uuid.uuid5(_NS_ROLE, r.name))
            assert r.id == expected, f"{r.name}: expected {expected}, got {r.id}"

    def test_role_permissions_reference_existing_codenames(self):
        for role in ROLES:
            for codename in role.permissions:
                assert codename in PERMISSION_BY_CODENAME, (
                    f"Role '{role.name}' references unknown permission '{codename}'"
                )

    def test_admin_has_all_permissions(self):
        admin = ROLE_BY_NAME["admin"]
        assert set(admin.permissions) == set(ALL_PERMISSION_CODENAMES)

    def test_hierarchy_references_existing_roles(self):
        role_names = {r.name for r in ROLES}
        for h in ROLE_HIERARCHY:
            assert h.parent in role_names, f"Hierarchy parent '{h.parent}' not in ROLES"
            assert h.child in role_names, f"Hierarchy child '{h.child}' not in ROLES"

    def test_no_self_referencing_hierarchy(self):
        for h in ROLE_HIERARCHY:
            assert h.parent != h.child
