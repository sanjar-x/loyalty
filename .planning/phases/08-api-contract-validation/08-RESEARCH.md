# Phase 8: API Contract Validation - Research

**Researched:** 2026-03-28
**Status:** Complete

## Objective

Determine everything needed to plan comprehensive E2E API contract tests for all 11 catalog REST routers, covering HTTP status codes, response shapes, authorization enforcement, pagination, and a full product lifecycle.

## Endpoint Inventory

### Admin Routers (10 routers, all under `/api/v1/catalog/`)

| Router | Prefix | Endpoints | Auth |
|--------|--------|-----------|------|
| **Brands** | `/brands` | POST, POST /bulk, GET, GET /{id}, PATCH /{id}, DELETE /{id} (6) | catalog:manage (write), catalog:read (read) |
| **Categories** | `/categories` | POST, POST /bulk, GET /tree, GET, GET /{id}, PATCH /{id}, DELETE /{id} (7) | catalog:manage (write), catalog:read (read) |
| **Attributes** | `/attributes` | POST, POST /bulk, GET, GET /{id}, PATCH /{id}, DELETE /{id}, GET /{id}/usage (7) | catalog:manage (write), catalog:read (read) |
| **Attribute Values** | `/attributes/{id}/values` | POST, POST /bulk, GET, GET /{id}, PATCH /{id}, PATCH /{id}/deactivate, PATCH /{id}/activate, DELETE /{id}, POST /reorder (9) | catalog:manage (write), catalog:read (read) |
| **Attribute Templates** | `/attribute-templates` | POST, POST /clone, GET, GET /{id}, PATCH /{id}, DELETE /{id}, POST /{id}/attributes, GET /{id}/attributes, PATCH /{id}/attributes/{bid}, DELETE /{id}/attributes/{bid}, POST /{id}/attributes/reorder (11) | catalog:manage (write), catalog:read (read) |
| **Products** | `/products` | POST, GET, GET /{id}, GET /{id}/completeness, PATCH /{id}, DELETE /{id}, PATCH /{id}/status (7) | catalog:manage (write), catalog:read (read) |
| **Variants** | `/products/{id}/variants` | POST, GET, PATCH /{vid}, DELETE /{vid} (4) | catalog:manage (write), catalog:read (read) |
| **SKUs** | `/products/{id}/variants/{vid}/skus` | POST, GET, POST /generate, PATCH /{sid}, DELETE /{sid} (5) | catalog:manage (write), catalog:read (read) |
| **Product Attributes** | `/products/{id}/attributes` | POST, GET, POST /bulk, DELETE /{aid} (4) | catalog:manage (write), catalog:read (read) |
| **Media** | `/products/{id}/media` | POST, GET, PATCH /{mid}, DELETE /{mid}, POST /reorder (5) | catalog:manage (write), catalog:read (read) |

**Total admin endpoints: 65**

### Storefront Router (1 router)

| Router | Prefix | Endpoints | Auth |
|--------|--------|-----------|------|
| **Storefront** | `/storefront/categories/{id}` | GET /filters, GET /card-attributes, GET /comparison-attributes, GET /form-attributes (4) | None (public) except form-attributes (catalog:manage) |

**Total storefront endpoints: 4**
**Grand total: 69 endpoints**

## Test Infrastructure Analysis

### Existing E2E Setup

- **conftest.py** (root): Session-scoped Dishka container, PostgreSQL engine with `Base.metadata.create_all()`, per-function `db_session` with savepoint rollback, Redis flush fixture
- **e2e/conftest.py**: `fastapi_app` (session scope), `async_client` (session scope, httpx ASGITransport), `authenticated_client` (registers user + login, no catalog perms), `admin_client` (registers user + login + seeds `catalog:manage` in Redis)
- **Existing tests**: `test_brands.py` (1 test), `test_categories.py` (2 tests) -- minimal, only success paths
- **Fixtures use**: Direct registration/login via `/api/v1/auth/register` + `/api/v1/auth/login`, then JWT decode to get session_id for Redis permission seeding

### Key Patterns

1. **httpx AsyncClient** with `ASGITransport(app=fastapi_app)` -- no real HTTP server needed
2. **DB isolation**: Each test gets its own savepoint that rolls back, so tests are independent
3. **Permission seeding**: `redis_client.set(f"perms:{session_id}", json.dumps(["catalog:manage"]), ex=300)`
4. **Response validation**: Assert `response.status_code`, then parse `response.json()` and check fields
5. **CamelCase responses**: All responses use camelCase field names (via CamelModel)

### What the Admin Client Needs

For the full lifecycle test and complex endpoint tests, the admin_client needs to:
1. Create prerequisite entities (brand, category, attribute, template, bindings) through the API
2. These persist within the test function because all DB operations share the same savepoint session

### Error Response Shape

All errors follow a uniform envelope:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {},
    "request_id": "..."
  }
}
```

Status codes:
- 401: Unauthorized (no token or invalid token)
- 403: Forbidden (valid token but missing permission)
- 404: NotFoundError (entity not found)
- 409: ConflictError (slug/code conflict, duplicate)
- 422: Validation error (Pydantic schema or domain business rule)

### Storefront Behavior

The storefront endpoints are public (no auth) except `form-attributes` which requires `catalog:manage`. They serve attribute metadata per category, not product listings. The current storefront router does NOT have product listing/detail/filtering endpoints -- it only serves attribute-related data for category-scoped filter/card/comparison/form views.

**Important observation**: The CONTEXT.md decision D-06 mentions "only PUBLISHED non-deleted products returned" and "product listing with pagination, product detail view, filtering by category/brand" for storefront. However, **no such endpoints exist in the storefront router**. The existing storefront only has attribute endpoints. Product listing/detail is served by the admin product router. This means:
- API-02 (storefront query endpoints) maps to the 4 existing storefront attribute endpoints
- Product listing from the storefront perspective is NOT implemented yet (no public product listing endpoint exists)
- Tests should verify the existing storefront endpoints work correctly

### Pagination Pattern

All paginated endpoints use `PaginatedResponse[S]`:
```json
{
  "items": [...],
  "total": 10,
  "offset": 0,
  "limit": 50,
  "hasNext": false
}
```

Query params: `offset` (default 0, ge=0), `limit` (default 50, ge=1, le=200 for most).

## Validation Architecture

### Test File Organization

Given 69 endpoints across 11 routers, organizing into a flat `tests/e2e/api/v1/` directory would create too many files mixed with auth/user tests. Recommended: create `tests/e2e/api/v1/catalog/` subdirectory.

Proposed files:
1. `test_brands.py` -- Brand CRUD endpoints (extend existing or create in catalog/)
2. `test_categories.py` -- Category CRUD + tree endpoints
3. `test_attributes.py` -- Attribute CRUD + usage endpoints
4. `test_attribute_values.py` -- AttributeValue CRUD + activate/deactivate/reorder
5. `test_attribute_templates.py` -- Template CRUD + binding endpoints
6. `test_products.py` -- Product CRUD + status change + completeness
7. `test_variants.py` -- Variant CRUD endpoints
8. `test_skus.py` -- SKU CRUD + matrix generation
9. `test_product_attributes.py` -- Product attribute assignment endpoints
10. `test_media.py` -- Media asset CRUD + reorder
11. `test_storefront.py` -- All 4 storefront endpoints
12. `test_auth_enforcement.py` -- Authorization 401/403 tests across all protected endpoints
13. `test_lifecycle.py` -- Full product lifecycle E2E test
14. `test_pagination.py` -- Pagination behavior tests

### Test Strategy per Endpoint

For each endpoint, test:
1. **Happy path**: Correct status code + response shape with camelCase fields
2. **Error path**: At least one error scenario (404 for non-existent ID, 422 for invalid input, 409 for conflict)
3. **Auth enforcement**: Covered by dedicated test_auth_enforcement.py

### Data Seeding Approach

Tests need prerequisite entities created through the API (not direct DB inserts) to test the full stack:
1. Helper functions that create brands, categories, attributes, etc. via POST calls
2. These helpers return the created entity IDs for use in subsequent test steps
3. All within the same test function (same DB savepoint)

### Known Complexities

1. **Media endpoints**: The `AddProductMediaHandler` may call ImageBackend HTTP service. In E2E tests, this call would fail. Need to check if there's a mock/stub or if internal media assets need `storage_object_id` validation bypassed.
2. **Product status transitions**: Publishing requires active SKU with price + media asset. The lifecycle test must create all prerequisites.
3. **Nested routes**: SKU routes are 4 levels deep: `/products/{pid}/variants/{vid}/skus/{sid}`. Each level needs valid parent IDs.
4. **Storefront endpoints need template+bindings**: The storefront attribute endpoints return data based on category templates. Tests need a category with an assigned template that has attribute bindings.

### Wave Planning

**Wave 1** (independent foundation tests):
- Brand, Category, Attribute, AttributeValue CRUD
- Auth enforcement (can be tested with any endpoint)
- Pagination tests

**Wave 2** (depends on Wave 1 entities existing in test):
- AttributeTemplate + bindings
- Product CRUD + status
- Storefront endpoints

**Wave 3** (depends on products):
- Variant, SKU, ProductAttribute, Media endpoints
- Full lifecycle test

## RESEARCH COMPLETE
