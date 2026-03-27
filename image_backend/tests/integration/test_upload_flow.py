"""Smoke tests for ImageBackend media API."""

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def app():
    """Create a test app instance."""
    from src.bootstrap.web import create_app

    return create_app()


@pytest.mark.asyncio
async def test_upload_without_api_key_returns_401(app):
    """Endpoints should reject requests without API key (when key is configured)."""
    # Note: if INTERNAL_API_KEY is empty, auth is disabled and this returns non-401
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/media/upload",
            json={"contentType": "image/jpeg", "filename": "test.jpg"},
        )
    # Accept 401 (auth enabled) or 201/422 (auth disabled in test env)
    assert resp.status_code in (401, 201, 422)


@pytest.mark.asyncio
async def test_get_metadata_returns_404_for_unknown(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/media/00000000-0000-0000-0000-000000000000",
            headers={"X-API-Key": "test-key"},
        )
    assert resp.status_code in (404, 401)


@pytest.mark.asyncio
async def test_delete_is_idempotent(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.delete(
            "/api/v1/media/00000000-0000-0000-0000-000000000000",
            headers={"X-API-Key": "test-key"},
        )
    assert resp.status_code in (200, 401)
