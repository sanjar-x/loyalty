# tests/e2e/api/v1/test_auth_telegram.py
"""E2E tests for POST /api/v1/auth/telegram."""

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.bootstrap.config import settings

pytestmark = pytest.mark.asyncio


def _build_init_data(
    user_id: int = 123456789,
    first_name: str = "Test",
    last_name: str | None = "User",
    username: str | None = "testuser",
    auth_date: int | None = None,
    start_param: str | None = None,
    bot_token: str | None = None,
) -> str:
    """Build a valid Telegram initData string with correct HMAC-SHA256."""
    token = bot_token or settings.BOT_TOKEN.get_secret_value()
    if auth_date is None:
        auth_date = int(time.time())

    user_obj = {"id": user_id, "first_name": first_name}
    if last_name:
        user_obj["last_name"] = last_name
    if username:
        user_obj["username"] = username

    params = {
        "user": json.dumps(user_obj, separators=(",", ":")),
        "auth_date": str(auth_date),
    }
    if start_param:
        params["start_param"] = start_param

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))

    secret_key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    hash_value = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    params["hash"] = hash_value
    return urlencode(params)


async def test_login_telegram_new_user_returns_tokens(
    async_client: AsyncClient, db_session: AsyncSession
):
    init_data = _build_init_data(user_id=900001)
    response = await async_client.post(
        "/api/v1/auth/telegram",
        headers={"Authorization": f"tma {init_data}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "accessToken" in data
    assert "refreshToken" in data
    assert data["tokenType"] == "bearer"
    assert data["isNewUser"] is True


async def test_login_telegram_existing_user_returns_is_new_false(
    async_client: AsyncClient, db_session: AsyncSession
):
    user_id = 900002
    init_data = _build_init_data(user_id=user_id)
    await async_client.post(
        "/api/v1/auth/telegram",
        headers={"Authorization": f"tma {init_data}"},
    )
    init_data2 = _build_init_data(user_id=user_id, first_name="Updated")
    response = await async_client.post(
        "/api/v1/auth/telegram",
        headers={"Authorization": f"tma {init_data2}"},
    )
    assert response.status_code == 200
    assert response.json()["isNewUser"] is False


async def test_login_telegram_invalid_signature_returns_401(
    async_client: AsyncClient,
):
    init_data = _build_init_data(bot_token="wrong:token")
    response = await async_client.post(
        "/api/v1/auth/telegram",
        headers={"Authorization": f"tma {init_data}"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_INIT_DATA"


async def test_login_telegram_expired_returns_401(
    async_client: AsyncClient,
):
    old_time = int(time.time()) - 600
    init_data = _build_init_data(auth_date=old_time)
    response = await async_client.post(
        "/api/v1/auth/telegram",
        headers={"Authorization": f"tma {init_data}"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INIT_DATA_EXPIRED"


async def test_login_telegram_missing_tma_header_returns_401(
    async_client: AsyncClient,
):
    response = await async_client.post(
        "/api/v1/auth/telegram",
        headers={"Authorization": "Bearer some_token"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_AUTH_SCHEME"


async def test_login_telegram_no_auth_header_returns_401(
    async_client: AsyncClient,
):
    response = await async_client.post("/api/v1/auth/telegram")
    assert response.status_code == 401


async def test_refresh_works_after_telegram_login(
    async_client: AsyncClient, db_session: AsyncSession
):
    init_data = _build_init_data(user_id=900010)
    login_resp = await async_client.post(
        "/api/v1/auth/telegram",
        headers={"Authorization": f"tma {init_data}"},
    )
    refresh_token = login_resp.json()["refreshToken"]
    refresh_resp = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": refresh_token},
    )
    assert refresh_resp.status_code == 200
    assert "accessToken" in refresh_resp.json()


async def test_logout_works_after_telegram_login(
    async_client: AsyncClient, db_session: AsyncSession
):
    init_data = _build_init_data(user_id=900011)
    login_resp = await async_client.post(
        "/api/v1/auth/telegram",
        headers={"Authorization": f"tma {init_data}"},
    )
    access_token = login_resp.json()["accessToken"]
    logout_resp = await async_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert logout_resp.status_code == 200


async def test_login_telegram_deactivated_identity_returns_403(
    async_client: AsyncClient, db_session: AsyncSession
):
    user_id = 900020
    init_data = _build_init_data(user_id=user_id)
    await async_client.post(
        "/api/v1/auth/telegram",
        headers={"Authorization": f"tma {init_data}"},
    )
    await db_session.execute(
        text("""
            UPDATE identities SET is_active = false,
            deactivated_at = now()
            WHERE id = (
                SELECT identity_id FROM linked_accounts
                WHERE provider = 'telegram' AND provider_sub_id = :tid::text
            )
        """),
        {"tid": user_id},
    )
    await db_session.commit()
    init_data2 = _build_init_data(user_id=user_id)
    response = await async_client.post(
        "/api/v1/auth/telegram",
        headers={"Authorization": f"tma {init_data2}"},
    )
    assert response.status_code == 403


async def test_login_telegram_session_eviction(async_client: AsyncClient, db_session: AsyncSession):
    user_id = 900030
    for _ in range(5):
        init_data = _build_init_data(user_id=user_id)
        resp = await async_client.post(
            "/api/v1/auth/telegram",
            headers={"Authorization": f"tma {init_data}"},
        )
        assert resp.status_code == 200

    init_data = _build_init_data(user_id=user_id)
    resp = await async_client.post(
        "/api/v1/auth/telegram",
        headers={"Authorization": f"tma {init_data}"},
    )
    assert resp.status_code == 200

    result = await db_session.execute(
        text("""
            SELECT count(*) FROM sessions
            WHERE identity_id = (
                SELECT identity_id FROM linked_accounts
                WHERE provider = 'telegram' AND provider_sub_id = :tid::text
            )
            AND is_revoked = false
            AND expires_at > now()
        """),
        {"tid": user_id},
    )
    active_count = result.scalar()
    assert active_count <= 5


async def test_login_telegram_referral_start_param(
    async_client: AsyncClient, db_session: AsyncSession
):
    init_data = _build_init_data(user_id=900040, start_param="TESTREF")
    response = await async_client.post(
        "/api/v1/auth/telegram",
        headers={"Authorization": f"tma {init_data}"},
    )
    assert response.status_code == 200
    assert response.json()["isNewUser"] is True
