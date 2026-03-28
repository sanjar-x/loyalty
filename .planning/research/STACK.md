# Stack Research: EAV Catalog Hardening — Testing & Validation Tooling

**Domain:** Testing, validation, and quality assurance for Python/FastAPI/SQLAlchemy EAV catalog system
**Researched:** 2026-03-28
**Confidence:** HIGH

## Context

The existing production stack (Python 3.14, FastAPI, SQLAlchemy 2.1 async, PostgreSQL 18, Dishka DI) is already decided and deployed. This research focuses exclusively on **testing, validation, and quality assurance tooling** needed to harden the EAV Catalog module — not the application stack itself.

The codebase already has a pytest-based test infrastructure (pytest 9.x, pytest-asyncio 1.3+, testcontainers, polyfactory, pytest-archon) with well-designed fixtures for DB isolation (nested transaction rollback), DI container overrides, and Redis cleanup. The gap is coverage: 44 of 46 catalog command handlers are untested, and the test-to-source ratio for catalog is 1.1%.

---

## Recommended Stack

### Core Testing Framework (Already in Place)

These are **already installed and configured** — do not change them. Listed for completeness.

| Technology | Version | Purpose | Status |
|------------|---------|---------|--------|
| pytest | >=9.0.2 | Test runner, assertion engine, fixture system | Installed |
| pytest-asyncio | >=1.3.0 | Async test auto-detection (mode: auto) | Installed |
| pytest-cov | >=7.0.0 | Coverage collection (--cov=src) | Installed |
| pytest-archon | >=0.0.7 | Architecture fitness functions (import boundary tests) | Installed |
| polyfactory | >=3.3.0 | SQLAlchemy ORM model factories, Pydantic schema factories | Installed |
| testcontainers | >=4.14.1 | Docker-based PostgreSQL/Redis/RabbitMQ for integration tests | Installed |
| Locust | >=2.43.3 | Load/performance testing scenarios | Installed |
| mypy | >=1.19.1 | Static type checking (strict mode, pydantic plugin) | Installed |
| Ruff | latest | Linting + formatting (py314 target) | Installed |

**Confidence:** HIGH — versions verified against `backend/pyproject.toml` and `backend/pytest.ini`.

### New: Validation & Contract Testing

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| hypothesis | >=6.151.5 | Property-based testing for EAV domain invariants | Has built-in attrs strategy inference via `builds()` and `from_type()`. Finds edge cases in attribute value combinations, category tree invariants, and SKU matrix generation that example-based tests miss. The EAV pattern has a combinatorial explosion of valid/invalid states that property-based testing was designed for. |
| schemathesis | >=4.13.0 | API contract testing from OpenAPI schema | FastAPI auto-generates OpenAPI specs. Schemathesis fuzzes every endpoint against that spec, catching response schema violations, 500 errors, and edge cases in catalog CRUD. Uses Hypothesis internally. |
| dirty-equals | >=0.11 | Declarative assertion helpers for API response testing | Makes assertions like `assert response_data == {"id": IsUUID(), "name": "Nike", "created_at": IsDatetime()}` readable. Built by the Pydantic author (Samuel Colvin), designed specifically for API response testing. |

**Confidence:** HIGH — all three verified on PyPI with recent 2025/2026 releases. Hypothesis and Schemathesis are the de facto standard for property-based and contract testing in the Python ecosystem.

### New: HTTP Mocking

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| respx | >=0.22.0 | Mock httpx requests to image backend service | The catalog module calls the image backend via httpx (`ImageBackendClient`). respx is the standard httpx mock library — provides pytest fixtures, pattern matching, and response side effects. Version 0.22.0 confirmed compatible with httpx 0.28+. |

**Confidence:** HIGH — respx is the canonical httpx mocking library. No real alternatives exist for httpx-specific mocking.

### New: Test Quality & Reliability

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| pytest-randomly | >=3.16.0 | Randomize test execution order | Detects hidden inter-test dependencies (test A passes only because test B runs first). Prints seed for reproducibility. Critical when scaling from ~20 to hundreds of catalog tests. |
| pytest-timeout | >=2.4.0 | Abort hanging async tests | Async tests with real DB can hang on deadlocks or connection pool exhaustion. Default 30s timeout catches these early instead of blocking CI indefinitely. |

**Confidence:** HIGH — both are mature, widely-used pytest plugins with active maintenance.

### New: Performance Validation

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| SQLAlchemy event listeners (built-in) | N/A (part of SQLAlchemy 2.1) | N+1 query detection via `after_execute` / `do_orm_execute` events | Build a lightweight `assert_query_count` context manager using SQLAlchemy's built-in event system. Works with async sessions. Better than `nplusone` (unmaintained, no async/SA 2.x support). |

**Confidence:** HIGH — uses SQLAlchemy's own documented event API. No external dependency needed.

### Development Tools (Already in Place, No Changes)

| Tool | Purpose | Notes |
|------|---------|-------|
| pytest (Makefile targets) | `make test-unit`, `make test-integration`, `make test-e2e` | Well-organized test pyramid commands |
| Docker Compose | PostgreSQL 18, Redis 8.4, RabbitMQ 4.2.4 for local tests | Already configured in `backend/docker-compose.yml` |
| Ruff | Linting test files (same config as source) | Already configured |

---

## Installation

```bash
# New testing dependencies — add to [dependency-groups] dev in backend/pyproject.toml
uv add --group dev "hypothesis>=6.151.5"
uv add --group dev "schemathesis>=4.13.0"
uv add --group dev "dirty-equals>=0.11"
uv add --group dev "respx>=0.22.0"
uv add --group dev "pytest-randomly>=3.16.0"
uv add --group dev "pytest-timeout>=2.4.0"
```

**pytest.ini additions:**

```ini
# Add to existing addopts:
addopts =
    -v
    --strict-markers
    --cov=src
    --cov-report=term-missing:skip-covered
    --cov-report=xml
    --timeout=30

# Add timeout default (30s per test — generous for integration tests with real DB)
timeout = 30
```

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| hypothesis | Only example-based tests | EAV systems have combinatorial state spaces (attributes x types x categories x variants). Example tests miss edge cases that property tests find automatically. |
| schemathesis | Manual endpoint testing | 44+ command handlers means dozens of API endpoints. Manual testing is incomplete and doesn't catch schema drift. Schemathesis auto-generates thousands of test cases from the OpenAPI spec. |
| dirty-equals | Raw dict comparison | API responses contain UUIDs, timestamps, and nested objects. `assert response == {...}` is brittle. dirty-equals makes assertions readable and maintainable. |
| respx | unittest.mock.patch on httpx | Patching internals is fragile. respx provides a purpose-built httpx mock with pattern matching, side effects, and a pytest fixture. |
| pytest-randomly | Fixed test order | Fixed ordering hides coupling between tests. Randomization surfaces it before it causes flaky CI. |
| SQLAlchemy events for N+1 | nplusone library | nplusone's last meaningful release was years ago. It does not support async SQLAlchemy or SQLAlchemy 2.x. Building a 20-line context manager on SQLAlchemy events is simpler and fully async-compatible. |
| pytest-timeout | No timeout | Async tests with real PostgreSQL can deadlock. Without timeout, CI hangs for 10+ minutes before failing. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| nplusone | Unmaintained, no async support, no SQLAlchemy 2.x support. Last significant update predates SA 2.0. | Custom `assert_query_count` context manager using SQLAlchemy `after_execute` event listener (20 lines of code). |
| factory_boy | Older factory library. Does not understand SQLAlchemy 2.x async sessions natively. Project already uses polyfactory which is newer, supports SA 2.x, and has built-in Pydantic integration. | polyfactory (already installed) + Object Mothers pattern (already in use). |
| pytest-flask-sqlalchemy | Flask-specific. This project uses FastAPI with Dishka DI, not Flask. | Existing `db_session` fixture with nested transaction rollback (already working). |
| pytest-sqlalchemy-mock | Uses in-memory SQLite instead of real PostgreSQL. Misses PostgreSQL-specific behaviors critical for EAV (JSONB, array types, recursive CTEs for category trees). | testcontainers with real PostgreSQL (already configured). |
| pytest-xdist (for now) | Parallel test execution adds complexity to DB isolation. The current test suite is small (~100 tests). Adding parallelism is premature — revisit when test count exceeds 500+. | Sequential execution with `pytest-timeout` to catch hangs. |
| pytest-sugar / pytest-clarity | Cosmetic output improvements. Add noise to CI logs and can conflict with `--cov-report=term-missing`. Not worth the dependency for a hardening milestone. | Default pytest verbose output (`-v`). |
| Faker (standalone) | General-purpose fake data. The project already has polyfactory for typed factories and Object Mothers for domain-specific construction. Adding Faker separately creates two data generation patterns. | polyfactory (has optional Faker integration if locale-specific data is ever needed). |

---

## Stack Patterns by Test Type

**Unit tests (domain entities, command handlers with mocked deps):**
- Use Object Mothers (`tests/factories/catalog_mothers.py`) for domain entities
- Use `unittest.mock.AsyncMock` for repository/UoW mocking (already established)
- Use `hypothesis` with `@given` + `builds()` for property-based invariant testing on attrs domain models
- Use `dirty-equals` for structured assertion matching

**Integration tests (repositories, handlers with real DB):**
- Use `db_session` fixture (nested transaction rollback) — already working
- Use `polyfactory` ORM factories for seeding test data
- Use `assert_query_count` context manager for N+1 detection
- Use `respx` to mock image backend HTTP calls

**E2E / API contract tests:**
- Use `httpx.AsyncClient` with `ASGITransport` — already working
- Use `schemathesis` for fuzz testing all catalog endpoints against OpenAPI schema
- Use `dirty-equals` for response payload assertions

**Property-based tests (EAV domain invariants):**
- Use `hypothesis` with custom strategies for:
  - Attribute value validation across types (string, number, boolean, select)
  - Category tree depth/hierarchy invariants
  - SKU matrix generation correctness
  - Product status FSM transitions
  - Slug generation uniqueness

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| hypothesis >=6.151.5 | Python 3.14, attrs >=25.4.0 | Built-in attrs introspection for `builds()` and `from_type()`. |
| schemathesis >=4.13.0 | FastAPI >=0.115.0, hypothesis >=6.x | Uses Hypothesis internally. Reads OpenAPI schema from FastAPI app. |
| dirty-equals >=0.11 | Python 3.8+, Pydantic v2 | Created by Pydantic author. Works with any assertion framework. |
| respx >=0.22.0 | httpx >=0.25.0 (project uses >=0.28.1) | Version 0.22.0 specifically fixed httpx 0.28 compatibility. |
| pytest-randomly >=3.16.0 | pytest >=9.0.2 | Drop-in plugin, no configuration needed beyond install. |
| pytest-timeout >=2.4.0 | pytest >=9.0.2, pytest-asyncio >=1.3.0 | Works with async tests. Supports `thread` and `signal` timeout methods. |
| polyfactory >=3.3.0 | SQLAlchemy >=2.1.0b1 | Already installed. SQLAlchemyFactory handles relationships, association proxies. |

---

## Custom Tooling to Build (Not External Libraries)

These are small utilities (10-30 lines each) to build inside the test suite rather than installing packages:

### 1. Query Count Assertion Context Manager

```python
# tests/helpers/query_counter.py
from contextlib import contextmanager
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

@contextmanager
def assert_query_count(session: AsyncSession, expected: int):
    """Assert that exactly `expected` SQL queries are executed within the block."""
    queries = []
    sync_conn = session.sync_session.bind

    def _record(conn, cursor, statement, parameters, context, executemany):
        queries.append(statement)

    event.listen(sync_conn, "after_cursor_execute", _record)
    try:
        yield queries
    finally:
        event.remove(sync_conn, "after_cursor_execute", _record)
    assert len(queries) == expected, (
        f"Expected {expected} queries, got {len(queries)}:\n"
        + "\n".join(f"  {i+1}. {q[:120]}" for i, q in enumerate(queries))
    )
```

### 2. Hypothesis Strategies for EAV Domain

```python
# tests/strategies/catalog_strategies.py
from hypothesis import strategies as st

# Attribute value strategies by type
eav_attribute_values = st.one_of(
    st.text(min_size=1, max_size=500),           # string attributes
    st.integers(min_value=0, max_value=999999),   # numeric attributes
    st.booleans(),                                 # boolean attributes
    st.floats(min_value=0, allow_nan=False, allow_infinity=False),  # decimal attributes
)

# i18n name strategy (required for categories, brands)
i18n_names = st.fixed_dictionaries({
    "en": st.text(min_size=1, max_size=100),
    "ru": st.text(min_size=1, max_size=100),
})

# Slug strategy (URL-safe strings)
slugs = st.from_regex(r"[a-z0-9][a-z0-9-]{2,48}[a-z0-9]", fullmatch=True)
```

---

## Sources

- [pytest PyPI](https://pypi.org/project/pytest/) — version 9.0.2 confirmed (HIGH confidence)
- [pytest-asyncio PyPI](https://pypi.org/project/pytest-asyncio/) — version 1.3.0 confirmed (HIGH confidence)
- [hypothesis PyPI](https://pypi.org/project/hypothesis/) — version 6.151.5+ confirmed (HIGH confidence)
- [hypothesis docs: attrs support](https://hypothesis.readthedocs.io/en/latest/data.html) — builds()/from_type() attrs introspection confirmed (HIGH confidence)
- [schemathesis PyPI](https://pypi.org/project/schemathesis/) — version 4.13.0 confirmed (HIGH confidence)
- [schemathesis + FastAPI guide](https://testdriven.io/blog/fastapi-hypothesis/) — integration pattern verified (MEDIUM confidence)
- [dirty-equals PyPI](https://pypi.org/project/dirty-equals/) — version 0.11 confirmed (HIGH confidence)
- [respx PyPI](https://pypi.org/project/respx/) — version 0.22.0, httpx 0.28 compat confirmed (HIGH confidence)
- [respx httpx 0.28 fix PR](https://github.com/lundberg/respx/pull/278) — compatibility verified (HIGH confidence)
- [pytest-randomly PyPI](https://pypi.org/project/pytest-randomly/) — active maintenance confirmed (HIGH confidence)
- [pytest-timeout PyPI](https://pypi.org/project/pytest-timeout/) — version 2.4.0 confirmed (HIGH confidence)
- [SQLAlchemy event docs](https://docs.sqlalchemy.org/en/21/orm/events.html) — after_cursor_execute for query counting (HIGH confidence)
- [nplusone GitHub](https://github.com/jmcarp/nplusone) — unmaintained, no SA 2.x/async support (HIGH confidence on "avoid" recommendation)
- [polyfactory docs: SQLAlchemy](https://polyfactory.litestar.dev/latest/usage/library_factories/sqlalchemy_factory.html) — SA 2.x support confirmed (HIGH confidence)
- [pytest-cov PyPI](https://pypi.org/project/pytest-cov/) — version 7.0.0 confirmed (HIGH confidence)
- [coverage.py docs](https://coverage.readthedocs.io/) — version 7.13.5, branch coverage supported (HIGH confidence)
- [Locust PyPI](https://pypi.org/project/locust/) — version 2.43.3 confirmed (HIGH confidence)

---

*Stack research for: EAV Catalog Hardening — Testing & Validation Tooling*
*Researched: 2026-03-28*
