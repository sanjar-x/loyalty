"""E2E tests for the admin passport list endpoint (ADR-011, follow-up).

Covers the contract surface used by the admin walk-in passport selector:

* ``GET /api/v1/admin/passports?identityId=<uuid>`` — 200 + list when
  the customer has passports;
* the same endpoint returns 200 + empty list when the identity has no
  passports (admin UI surfaces «customer needs to add a passport»
  empty state without a 404 branch);
* ``401`` when called without a Bearer token;
* ``403`` when called by a customer-only token (RequireStaffRole guard).

Permission injection mirrors the ``admin_client`` fixture pattern: the
admin's identity is promoted to ``STAFF`` directly in the DB (so the
``RequireStaffRole`` check passes), and the per-session permission
cache in Redis is primed with ``passport:read``.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterable
from datetime import date

import jwt
import pytest
import redis.asyncio as aioredis
from dishka import AsyncContainer
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Local fixtures — promote a freshly-registered identity to STAFF and prime
# its Redis permission cache with ``passport:read``.
# ---------------------------------------------------------------------------


@pytest.fixture
async def passport_admin_client(
    async_client: AsyncClient,
    db_session: AsyncSession,
    app_container: AsyncContainer,
) -> AsyncIterable[AsyncClient]:
    email = f"passport-admin-{uuid.uuid4().hex[:8]}@test.com"
    password = "S3cure!AdminPass"

    await async_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"login": email, "password": password},
    )
    tokens = login_resp.json()
    access_token = tokens["accessToken"]
    payload = jwt.decode(access_token, options={"verify_signature": False})
    identity_id = uuid.UUID(payload["sub"])
    session_id = payload["sid"]

    # Promote to STAFF so RequireStaffRole passes.
    await db_session.execute(
        text("UPDATE identities SET account_type = 'STAFF' WHERE id = :id"),
        {"id": identity_id},
    )
    await db_session.flush()

    # Prime the Redis permission cache (Cache-Aside pattern — see
    # ``PermissionResolver``).
    cache_key = f"perms:{session_id}"
    redis_client: aioredis.Redis = await app_container.get(aioredis.Redis)
    await redis_client.set(cache_key, json.dumps(["passport:read"]), ex=300)

    async_client.headers["Authorization"] = f"Bearer {access_token}"
    yield async_client
    async_client.headers.pop("Authorization", None)
    await redis_client.delete(cache_key)


@pytest.fixture
async def seed_customer_with_passports(
    db_session: AsyncSession,
) -> dict:
    """Insert one CUSTOMER identity + two non-archived passports."""
    identity_id = uuid.uuid4()
    await db_session.execute(
        text(
            """
            INSERT INTO identities (id, primary_auth_method, account_type, is_active)
            VALUES (:id, 'LOCAL', 'CUSTOMER', true)
            """
        ),
        {"id": identity_id},
    )
    passport_ids: list[uuid.UUID] = []
    for i in range(2):
        pid = uuid.uuid4()
        passport_ids.append(pid)
        # Two passports with distinct INNs (mock checksum-valid INNs).
        inn = "500100732272" if i == 0 else "500100732259"
        await db_session.execute(
            text(
                """
                INSERT INTO passports (
                    id, identity_id, full_name_ru, full_name_lat,
                    passport_serial, passport_number, passport_issue_date,
                    birth_date, inn, validation_status, is_archived, version
                ) VALUES (
                    :id, :identity, :fn_ru, :fn_lat,
                    '1234', '567890', :pid, :bd, :inn,
                    'pending', false, 0
                )
                """
            ),
            {
                "id": pid,
                "identity": identity_id,
                "fn_ru": "Иван Иванов",
                "fn_lat": "Ivan Ivanov",
                "pid": date(2015, 5, 22),
                "bd": date(1990, 1, 1),
                "inn": inn,
            },
        )
    await db_session.flush()
    return {"identity_id": identity_id, "passport_ids": passport_ids}


@pytest.fixture
async def seed_customer_without_passports(
    db_session: AsyncSession,
) -> dict:
    """Insert one CUSTOMER identity with zero passports."""
    identity_id = uuid.uuid4()
    await db_session.execute(
        text(
            """
            INSERT INTO identities (id, primary_auth_method, account_type, is_active)
            VALUES (:id, 'LOCAL', 'CUSTOMER', true)
            """
        ),
        {"id": identity_id},
    )
    await db_session.flush()
    return {"identity_id": identity_id}


# ---------------------------------------------------------------------------
# Happy / empty / auth-gating cases
# ---------------------------------------------------------------------------


async def test_admin_lists_two_passports_for_target_identity(
    passport_admin_client: AsyncClient,
    seed_customer_with_passports: dict,
) -> None:
    resp = await passport_admin_client.get(
        "/api/v1/admin/passports",
        params={"identityId": str(seed_customer_with_passports["identity_id"])},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert {p["passportId"] for p in body["items"]} == {
        str(pid) for pid in seed_customer_with_passports["passport_ids"]
    }


async def test_admin_gets_empty_list_for_customer_without_passports(
    passport_admin_client: AsyncClient,
    seed_customer_without_passports: dict,
) -> None:
    """Empty list (200) rather than 404 — admin UI uses it as
    «customer has no passport yet» empty state."""
    resp = await passport_admin_client.get(
        "/api/v1/admin/passports",
        params={
            "identityId": str(seed_customer_without_passports["identity_id"]),
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["items"] == []


async def test_admin_gets_empty_list_for_unknown_identity(
    passport_admin_client: AsyncClient,
) -> None:
    resp = await passport_admin_client.get(
        "/api/v1/admin/passports",
        params={"identityId": str(uuid.uuid4())},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["items"] == []


async def test_admin_rejects_malformed_identity_uuid(
    passport_admin_client: AsyncClient,
) -> None:
    resp = await passport_admin_client.get(
        "/api/v1/admin/passports",
        params={"identityId": "not-a-uuid"},
    )
    assert resp.status_code == 422


async def test_customer_token_gets_403(
    authenticated_client: AsyncClient,
    seed_customer_with_passports: dict,
) -> None:
    """RequireStaffRole baseline rejects a customer JWT."""
    resp = await authenticated_client.get(
        "/api/v1/admin/passports",
        params={"identityId": str(seed_customer_with_passports["identity_id"])},
    )
    assert resp.status_code == 403


async def test_no_auth_returns_401(
    async_client: AsyncClient,
) -> None:
    resp = await async_client.get(
        "/api/v1/admin/passports",
        params={"identityId": str(uuid.uuid4())},
    )
    assert resp.status_code == 401
