# Phase 8: API Contract Validation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.

**Date:** 2026-03-28
**Phase:** 08-API Contract Validation
**Mode:** auto
**Areas discussed:** Test type, Admin coverage, Storefront, Auth enforcement, Lifecycle, Pagination

---

## Test Type

| Option | Description | Selected |
|--------|-------------|----------|
| E2E with httpx | Full FastAPI stack, same as existing tests | ✓ |
| Integration without HTTP | Test handlers directly with DI container | |

**User's choice:** [auto] E2E with httpx (recommended default)

## Admin Endpoint Coverage

| Option | Description | Selected |
|--------|-------------|----------|
| All 10 routers | Comprehensive API contract coverage | ✓ |
| High-priority only | Products, variants, SKUs only | |

**User's choice:** [auto] All 10 routers (recommended default)

## Auth Enforcement

| Option | Description | Selected |
|--------|-------------|----------|
| Per-router 401 + 403 | One auth test pair per router | ✓ |
| Centralized auth tests | Test auth in one file for all endpoints | |

**User's choice:** [auto] Per-router (recommended default)

## Deferred Ideas

- Schemathesis fuzzing → v2 ADV-01
- Load testing → v2 PERF-03
- API docs generation → v2 DOC-01
