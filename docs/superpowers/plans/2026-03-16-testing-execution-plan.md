# Testing Architecture — Execution Plan

> **Date:** 2026-03-16
> **Spec:** `docs/specs/testing-design-specification.md`
> **Orchestration:** `superpowers:subagent-driven-development` with worktree isolation
> **Goal:** Implement the full Testing Design Specification in 5 sequential chunks with maximum intra-chunk parallelism

---

## Dependency Graph

```
Chunk 1 (Foundation)
    │
    ├──→ Chunk 2 (Data Generation)    ← depends on working fixtures
    │        │
    │        ├──→ Chunk 3a (Architecture Tests)  ← no data deps, only pytest infra
    │        └──→ Chunk 3b (Unit Tests)          ← depends on Object Mothers
    │                 │
    │                 └──→ Chunk 4 (Integration Tests)  ← depends on fixtures + factories + passing unit tests
    │                          │
    │                          └──→ Chunk 5 (E2E + Load) ← depends on full stack working
    │
    └──→ Chunk 3a can start in parallel with Chunk 2 (no shared files)
```

---

## Current State Audit

| Area | Status | Files |
|------|--------|-------|
| `tests/conftest.py` | **Exists, needs hardening** — missing `join_transaction_mode`, fail-fast DB check, ContextVar reset, uses `AsyncMock` instead of Fake for `IBlobStorage` |
| `tests/integration/conftest.py` | **Exists, correct** — already uses `join_transaction_mode="create_savepoint"` |
| `tests/e2e/conftest.py` | **Exists, correct** — ASGI transport, session-scoped app |
| `tests/unit/conftest.py` | **Exists, empty** — correct (unit tests need no DB) |
| `tests/architecture/conftest.py` | **Missing** — needs `pytestmark` |
| `pyproject.toml` `[tool.pytest]` | **Partial** — missing `asyncio_mode`, `filterwarnings`, full marker list |
| Object Mothers | **Missing** — no `identity_mothers.py`, `catalog_mothers.py`, `user_mothers.py`, `storage_mothers.py` |
| Builders | **Missing** — no `builders.py` |
| ORM Factories | **Empty** — `catalog_factories.py` and `storage_factories.py` exist but are empty |
| Fakes/Stubs | **Missing** — `InMemoryBlobStorage`, `StubOIDCProvider` not created |
| Architecture tests | **Exists, partial** — 9 rules, missing parameterized framework checks and reverse-layer rules |
| Unit tests | **Exists, partial** — Identity (13), Catalog (11), User (6). Missing: Storage, events, value objects expansion |
| Integration tests | **Exists, partial** — Catalog only (8 tests). Missing: Identity, User, Storage handlers |
| E2E tests | **Exists, minimal** — Brands (2), Categories (2). Missing: Auth, Users, error paths |
| Load tests | **Exists, skeleton** — 1 scenario. Missing: auth_flow, connection_pool, thresholds.yml |

---

## Chunk 1: Foundation (Test Infrastructure)

> **Effort:** Critical
> **Files touched:** 6 files (all in `tests/` root and config)
> **Parallelism:** `[SEQUENTIAL]` — these files are the root of the fixture DAG; concurrent edits will conflict

### Tasks

- [ ] **1.1** Update `pyproject.toml` `[tool.pytest.ini_options]` — Effort: Low
  - Add `asyncio_mode = "auto"`
  - Add full marker list (`architecture`, `unit`, `integration`, `e2e`, `load`)
  - Add `filterwarnings = ["ignore::DeprecationWarning:dishka.*"]`
  - Add `testpaths = ["tests"]`
  - **File:** `pyproject.toml`

- [ ] **1.2** Harden `tests/conftest.py` — root fixture upgrade — Effort: High
  - Add fail-fast DB connectivity check in `test_engine` fixture (`SELECT 1` with `pytest.exit()` on failure)
  - Add `join_transaction_mode="create_savepoint"` to the root `db_session` fixture (currently missing — the integration conftest has it, but root doesn't)
  - Replace `AsyncMock(spec=IBlobStorage)` with a proper `InMemoryBlobStorage` Fake (Task 1.4)
  - Add `_reset_context_vars` autouse fixture for `request_id` ContextVar isolation
  - Add Redis FLUSHDB autouse fixture for per-test cache isolation
  - **File:** `tests/conftest.py`

- [ ] **1.3** Create `tests/architecture/conftest.py` — Effort: Low
  - Add `pytestmark = pytest.mark.architecture`
  - **File:** `tests/architecture/conftest.py`

- [ ] **1.4** Create `tests/fakes/` directory with test doubles — Effort: Medium
  - `tests/fakes/__init__.py`
  - `tests/fakes/blob_storage.py` — `InMemoryBlobStorage` implementing `IBlobStorage` (dict-based file store with `generate_presigned_put_url`, `generate_presigned_get_url`, `object_exists`, `delete_object`)
  - `tests/fakes/oidc_provider.py` — `StubOIDCProvider` implementing `IOIDCProvider` (returns configurable `OIDCUserInfo`)
  - **Files:** 3 new files in `tests/fakes/`

- [ ] **1.5** Wire Fakes into `TestOverridesProvider` — Effort: Low
  - Add `IOIDCProvider` override using `StubOIDCProvider` in `tests/conftest.py`
  - Replace `AsyncMock(spec=IBlobStorage)` with `InMemoryBlobStorage`
  - **File:** `tests/conftest.py` (same as 1.2, do together)

- [ ] **1.6** Create `tests/factories/__init__.py` — Effort: Low
  - Ensure the package is importable
  - **File:** `tests/factories/__init__.py`

### Verification Gate

```bash
# All existing tests must still pass after foundation changes
uv run pytest tests/ -v --tb=short -x
# Specifically: architecture (9 rules) + unit (32 tests) + integration (8 tests) + e2e (4 tests)
```

---

## Chunk 2: Data Generation (Object Mothers & Factories)

> **Effort:** Medium
> **Files touched:** 7 new files in `tests/factories/`
> **Parallelism:** `[PARALLEL]` — each module's Object Mother is an independent file with no shared state. Safe for concurrent subagent worktrees.

### Tasks

- [ ] **2.1** `tests/factories/identity_mothers.py` — Effort: Medium `[PARALLEL]`
  - `IdentityMothers`: `active_local()`, `active_oidc()`, `deactivated()`, `with_session()`, `with_credentials()`
  - `SessionMothers`: `active()`, `expired()`, `revoked()`
  - `RoleMothers`: `customer()`, `admin()`, `system_role()`
  - `PermissionMothers`: `brand_create()`, `brand_read()`, `category_manage()`
  - `LinkedAccountMothers`: `google()`, `github()`
  - **Depends on:** `src/modules/identity/domain/entities.py`, `value_objects.py`

- [ ] **2.2** `tests/factories/catalog_mothers.py` — Effort: Medium `[PARALLEL]`
  - `BrandMothers`: `without_logo()`, `with_pending_logo()`, `with_completed_logo()`, `with_failed_logo()`
  - `CategoryMothers`: `root()`, `child(parent)`, `deep_nested(depth=3)`
  - **Depends on:** `src/modules/catalog/domain/entities.py`, `value_objects.py`

- [ ] **2.3** `tests/factories/user_mothers.py` — Effort: Low `[PARALLEL]`
  - `UserMothers`: `active()`, `anonymized()`, `with_profile()`
  - **Depends on:** `src/modules/user/domain/entities.py`

- [ ] **2.4** `tests/factories/storage_mothers.py` — Effort: Low `[PARALLEL]`
  - `StorageFileMothers`: `pending()`, `active()`, `deleted()`
  - **Depends on:** `src/modules/storage/domain/entities.py`

- [ ] **2.5** `tests/factories/builders.py` — Effort: Medium `[PARALLEL]`
  - `RoleBuilder`: fluent builder for Role with `with_name()`, `as_system_role()`, `with_permissions()`, `build()`
  - `SessionBuilder`: fluent builder for Session with `with_identity()`, `expired_at()`, `revoked()`, `build()`
  - `CategoryBuilder`: fluent builder for nested Category trees
  - **Depends on:** domain entities only (no infrastructure imports)

- [ ] **2.6** `tests/factories/orm_factories.py` — Effort: Medium `[PARALLEL]`
  - `IdentityModelFactory` (polyfactory `SQLAlchemyFactory`)
  - `BrandModelFactory`
  - `CategoryModelFactory`
  - `UserModelFactory`
  - **Depends on:** `src/modules/*/infrastructure/models.py`

- [ ] **2.7** `tests/factories/schema_factories.py` — Effort: Low `[PARALLEL]`
  - `RegisterRequestFactory` (polyfactory `ModelFactory` for Pydantic)
  - `LoginRequestFactory`
  - `CreateBrandRequestFactory`
  - `CreateCategoryRequestFactory`
  - **Depends on:** `src/modules/*/presentation/schemas.py`

### Verification Gate

```bash
# Factories must be importable and produce valid domain objects
uv run python -c "
from tests.factories.identity_mothers import IdentityMothers, SessionMothers, RoleMothers
from tests.factories.catalog_mothers import BrandMothers, CategoryMothers
from tests.factories.user_mothers import UserMothers
from tests.factories.builders import RoleBuilder, SessionBuilder
print('All factories importable and valid')
"
# Existing tests must still pass (no regressions)
uv run pytest tests/ -v --tb=short -x
```

---

## Chunk 3: Architecture Boundary Tests & Domain Unit Tests

> **Effort:** High
> **Parallelism:** `[PARALLEL]` across modules — architecture tests (3a) and each module's unit tests (3b) touch completely different files

### Chunk 3a: Architecture Boundary Tests Enhancement

- [ ] **3a.1** Enhance `tests/architecture/test_boundaries.py` — Effort: Medium `[PARALLEL]`
  - Add parameterized `test_domain_has_zero_framework_imports` for all 4 modules (spec Rule 2)
  - Add parameterized `test_module_isolation` with all cross-module pairs (spec Rule 5)
  - Add `test_no_reverse_layer_dependencies` for all modules (spec Rule 7)
  - Preserve existing rules (don't break the 9 passing tests)
  - Add `exclude()` clauses with comments for allowed exceptions (`user.presentation → identity.presentation`, `catalog.application.queries.get_category_tree`)
  - **File:** `tests/architecture/test_boundaries.py`

### Chunk 3b: Domain Unit Tests (per module)

> All unit tests: synchronous `def test_*`, zero I/O, use Object Mothers from Chunk 2

- [ ] **3b.1** Identity domain unit tests — Effort: Medium `[PARALLEL]`
  - **Existing:** 13 tests in `test_entities.py`, 8 in `test_value_objects.py` — refactor to use `IdentityMothers`
  - **New tests to add:**
    - `test_entities.py`: `TestIdentity.test_register_oidc_type`, `TestSession.test_ensure_valid_passes_when_fresh`, tests for `LinkedAccount` edge cases
    - `test_events.py`: Verify event field population for `IdentityRegisteredEvent`, `IdentityDeactivatedEvent`, `RoleAssignmentChangedEvent`
    - `test_value_objects.py`: `TestPermissionCode` — validate formatting, invalid inputs
  - **Files:** `tests/unit/modules/identity/domain/test_entities.py`, `test_events.py`, `test_value_objects.py`

- [ ] **3b.2** Catalog domain unit tests — Effort: Medium `[PARALLEL]`
  - **Existing:** 11 tests in `test_entities.py` — refactor to use `CatalogMothers`
  - **New tests to add:**
    - `test_entities.py`: Full Brand FSM coverage (every state transition + invalid transitions), Category depth enforcement, `create_child` slug generation
    - `test_events.py`: Verify `BrandCreatedEvent`, `BrandLogoConfirmedEvent`, `BrandLogoProcessedEvent` field population
    - `test_value_objects.py`: `TestMediaProcessingStatus` enum membership
  - **Files:** `tests/unit/modules/catalog/domain/test_entities.py`, `test_events.py`, `test_value_objects.py`

- [ ] **3b.3** User domain unit tests — Effort: Low `[PARALLEL]`
  - **Existing:** 6 tests in `test_entities.py` — refactor to use `UserMothers`
  - **New tests to add:**
    - `test_entities.py`: `TestUser.test_anonymize_replaces_all_pii`, `test_update_profile_partial_fields`, `test_create_from_identity_uses_shared_pk`
  - **Files:** `tests/unit/modules/user/domain/test_entities.py`

- [ ] **3b.4** Storage domain unit tests — Effort: Low `[PARALLEL]`
  - **New file:** `tests/unit/modules/storage/domain/test_entities.py`
  - Tests: `TestStorageFile.test_create_sets_fields`, `test_create_with_owner_module`
  - Create directory structure: `tests/unit/modules/storage/domain/`
  - **Files:** new `test_entities.py`

### Verification Gate

```bash
# Architecture tests — HARD BLOCK if any fail
uv run pytest tests/architecture/ -v --tb=short -x

# Unit tests — all modules
uv run pytest tests/unit/ -v --tb=short

# Combined: must show zero failures
uv run pytest tests/architecture/ tests/unit/ -v --tb=short --co | head -50  # dry-run to verify collection
uv run pytest tests/architecture/ tests/unit/ -v --tb=short -x
```

---

## Chunk 4: CQRS Integration Tests (Application + Infrastructure)

> **Effort:** High
> **Files touched:** 12+ new/modified test files across modules
> **Parallelism:** `[PARALLEL]` across modules — each module's integration tests are in separate directories and interact with independent DB tables

### Prerequisites
- Chunk 1 complete (hardened `db_session` with `join_transaction_mode`)
- Chunk 2 complete (factories available for data setup)
- Chunk 3 complete (domain logic verified independently)
- Docker containers running (`docker compose up -d`)

### Chunk 4a: Identity Module Integration Tests

- [ ] **4a.1** `tests/integration/modules/identity/infrastructure/repositories/test_identity_repo.py` — Effort: Medium `[PARALLEL]`
  - `test_add_identity_persists_to_db`
  - `test_get_identity_returns_domain_entity`
  - `test_get_by_email_returns_identity_with_credentials`
  - `test_email_exists_returns_true_for_existing`
  - `test_email_exists_returns_false_for_missing`
  - Pattern: `app_container() → get(IdentityRepository)` via Dishka, assert via `db_session`
  - **File:** new

- [ ] **4a.2** `tests/integration/modules/identity/infrastructure/repositories/test_session_repo.py` — Effort: Medium `[PARALLEL]`
  - `test_add_session_persists_with_hashed_token`
  - `test_get_by_refresh_token_hash_returns_session`
  - `test_revoke_all_for_identity`
  - `test_count_active_sessions`
  - `test_add_session_roles_persists_junction`
  - **File:** new

- [ ] **4a.3** `tests/integration/modules/identity/infrastructure/repositories/test_role_repo.py` — Effort: Medium `[PARALLEL]`
  - `test_add_role_persists`
  - `test_get_by_name_returns_role`
  - `test_assign_to_identity_creates_junction`
  - `test_get_identity_role_ids_returns_assigned`
  - `test_delete_role_cascades`
  - **File:** new

- [ ] **4a.4** `tests/integration/modules/identity/application/commands/test_register.py` — Effort: High `[PARALLEL]`
  - `test_register_creates_identity_and_credentials`
  - `test_register_hashes_password_with_argon2`
  - `test_register_emits_identity_registered_event_to_outbox`
  - `test_register_assigns_default_customer_role`
  - `test_register_raises_conflict_on_duplicate_email`
  - Pattern: `app_container() → get(RegisterHandler) → handler.handle(command)`, assert DB + Outbox
  - **File:** new

- [ ] **4a.5** `tests/integration/modules/identity/application/commands/test_login.py` — Effort: High `[PARALLEL]`
  - `test_login_returns_tokens_for_valid_credentials`
  - `test_login_creates_session_in_db`
  - `test_login_raises_invalid_credentials_for_wrong_password`
  - `test_login_raises_invalid_credentials_for_nonexistent_email`
  - `test_login_raises_when_identity_deactivated`
  - **File:** new

- [ ] **4a.6** `tests/integration/modules/identity/application/commands/test_login_oidc.py` — Effort: High `[PARALLEL]`
  - `test_login_oidc_creates_new_identity_and_linked_account`
  - `test_login_oidc_returns_existing_identity_for_known_provider`
  - `test_login_oidc_raises_when_identity_deactivated`
  - `test_login_oidc_emits_identity_registered_event_for_new_identity`
  - Requires: `StubOIDCProvider` from `tests/fakes/` (Chunk 1.4)
  - **File:** new

### Chunk 4b: Catalog Module Integration Tests (Enhance Existing)

- [ ] **4b.1** Enhance existing catalog integration tests — Effort: Low `[PARALLEL]`
  - Refactor `test_create_brand.py` to use `CatalogMothers` and `InMemoryBlobStorage`
  - Refactor `test_confirm_brand_logo.py` similarly
  - Verify Outbox event assertions follow spec patterns
  - **Files:** existing files in `tests/integration/modules/catalog/`

### Chunk 4c: User Module Integration Tests

- [ ] **4c.1** `tests/integration/modules/user/infrastructure/repositories/test_user_repo.py` — Effort: Medium `[PARALLEL]`
  - `test_add_user_persists_to_db`
  - `test_get_user_returns_domain_entity`
  - `test_update_user_modifies_fields`
  - **File:** new

- [ ] **4c.2** `tests/integration/modules/user/application/commands/test_create_user.py` — Effort: Medium `[PARALLEL]`
  - `test_create_user_from_identity_event`
  - `test_create_user_sets_shared_pk`
  - **File:** new

- [ ] **4c.3** `tests/integration/modules/user/application/commands/test_update_profile.py` — Effort: Low `[PARALLEL]`
  - `test_update_profile_modifies_allowed_fields`
  - `test_update_profile_raises_for_nonexistent_user`
  - **File:** new

### Verification Gate

```bash
# Integration tests — sequential execution, real database
uv run pytest tests/integration/ -v --tb=short -x

# Full regression — architecture + unit + integration
uv run pytest tests/architecture/ tests/unit/ tests/integration/ -v --tb=short -x
```

---

## Chunk 5: E2E Tests & Load Testing Setup

> **Effort:** Medium
> **Parallelism:** `[PARALLEL]` across test files — each e2e test file targets independent API routes

### Prerequisites
- Chunks 1-4 complete (full stack working)
- Docker containers running

### Chunk 5a: E2E Tests

- [ ] **5a.1** `tests/e2e/api/v1/test_auth.py` — Effort: High `[PARALLEL]`
  - `test_register_returns_201_with_identity_id`
  - `test_register_returns_409_when_email_exists`
  - `test_register_returns_422_for_invalid_email`
  - `test_login_returns_200_with_tokens`
  - `test_login_returns_401_for_wrong_password`
  - `test_refresh_token_returns_new_token_pair`
  - `test_logout_returns_204`
  - `test_logout_invalidates_refresh_token`
  - **File:** new

- [ ] **5a.2** `tests/e2e/api/v1/test_users.py` — Effort: Medium `[PARALLEL]`
  - `test_get_my_profile_returns_200_with_profile`
  - `test_get_my_profile_returns_401_without_token`
  - `test_update_profile_returns_200`
  - `test_update_profile_returns_401_without_token`
  - Requires: helper to create authenticated user + obtain JWT for test requests
  - **File:** new

- [ ] **5a.3** Enhance `tests/e2e/api/v1/test_brands.py` — Effort: Low `[PARALLEL]`
  - Add: `test_create_brand_returns_422_for_missing_name`
  - Add: `test_create_brand_returns_409_for_duplicate_slug`
  - **File:** existing, append tests

- [ ] **5a.4** Enhance `tests/e2e/api/v1/test_categories.py` — Effort: Low `[PARALLEL]`
  - Add: `test_create_category_returns_422_for_invalid_depth`
  - Add: `test_get_category_tree_returns_200`
  - **File:** existing, append tests

- [ ] **5a.5** Create e2e test helper for authenticated requests — Effort: Medium `[SEQUENTIAL before 5a.1-5a.4]`
  - Add to `tests/e2e/conftest.py`: `authenticated_client` fixture that registers a user, logs in, and returns an `AsyncClient` with `Authorization: Bearer {token}` header
  - **File:** `tests/e2e/conftest.py`

### Chunk 5b: Load Testing Setup

- [ ] **5b.1** `tests/load/thresholds.yml` — Effort: Low `[PARALLEL]`
  - Define SLA thresholds per scenario (auth_flow, catalog_browse, connection_pool_saturation)
  - **File:** new

- [ ] **5b.2** `tests/load/scenarios/auth_flow.py` — Effort: Medium `[PARALLEL]`
  - Locust `HttpUser` with `register → login → refresh → logout` task sequence
  - **File:** new

- [ ] **5b.3** `tests/load/scenarios/mixed_workload.py` — Effort: Medium `[PARALLEL]`
  - Locust `HttpUser` with weighted tasks: 80% reads (category tree, product search), 20% writes (register, create brand)
  - **File:** new

- [ ] **5b.4** Update `tests/load/locustfile.py` — Effort: Low `[PARALLEL]`
  - Import and register all scenarios
  - Configure `wait_time`, `host`, default user count
  - **File:** existing

### Verification Gate

```bash
# E2E tests
uv run pytest tests/e2e/ -v --tb=short -x

# FULL SUITE — the final quality gate
uv run ruff check --fix . && uv run ruff format .
uv run pytest tests/architecture/ -v -x
uv run pytest tests/unit/ -v --tb=short
uv run pytest tests/integration/ -v --tb=short
uv run pytest tests/e2e/ -v --tb=short

# Coverage gate
uv run pytest tests/unit/ tests/integration/ tests/e2e/ \
    --cov=src --cov-branch \
    --cov-fail-under=80 \
    --cov-report=term-missing
```

---

## Execution Summary

| Chunk | Name | Effort | Parallelism | Est. Tasks | Key Constraint |
|-------|------|--------|-------------|------------|----------------|
| **1** | Foundation | Critical | `SEQUENTIAL` | 6 tasks | Root fixtures — no concurrent edits |
| **2** | Data Generation | Medium | `PARALLEL` (7 subagents) | 7 tasks | Each module's mothers in separate file |
| **3a** | Architecture Tests | Medium | `PARALLEL` with 3b | 1 task | Single file, no deps on factories |
| **3b** | Unit Tests | High | `PARALLEL` (4 subagents) | 4 tasks | One subagent per module |
| **4** | Integration Tests | High | `PARALLEL` (3 module groups) | 10 tasks | Needs Docker containers + Chunk 1 fixtures |
| **5a** | E2E Tests | Medium | `PARALLEL` (after 5a.5) | 5 tasks | Auth helper must be built first |
| **5b** | Load Tests | Low | `PARALLEL` | 4 tasks | Separate runner, no pytest deps |

### Maximum Parallelism Points

| Phase | Max Concurrent Subagents | Files at risk of conflict |
|-------|--------------------------|---------------------------|
| Chunk 2 | **7** | None (all new files in `tests/factories/`) |
| Chunk 3 | **5** (1 arch + 4 unit modules) | None (separate directories per module) |
| Chunk 4 | **10** (all tasks independent) | None (separate directories per module) |
| Chunk 5a | **4** (after helper is built) | `tests/e2e/conftest.py` must be done first |

### Files That MUST NOT Be Edited Concurrently

These files are singletons that multiple subagents depend on. Only ONE agent may edit them, and always in the `SEQUENTIAL` phase:

| File | Edited in | Reason |
|------|-----------|--------|
| `tests/conftest.py` | Chunk 1 only | Root fixture DAG — all tests depend on it |
| `tests/e2e/conftest.py` | Chunk 5a.5 only | E2E fixture DAG — all e2e tests depend on it |
| `tests/integration/conftest.py` | Chunk 1 only (if changes needed) | Integration fixture DAG |
| `pyproject.toml` | Chunk 1 only | Global pytest configuration |
| `tests/architecture/test_boundaries.py` | Chunk 3a only | Single architecture test file |

### Subagent Worktree Isolation Rules

Per CLAUDE.md Section 2:
- All `[PARALLEL]` tasks MUST use `isolation: "worktree"`
- Each subagent creates files in its own worktree branch
- Merge order: Chunk N fully merged before Chunk N+1 starts
- Conflict resolution: if two subagents accidentally touch the same file, the later merge is rebased manually
