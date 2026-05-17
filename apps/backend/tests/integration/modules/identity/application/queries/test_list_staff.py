"""Integration tests for ListStaffHandler.

Covers the widening that lands data anomalies (legacy CUSTOMER carrying a
staff role, identity provisioned as STAFF but without a ``staff_members``
profile row) in the admin staff list, plus the two diagnostic booleans
the frontend uses to highlight those rows.
"""

import uuid
from datetime import UTC, datetime

from dishka import AsyncContainer
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.identity.application.queries.list_staff import (
    ListStaffHandler,
    ListStaffQuery,
)
from src.modules.identity.infrastructure.models import (
    IdentityModel,
    IdentityRoleModel,
    LocalCredentialsModel,
    RoleModel,
)
from src.modules.user.infrastructure.models import StaffMemberModel


async def _make_identity(
    db_session: AsyncSession,
    *,
    account_type: str,
    email: str,
) -> uuid.UUID:
    identity_id = uuid.uuid4()
    db_session.add(
        IdentityModel(
            id=identity_id,
            primary_auth_method="LOCAL",
            account_type=account_type,
            is_active=True,
        )
    )
    db_session.add(
        LocalCredentialsModel(identity_id=identity_id, email=email, password_hash="x")
    )
    await db_session.flush()
    return identity_id


async def _make_role(
    db_session: AsyncSession,
    *,
    name: str,
    target_account_type: str | None,
) -> uuid.UUID:
    role_id = uuid.uuid4()
    db_session.add(
        RoleModel(
            id=role_id,
            name=name,
            is_system=False,
            target_account_type=target_account_type,
        )
    )
    await db_session.flush()
    return role_id


async def _assign_role(
    db_session: AsyncSession, *, identity_id: uuid.UUID, role_id: uuid.UUID
) -> None:
    db_session.add(IdentityRoleModel(identity_id=identity_id, role_id=role_id))
    await db_session.flush()


async def _make_staff_profile(
    db_session: AsyncSession,
    *,
    identity_id: uuid.UUID,
    first_name: str,
    last_name: str,
) -> None:
    db_session.add(
        StaffMemberModel(
            id=identity_id,
            first_name=first_name,
            last_name=last_name,
            invited_by=identity_id,
            created_at=datetime.now(UTC),
        )
    )
    await db_session.flush()


def _item_for(items, identity_id):
    matched = [it for it in items if it.identity_id == identity_id]
    assert len(matched) == 1, (
        f"identity {identity_id} expected exactly once, got {len(matched)}"
    )
    return matched[0]


async def test_canonical_staff_with_profile_visible(
    app_container: AsyncContainer, db_session: AsyncSession
) -> None:
    admin_role = await _make_role(
        db_session,
        name=f"role_admin_{uuid.uuid4().hex[:6]}",
        target_account_type="STAFF",
    )
    identity_id = await _make_identity(
        db_session, account_type="STAFF", email=f"staff-{uuid.uuid4().hex[:6]}@x.io"
    )
    await _assign_role(db_session, identity_id=identity_id, role_id=admin_role)
    await _make_staff_profile(
        db_session, identity_id=identity_id, first_name="Анна", last_name="Иванова"
    )

    result = await ListStaffHandler(db_session).handle(ListStaffQuery(limit=100))

    item = _item_for(result.items, identity_id)
    assert item.first_name == "Анна"
    assert item.last_name == "Иванова"
    assert item.has_staff_member_profile is True
    assert item.account_type_mismatch is False


async def test_staff_identity_without_profile_still_visible(
    app_container: AsyncContainer, db_session: AsyncSession
) -> None:
    # account_type=STAFF but no staff_members row — outbox dropped the event
    # or a legacy admin was inserted by hand. Row must still appear so the
    # admin can see and remediate the gap.
    identity_id = await _make_identity(
        db_session,
        account_type="STAFF",
        email=f"lost-{uuid.uuid4().hex[:6]}@x.io",
    )

    result = await ListStaffHandler(db_session).handle(ListStaffQuery(limit=100))

    item = _item_for(result.items, identity_id)
    assert item.first_name is None
    assert item.last_name is None
    assert item.has_staff_member_profile is False
    assert item.account_type_mismatch is False


async def test_customer_with_staff_role_surfaces_as_mismatch(
    app_container: AsyncContainer, db_session: AsyncSession
) -> None:
    # Legacy data anomaly: CUSTOMER identity with admin role assigned
    # directly in identity_roles, bypassing AccountTypeMismatchError on
    # AssignRoleHandler. Widening the list catches this so it isn't
    # silently invisible to the admin panel.
    admin_role = await _make_role(
        db_session,
        name=f"role_admin_{uuid.uuid4().hex[:6]}",
        target_account_type="STAFF",
    )
    identity_id = await _make_identity(
        db_session,
        account_type="CUSTOMER",
        email=f"mismatch-{uuid.uuid4().hex[:6]}@x.io",
    )
    await _assign_role(db_session, identity_id=identity_id, role_id=admin_role)

    result = await ListStaffHandler(db_session).handle(ListStaffQuery(limit=100))

    item = _item_for(result.items, identity_id)
    assert item.account_type_mismatch is True
    assert item.has_staff_member_profile is False
    assert item.first_name is None


async def test_plain_customer_excluded(
    app_container: AsyncContainer, db_session: AsyncSession
) -> None:
    customer_role = await _make_role(
        db_session,
        name=f"role_customer_{uuid.uuid4().hex[:6]}",
        target_account_type="CUSTOMER",
    )
    identity_id = await _make_identity(
        db_session,
        account_type="CUSTOMER",
        email=f"plain-{uuid.uuid4().hex[:6]}@x.io",
    )
    await _assign_role(db_session, identity_id=identity_id, role_id=customer_role)

    result = await ListStaffHandler(db_session).handle(ListStaffQuery(limit=100))

    assert all(it.identity_id != identity_id for it in result.items)


async def test_role_id_filter_narrows_against_staff_signal(
    app_container: AsyncContainer, db_session: AsyncSession
) -> None:
    # Two staff roles, one identity per role. ``role_id`` must constrain
    # the returned set to that role only (the staff-signal OR alone would
    # otherwise return both).
    admin_role = await _make_role(
        db_session,
        name=f"role_admin_{uuid.uuid4().hex[:6]}",
        target_account_type="STAFF",
    )
    manager_role = await _make_role(
        db_session,
        name=f"role_manager_{uuid.uuid4().hex[:6]}",
        target_account_type="STAFF",
    )
    admin_id = await _make_identity(
        db_session, account_type="STAFF", email=f"a-{uuid.uuid4().hex[:6]}@x.io"
    )
    manager_id = await _make_identity(
        db_session, account_type="STAFF", email=f"m-{uuid.uuid4().hex[:6]}@x.io"
    )
    await _assign_role(db_session, identity_id=admin_id, role_id=admin_role)
    await _assign_role(db_session, identity_id=manager_id, role_id=manager_role)

    result = await ListStaffHandler(db_session).handle(
        ListStaffQuery(limit=100, role_id=admin_role)
    )

    ids = {it.identity_id for it in result.items}
    assert admin_id in ids
    assert manager_id not in ids
