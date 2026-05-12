"""
E2E contract tests for Brand admin endpoints.

Validates HTTP status codes, camelCase response shapes, and error handling
for all brand CRUD and bulk endpoints through the full HTTP stack.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.e2e.api.v1.catalog.conftest import create_brand

pytestmark = pytest.mark.asyncio


class TestBrandEndpoints:
    """Tests for /api/v1/catalog/brands endpoints."""

    # ── POST /brands ──

    async def test_create_brand_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        slug = f"nike-{uuid.uuid4().hex[:8]}"
        payload = {
            "name": "Nike",
            "slug": slug,
            "logoUrl": "https://cdn.example.com/nike.webp",
        }
        resp = await admin_client.post("/api/v1/catalog/brands", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data

    async def test_create_brand_duplicate_slug_returns_409(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        slug = f"dup-{uuid.uuid4().hex[:8]}"
        await admin_client.post(
            "/api/v1/catalog/brands", json={"name": "A", "slug": slug}
        )
        resp = await admin_client.post(
            "/api/v1/catalog/brands", json={"name": "B", "slug": slug}
        )
        assert resp.status_code == 409
        assert "error" in resp.json()

    async def test_create_brand_invalid_slug_returns_422(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        resp = await admin_client.post(
            "/api/v1/catalog/brands", json={"name": "X", "slug": "INVALID SLUG"}
        )
        assert resp.status_code == 422

    # ── POST /brands/bulk ──

    async def test_bulk_create_brands_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        items = [
            {"name": f"B{i}", "slug": f"bulk-b{i}-{uuid.uuid4().hex[:6]}"}
            for i in range(3)
        ]
        resp = await admin_client.post(
            "/api/v1/catalog/brands/bulk",
            json={"items": items, "skipExisting": False},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["createdCount"] == 3
        assert len(data["ids"]) == 3

    # ── GET /brands ──

    async def test_list_brands_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        await create_brand(admin_client)
        resp = await admin_client.get(
            "/api/v1/catalog/brands", params={"offset": 0, "limit": 10}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "offset" in data
        assert "limit" in data
        assert "hasNext" in data
        assert len(data["items"]) >= 1
        item = data["items"][0]
        assert "id" in item
        assert "name" in item
        assert "slug" in item

    # ── GET /brands/{brand_id} ──

    async def test_get_brand_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        created = await create_brand(admin_client)
        resp = await admin_client.get(f"/api/v1/catalog/brands/{created['id']}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == created["id"]

    async def test_get_brand_not_found_returns_404(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        fake_id = str(uuid.uuid4())
        resp = await admin_client.get(f"/api/v1/catalog/brands/{fake_id}")
        assert resp.status_code == 404

    # ── PATCH /brands/{brand_id} ──

    async def test_update_brand_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        created = await create_brand(admin_client)
        resp = await admin_client.patch(
            f"/api/v1/catalog/brands/{created['id']}", json={"name": "Updated"}
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

    # ── DELETE /brands/{brand_id} ──

    async def test_delete_brand_success(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        created = await create_brand(admin_client)
        resp = await admin_client.delete(f"/api/v1/catalog/brands/{created['id']}")
        assert resp.status_code == 204

    async def test_delete_brand_not_found_returns_404(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ):
        resp = await admin_client.delete(f"/api/v1/catalog/brands/{uuid.uuid4()}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# T-1.1 — ETag/If-Match optimistic locking on Brand
# ---------------------------------------------------------------------------


class TestBrandETagFlow:
    """Wire-level checks for the ETag/If-Match contract on Brand.

    Mirrors the Recipient pattern (Sprint 3 D0.3): GET emits
    ``ETag: "v{N}"``, PATCH accepts ``If-Match`` and surfaces 412 on
    stale versions, header-absent path keeps the legacy 200/409
    behaviour for clients that haven't adopted the contract yet.
    """

    async def test_get_brand_emits_etag_header(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        created = await create_brand(admin_client)
        resp = await admin_client.get(f"/api/v1/admin/catalog/brands/{created['id']}")
        assert resp.status_code == 200
        etag = resp.headers.get("etag")
        assert etag is not None
        # Strong validator: ``"v{N}"`` (no ``W/`` prefix).
        assert etag.startswith('"v')
        body = resp.json()
        assert "version" in body
        assert int(etag.strip('"').lstrip("v")) == body["version"]

    async def test_patch_with_matching_if_match_succeeds_and_bumps_version(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        created = await create_brand(admin_client)
        get_resp = await admin_client.get(
            f"/api/v1/admin/catalog/brands/{created['id']}"
        )
        etag = get_resp.headers["etag"]
        original_version = get_resp.json()["version"]

        patch_resp = await admin_client.patch(
            f"/api/v1/admin/catalog/brands/{created['id']}",
            json={"name": "ETag Updated"},
            headers={"If-Match": etag},
        )
        assert patch_resp.status_code == 200
        body = patch_resp.json()
        assert body["name"] == "ETag Updated"
        assert body["version"] > original_version
        # The updated ETag is reflected on the response.
        new_etag = patch_resp.headers.get("etag")
        assert new_etag is not None
        assert new_etag != etag

    async def test_patch_with_stale_if_match_returns_412(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        created = await create_brand(admin_client)
        # First update bumps version to 1 (or higher).
        await admin_client.patch(
            f"/api/v1/admin/catalog/brands/{created['id']}",
            json={"name": "First"},
            headers={"If-Match": '"v0"'},
        )
        # Replay the original v0 — must be rejected as stale.
        resp = await admin_client.patch(
            f"/api/v1/admin/catalog/brands/{created['id']}",
            json={"name": "Race"},
            headers={"If-Match": '"v0"'},
        )
        assert resp.status_code == 412
        body = resp.json()
        assert body["error"]["code"] == "PRECONDITION_FAILED"
        assert body["error"]["details"]["entity_type"] == "Brand"

    async def test_patch_without_if_match_keeps_legacy_200(
        self, admin_client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Header-absent path stays on last-write-wins (no breaking change)."""
        created = await create_brand(admin_client)
        resp = await admin_client.patch(
            f"/api/v1/admin/catalog/brands/{created['id']}",
            json={"name": "No If-Match"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "No If-Match"
