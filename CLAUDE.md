# Enterprise API — Claude Code Configuration

E-commerce async REST API built with FastAPI, following DDD / Clean Architecture / CQRS / Modular Monolith patterns.

**Stack:** Python 3.14 · FastAPI · SQLAlchemy 2.1 (async) · Alembic · Dishka DI ·
TaskIQ · RabbitMQ · Redis · MinIO/S3 · PostgreSQL · structlog · Pydantic v2 · uv · Ruff · mypy (strict)

**Bounded contexts:** `catalog` · `identity` · `user` · `storage`

---

## 1. 🤖 Agent Pipeline — HOW TO START ANY WORK

Every task, feature, or change **must** start with `@senior-pm`. No exceptions.

### Agents

| Agent | Model | Responsibility |
|---|---|---|
| `@senior-pm` | opus | Researches via Context7, breaks task into micro-tasks, writes TodoWrite list, runs loop |
| `@senior-architect` | opus | Writes implementation plan per micro-task (no code) |
| `@senior-backend` | opus | Implements the plan layer by layer, runs ruff/mypy/pytest |
| `@senior-reviewer` | opus | Audits + fixes all violations, signs off |
| `@senior-qa` | sonnet | Writes and runs unit/arch/integration/e2e test suite |

### Pipeline Loop

```
User describes task
       │
       ▼
  @senior-pm
  ├── Context7 research (mandatory)
  ├── Decompose into micro-tasks
  ├── TodoWrite([MT-1..N] × 4 agents)    ← loop's exit condition
  └── Start loop ───────────────────────────────────────────┐
                                                            │
  ┌─────────────── FOR EACH MICRO-TASK ───────────────┐     │
  │                                                   │     │
  │  @senior-architect  →  plan                       │     │
  │         │                                         │     │
  │  @senior-backend    →  implement                  │     │
  │         │                                         │     │
  │  @senior-reviewer   →  fix + approve              │     │
  │         │              └─ BLOCKED → back to BE    │     │
  │  @senior-qa         →  test + approve             │     │
  │         │              └─ BLOCKED → back to BE    │     │
  │         │                                         │     │
  │  Mark all 4 todos COMPLETED → next micro-task     │     │
  └───────────────────────────────────────────────────┘     │
                                                            │
  EXIT when TodoRead shows 0 PENDING ◄──────────────────────┘
```

### How to invoke

```
# Start a new feature:
@senior-pm Нужно добавить поддержку Product в модуль catalog

# Check progress:
@senior-pm покажи статус задач

# Resume after interruption:
@senior-pm продолжи с последней незавершённой задачи
```

---

## 2. 📋 Development Lifecycle

Every implementation chunk follows this strict sequence:

```
Plan → Brainstorm → Implement (subagent-driven) → Review → Update CLAUDE.md
```

| Phase | Tool / Agent | Trigger |
|---|---|---|
| **Plan** | `@senior-pm` + `superpowers:writing-plans` | Any multi-step task (≥3 files or ≥2 layers) |
| **Brainstorm** | `superpowers:brainstorming` | New features, components, architectural decisions |
| **Implement** | `@senior-backend` via pipeline | When architect's plan exists |
| **Parallel tasks** | `superpowers:subagent-driven-development` | 2+ independent tasks with no shared state |
| **Review** | `@senior-reviewer` + `superpowers:requesting-code-review` | After every implementation |
| **Update context** | `claude-md-management:revise-claude-md` | After each completed chunk |

**Plans live in** `docs/superpowers/plans/YYYY-MM-DD-<feature>.md` — not in conversation (survives compaction).

**Subagent parallelism** — within a single micro-task these can run in parallel:
- Domain layer (step 1) + Application layer (step 2): no shared state, safe to parallelize
- Unit tests (after step 2) + Integration tests (after step 3): independent suites

**Subagents MUST use** `isolation: "worktree"` when editing files to prevent conflicts.

---

## 3. 🔍 Context7 — Dynamic Knowledge Retrieval

**Query Context7 BEFORE writing code when:**

- Integrating or updating any external library: SQLAlchemy, FastAPI, Dishka, TaskIQ, Pydantic, Alembic, pytest, attrs, structlog, PyJWT, pwdlib, aiobotocore
- Implementing a pattern not used in this codebase before
- Writing infrastructure-layer code that depends on library-specific APIs
- Debugging a library-related error

**Workflow:**
1. `resolve-library-id` — find the Context7-compatible library ID
2. `query-docs` — retrieve up-to-date docs with a specific query
   - e.g. `"SQLAlchemy async session factory pattern"`, `"Dishka provider scope lifecycle"`
3. Apply retrieved patterns — **never rely on memorized APIs that may be outdated**

**Do NOT query Context7 for:**
- Pure domain logic (entities, value objects, events) — zero library imports
- Project-internal patterns already documented in this CLAUDE.md

---

## 4. ✅ Quality Gates — Mandatory Before Every Commit

All of the following must pass before `git commit`:

```bash
uv run ruff check --fix .             # 1. Lint + format
uv run ruff format .
uv run mypy .                         # 2. Type check (modified modules minimum)
uv run pytest tests/unit/ -v          # 3. Unit tests (no skips on modified modules)
uv run pytest tests/architecture/ -v  # 4. Architecture tests (violations = hard block)
```

Then invoke `@senior-reviewer` or `superpowers:requesting-code-review`.

**Code review checklist:**

- [ ] Clean Architecture: no infrastructure imports in domain/application layers
- [ ] Cross-module boundaries: no direct imports between modules (only `user.presentation → identity.presentation` allowed)
- [ ] Domain entity purity: `attrs` only, no SQLAlchemy/Pydantic in domain
- [ ] UoW discipline: all writes through `IUnitOfWork`, aggregates registered before commit
- [ ] Data Mapper: ORM models never leak into domain; repositories map between layers
- [ ] Security: no hardcoded secrets, proper input validation at presentation layer
- [ ] CQRS: commands mutate state + return None/ID; queries are read-only + return DTOs
- [ ] Type coverage: all new public functions and methods have full annotations

**Review severity:**
- 🔴 **CRITICAL** (must fix): Security vulnerabilities, architecture violations, data corruption risk
- 🟠 **MAJOR** (must fix): Missing error handling, CQRS violations, missing UoW registration
- 🟡 **MINOR** (fix if quick): Naming, missing docstrings, suboptimal queries

---

## 5. 🏗️ Architecture Rules

### Layer dependency (arrows = allowed import direction)

```
Presentation → Application → Domain ← Infrastructure
```

### Invariants — enforced by `@senior-reviewer` and `tests/architecture/`

1. **Domain purity** — entities never import SQLAlchemy, FastAPI, Pydantic, Redis, or any infra library
2. **No cross-module imports** — modules communicate only via domain events through the transactional outbox
3. **CQRS** — `CommandHandler` (write, returns None/ID) and `QueryHandler` (read, returns DTO) are always separate classes
4. **Unit of Work** — all writes go through `IUnitOfWork.commit()` — never `session.commit()` directly
5. **Data Mapper** — repositories translate between `attrs` domain entities and SQLAlchemy ORM models; ORM models never appear in domain or application layers
6. **Dependency injection** — constructor injection via Dishka; no `container.resolve()` in business logic
7. **One aggregate per transaction** — never modify two aggregate roots in a single UoW commit
8. **Events before commit** — domain events raised inside domain methods, persisted in outbox atomically

### Implementation order within a module (always follow this sequence)

1. **Domain** — entities, value objects, events, exceptions, repository interfaces
2. **Application** — command/query DTOs and handlers (imports only from domain + shared)
3. **Infrastructure** — ORM models, repository implementations, Dishka providers
4. **Presentation** — Pydantic schemas, FastAPI routers, DI dependencies
5. **Bootstrap** — register providers in `container.py`, mount routers in `web.py`
6. **Tests** — unit (domain + application), integration (repositories), e2e (API), architecture (boundaries)

---

## 6. 🧪 Testing

### Test categories

| Marker | Scope | Speed | Infrastructure |
|---|---|---|---|
| `unit` | Domain + application logic | ~6 s | None |
| `architecture` | Import boundary enforcement | ~1 s | None |
| `integration` | Real DB + Redis + RabbitMQ | ~30 s | testcontainers |
| `e2e` | Full HTTP round-trips | ~15 s | testcontainers |

### Commands

```bash
# Fast — always run first (no Docker needed)
uv run pytest tests/unit/ tests/architecture/ -v

# Full suite
uv run pytest tests/ -v

# With coverage (must not decrease from 88% baseline)
uv run pytest tests/ --cov=src --cov-report=term-missing
```

### Architecture fitness tests enforce at CI time

- Domain layer has zero infrastructure imports
- Application layer imports only from domain
- No direct cross-module imports
- ORM models never appear in domain or application layers

```bash
uv run pytest tests/architecture/ -v
```

---

## 7. 🔧 Dev Commands

```bash
uv run ruff check --fix .                          # lint
uv run ruff format .                               # format
uv run mypy .                                      # type check
uv run alembic revision --autogenerate -m "desc"   # create migration
uv run alembic upgrade head                        # apply migrations
docker compose up -d                               # start infrastructure
uv run uvicorn src.bootstrap.web:create_app --factory --reload --host 0.0.0.0 --port 8000
```

---

## 8. 🔌 Hooks — Automation Opportunities

Project-specific hooks to implement via `plugin-dev:*` skills:

- `PostToolUse` on `Write|Edit` → run `ruff check` on the modified file
- `PreToolUse` on `Bash(git commit*)` → verify lint + type check + tests pass
- Architecture boundary validation → prevent cross-module imports at edit time

---

## 9. 🧠 Context Window Protection

- Store all persistent rules here in CLAUDE.md — conversation context is ephemeral
- Use `/compact` proactively when working on large chunks (>20 file operations)
- Delegate research and exploration to subagents — keeps main context clean
- Use `superpowers:subagent-driven-development` for parallel work instead of sequential exploration
- Track context usage via `/context` command when sessions run long
- Plans live in `docs/superpowers/plans/` — they survive compaction; conversation history does not
- After compaction, all critical decisions must be captured here, not in conversation history

---

## 10. 📁 Project Structure

```
src/
├── api/                          # HTTP layer — routers, middleware, exceptions
├── bootstrap/                    # Composition root — DI container, app factory, config
├── infrastructure/               # DB, cache, outbox, security, storage, logging
├── modules/
│   ├── catalog/                  # Brands, categories, products
│   ├── identity/                 # Auth, sessions, roles, permissions
│   ├── user/                     # User profiles
│   └── storage/                  # File management, media processing
└── shared/                       # Base exceptions, schemas, cross-module interfaces

.claude/
└── agents/
    ├── senior-pm.md              # opus  — task decomposition + loop orchestration
    ├── senior-architect.md       # opus  — implementation planning
    ├── senior-backend.md         # sonnet — code implementation
    ├── senior-reviewer.md        # opus  — code audit + fixes
    └── senior-qa.md              # sonnet — test suite

docs/
└── superpowers/
    └── plans/                    # YYYY-MM-DD-<feature>.md — persistent plans
```
