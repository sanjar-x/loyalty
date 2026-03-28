# Phase 8: API Contract Validation - Context

**Gathered:** 2026-03-28 (auto mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Prove all catalog REST endpoints return correct HTTP status codes, response shapes (camelCase JSON via CamelModel), authorization enforcement, and pagination behavior through the full HTTP stack. This is the final testing layer — E2E tests through FastAPI with httpx AsyncClient. Prior phases tested domain (2-3), handlers (4-6), and repositories (7) in isolation.

</domain>

<decisions>
## Implementation Decisions

### Test Type
- **D-01:** E2E tests using httpx AsyncClient with ASGITransport through the full FastAPI stack. Same pattern as existing test_brands.py and test_categories.py in tests/e2e/api/v1/.
- **D-02:** Tests use admin_client (with catalog:manage permissions seeded in Redis) and authenticated_client (regular user, no catalog perms) fixtures from e2e conftest.

### Admin Endpoint Coverage (API-01)
- **D-03:** Test ALL 10 catalog admin routers. Extend existing test_brands.py and test_categories.py where gaps exist. Create new files for: test_products.py, test_variants.py, test_skus.py, test_attributes.py, test_attribute_templates.py, test_attribute_values.py, test_media.py, test_product_attributes.py.
- **D-04:** For each endpoint: test success response (correct status code + JSON shape) and at least one error response (400/404/409/422).
- **D-05:** Response shape assertions: verify camelCase field names (CamelModel), presence of required fields (id, slug, createdAt, etc.), correct nested object shapes.

### Storefront Endpoints (API-02)
- **D-06:** Dedicated test_storefront.py. Verify: only PUBLISHED non-deleted products returned, product listing with pagination, product detail view, filtering by category/brand.
- **D-07:** Storefront is a public (or customer-authenticated) endpoint — test that it works WITHOUT admin permissions.

### Authorization Enforcement (API-03)
- **D-08:** For each admin router: one test verifying unauthenticated request returns 401, one test verifying missing catalog:manage permission returns 403.
- **D-09:** Use existing fixtures: admin_client (has perms) for success, authenticated_client (no catalog perms) for 403, raw httpx client (no auth) for 401.

### Full Lifecycle E2E (API-04)
- **D-10:** One comprehensive test covering: create brand → create category → create attribute template → bind attribute → create product → add variant → add SKU → change status to PUBLISHED → query storefront → verify product appears.
- **D-11:** This test goes in test_lifecycle.py — separate from per-endpoint tests because it spans multiple routers.

### Pagination (API-05)
- **D-12:** Test pagination on at least 2 list endpoints (brands list, products list). Verify: correct offset/limit in response, total count, empty results (offset beyond total), boundary conditions (limit=0 if supported).
- **D-13:** Pagination tests can be in each endpoint's test file or grouped in test_pagination.py. Claude's discretion.

### Test Organization
- **D-14:** All files under `backend/tests/e2e/api/v1/catalog/` subdirectory to separate from identity/auth tests. Or follow existing flat structure in `tests/e2e/api/v1/` — Claude's discretion based on file count.
- **D-15:** One test class per router/concern: TestBrandEndpoints, TestProductEndpoints, TestStorefrontEndpoints, TestCatalogAuth, TestProductLifecycle, TestPagination.

### Claude's Discretion
- Whether to create tests/e2e/api/v1/catalog/ subdirectory or keep flat
- Exact error scenarios per endpoint (which 400/404/409/422 paths to test)
- Whether pagination tests are grouped or per-endpoint
- Amount of storefront filtering scenarios
- Whether to test CamelModel JSON transformation explicitly or trust schema

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Catalog routers (source of truth for endpoints)
- `backend/src/modules/catalog/presentation/router_brands.py` — Brand CRUD endpoints
- `backend/src/modules/catalog/presentation/router_categories.py` — Category CRUD + tree endpoints
- `backend/src/modules/catalog/presentation/router_products.py` — Product CRUD endpoints
- `backend/src/modules/catalog/presentation/router_variants.py` — Variant management endpoints
- `backend/src/modules/catalog/presentation/router_skus.py` — SKU management endpoints
- `backend/src/modules/catalog/presentation/router_attributes.py` — Attribute CRUD endpoints
- `backend/src/modules/catalog/presentation/router_attribute_templates.py` — Template management
- `backend/src/modules/catalog/presentation/router_attribute_values.py` — Value management
- `backend/src/modules/catalog/presentation/router_product_attributes.py` — Product attribute assignment
- `backend/src/modules/catalog/presentation/router_media.py` — Media management
- `backend/src/modules/catalog/presentation/router_storefront.py` — Public storefront queries

### Schemas (response shapes)
- `backend/src/modules/catalog/presentation/schemas.py` — All request/response Pydantic schemas (CamelModel)
- `backend/src/shared/schemas.py` — CamelModel base, PaginatedResponse

### Auth fixtures
- `backend/src/modules/catalog/presentation/dependencies.py` — RequirePermission("catalog:manage")
- `backend/src/modules/identity/presentation/dependencies.py` — Auth dependency (get_auth_context)

### Existing E2E tests (extend, don't duplicate)
- `backend/tests/e2e/conftest.py` — FastAPI app, httpx AsyncClient, admin_client, authenticated_client fixtures
- `backend/tests/e2e/api/v1/test_brands.py` — Existing brand E2E tests
- `backend/tests/e2e/api/v1/test_categories.py` — Existing category E2E tests

### API documentation
- `backend/docs/api/product-creation-flow.md` — Product creation flow documentation

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- admin_client fixture with catalog:manage permissions seeded in Redis
- authenticated_client fixture (regular user, no catalog perms)
- Existing test_brands.py and test_categories.py patterns
- Polyfactory ORM factories for DB seeding in E2E tests

### Established Patterns
- E2E tests use httpx.AsyncClient with ASGITransport(app=fastapi_app)
- Auth: permissions seeded in Redis via `redis_client.set(f"perms:{session_id}", json.dumps([...]))`
- Response assertions: check status_code, then parse response.json() and verify fields
- CamelModel transforms snake_case → camelCase automatically

### Integration Points
- New test files under `backend/tests/e2e/api/v1/`
- Tests import nothing from src — they only make HTTP calls and check responses
- DB seeding done via ORM factories or direct httpx POST calls
- Redis seeding for permissions

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. The full lifecycle test (API-04) is the most valuable single test in this phase — it proves the entire catalog stack works end-to-end.

</specifics>

<deferred>
## Deferred Ideas

- Schemathesis API fuzzing from OpenAPI spec — v2 ADV-01
- Load testing with Locust for catalog endpoints — v2 PERF-03
- API contract documentation generation — v2 DOC-01

</deferred>

---

*Phase: 08-api-contract-validation*
*Context gathered: 2026-03-28*
