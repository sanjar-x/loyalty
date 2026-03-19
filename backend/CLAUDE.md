# Enterprise API — Claude Code Configuration

E-commerce async REST API built with FastAPI, following DDD / Clean Architecture / CQRS / Modular Monolith patterns.

**Stack:** Python 3.14 · FastAPI · SQLAlchemy 2.1 (async) · Alembic · Dishka DI ·
TaskIQ · RabbitMQ · Redis · MinIO/S3 · PostgreSQL · structlog · Pydantic v2 · uv · Ruff · mypy (strict)

**Bounded contexts:** `catalog` · `identity` · `user` · `storage`

---

## 1. 🎯 Task Triage — CHOOSE THE RIGHT MODE

**BEFORE doing any work, classify the task into one of three modes.**
This is the most important decision — it determines cost, speed, and quality.

### Decision tree

```
User request arrives
       │
       ▼
  Is it a bug fix, typo, config change,
  or change to ≤2 files?
       │
   YES ▼                    NO ▼
  ┌─────────┐          Is it a new bounded context,
  │ HOTFIX  │          new module, or 5+ entities?
  └─────────┘               │
                      NO ▼           YES ▼
                    ┌──────┐      ┌─────────┐
                    │ TASK │      │ FEATURE │
                    └──────┘      └─────────┘
```

### Mode 1: `hotfix` — bug fix, typo, config, ≤2 files

**Agents: NONE.** Main agent does everything directly.

```
main agent → fix code → ruff/mypy/pytest → done
```

**When:** "исправь баг", "добавь поле", "поправь опечатку", "обнови конфиг",
"переименуй метод", "добавь docstring", any change touching 1-2 files.

**Rules:**
- Read the relevant code first
- Fix directly (no subagents)
- Run quality gates: `uv run ruff check --fix . && uv run ruff format . && uv run mypy . && uv run pytest tests/unit/ tests/architecture/ -v`
- If tests fail → fix → re-run

### Mode 2: `task` — concrete task, 3-10 files, single layer or cross-layer

**Agents: senior-backend + senior-qa** (2 opus calls per task)

```
main agent plans → senior-backend implements → senior-qa tests → done
```

**When:** "добавь query handler", "реализуй repository", "добавь новый endpoint",
"добавь command handler для X", any scoped task within an existing module.

**Rules:**
- Main agent writes a brief plan (which files, what changes, acceptance criteria)
- Dispatch `senior-backend` with the plan
- Dispatch `senior-qa` to write tests
- No architect (main agent plans), no reviewer (QA + linters catch issues)
- If QA blocks → re-dispatch senior-backend with fix instructions

### Mode 3: `feature` — new module, new bounded context, 5+ entities

**Full pipeline with optimizations:**

```
 PRD Phase (3 agents, not 5):
  1. context-analyst    → context-brief.json        Analyze topic + scan codebase
  2. prd-writer         → prd.md                    Write PRD (uses brief directly)
  3. review-qa          → qa-report.json            Validate PRD

 Implementation Phase:
  4. senior-pm          → pm-spec.md                Decompose into micro-tasks
  ┌──────── FOR EACH MICRO-TASK ────────┐
  │  IF complex (Infra/Presentation/Cross-cutting): │
  │    senior-architect → arch/MT-{N}-plan.md       │
  │    senior-backend   → code files                │
  │    senior-qa        → qa-tests/MT-{N}-qa.md     │
  │  IF simple (Domain/Application):                │
  │    senior-backend   → code files                │
  │    senior-qa        → qa-tests/MT-{N}-qa.md     │
  └─────────────────────────────────────────────────┘
```

**What's removed vs old pipeline:**
- `competitive-intel` — removed. For internal project, market research is not needed. Context-analyst scans the codebase directly.
- `gap-analysis` — removed. Main agent decides what to build based on the user's request and context brief.
- `senior-reviewer` — removed from loop. QA + ruff + mypy + pytest catch the same issues. Reviewer found 0 critical/0 major on 5 out of 6 reviewed MTs.

**MT merging rules (CRITICAL — reduces MT count by 60%):**
- All value objects + enums for one module → 1 MT
- All entities + exceptions for one aggregate → 1 MT
- All command handlers for one aggregate → 1 MT
- All query handlers for one module → 1 MT
- Repository interface + implementation + ORM model → 1 MT
- All Pydantic schemas + routers for one resource → 1 MT
- DI registration + bootstrap wiring → 1 MT

**Target: 6-10 MTs for a medium feature, not 23.**

**MT complexity classification (determines whether architect is needed):**

| MT Layer | Type | Flow | Opus calls |
|----------|------|------|------------|
| Domain (VOs, entities, events, exceptions, interfaces) | `simple` | backend → qa | 2 |
| Application (handlers, DTOs, read models) | `simple` | backend → qa | 2 |
| Infrastructure (ORM, repos, migrations) | `complex` | architect → backend → qa | 3 |
| Presentation (schemas, routers) | `complex` | architect → backend → qa | 3 |
| Cross-cutting (DI, bootstrap, config) | `complex` | architect → backend → qa | 3 |

**Simple MT:** main agent passes the pm-spec.md section directly to senior-backend. No architect needed — no DI, no migrations, no library APIs.

**Complex MT:** architect plans DI wiring, migration schema, Context7 research, router structure. Backend follows the plan.

### Agent roster

| Agent               | Model | Used in          | Role                     |
| ------------------- | ----- | ---------------- | ------------------------ |
| `context-analyst`   | opus  | feature          | Topic → structured brief |
| `competitive-intel` | opus  | on-demand only   | Market research (when explicitly requested) |
| `gap-analysis`      | opus  | on-demand only   | Decision matrix (when explicitly requested) |
| `prd-writer`        | opus  | feature          | Write PRD                |
| `review-qa`         | opus  | feature          | Validate PRD             |
| `senior-pm`         | opus  | feature          | Micro-task decomposition |
| `senior-architect`  | opus  | feature          | Architecture plan per MT |
| `senior-backend`    | opus  | feature, task    | Implement code           |
| `senior-reviewer`   | opus  | on-demand only   | Code review (when explicitly requested) |
| `senior-qa`         | opus  | feature, task    | Write and run tests      |

### Communication protocol

- **PRD agents:** communicate via JSON/MD files in `.claude/pipeline-runs/current/artifacts/`
- **MT agents:** save to subdirectories (`arch/`, `qa-tests/`)
- **Every agent's final message** ends with `═══ PIPELINE HANDOFF ═══` or `═══ MICRO-TASK HANDOFF ═══`
- **Follow the handoff block** — it contains exact paths and next commands

### Cost comparison

| Mode    | Opus calls | Use case                          |
| ------- | ---------- | --------------------------------- |
| hotfix  | 0          | Bug fix, typo, config, ≤2 files   |
| task    | 2          | Scoped task in existing module    |
| feature | 15-25      | New module / 5+ entities          |
| OLD     | 90-100     | Everything went through full pipe |

Feature breakdown (8 MTs, 4 simple + 4 complex):
- PRD phase: 3 calls (analyst + prd-writer + review-qa)
- PM: 1 call
- Simple MTs: 4 × 2 = 8 calls (backend + qa)
- Complex MTs: 4 × 3 = 12 calls (architect + backend + qa)
- Total: ~24 calls vs ~97 old pipeline = **75% savings**

---

## 2. 🚀 How to Run

### Hotfix / Task — just tell Claude

```
"Исправь баг в ProductRepository.get_by_id"     → hotfix mode, 0 agents
"Добавь endpoint для получения SKU по product"   → task mode, 2 agents
```

Main agent triages automatically based on Section 1 decision tree.

### Feature — start the pipeline

```bash
# Option A: Tell Claude directly
"Добавь модуль корзины (Cart) с товарами, промокодами и чекаутом"

# Option B: Initialize manually
bash .claude/hooks/pipeline-state.sh init "Cart module — items, promo codes, checkout"
# Then: Use the context-analyst subagent on this topic.
```

### Resume after interruption

```bash
bash .claude/hooks/pipeline-state.sh resume
```

Scans artifacts on disk (including `arch/`, `review/`, `qa-tests/`), reconciles state, finds the resume point — whether in PRD phase or mid-MT-loop.

### Check progress

```bash
bash .claude/hooks/pipeline-state.sh status      # Full pipeline status
bash .claude/hooks/pipeline-state.sh mt-status    # Micro-task progress table
bash .claude/hooks/pipeline-state.sh next         # Show next action (PRD or MT)
```

### Pipeline artifacts location

```
.claude/pipeline-runs/current/artifacts/
├── context-brief.json          # Agent 1
├── competitive-report.json     # Agent 2
├── enhancement-plan.json       # Agent 3
├── prd.md                      # Agent 4
├── qa-report.json              # Agent 5
├── pm-spec.md                  # Agent 6
├── arch/                       # Agent 7 (per MT)
│   ├── MT-1-plan.md
│   ├── MT-2-plan.md
│   └── ...
├── review/                     # Agent 9 (per MT)
│   ├── MT-1-review.md
│   └── ...
└── qa-tests/                   # Agent 10 (per MT)
    ├── MT-1-qa.md
    └── ...
```

Previous runs archived in `.claude/pipeline-runs/archive/{run_id}/`.

---

## 3. 🔄 Micro-Task Implementation Loop (feature mode)

After senior-pm produces pm-spec.md:

```bash
bash .claude/hooks/pipeline-state.sh init-mt <total_mt_count>
```

```
For each MT-N (in order):

  1. Read pm-spec.md overview table. Group MTs into waves by dependency:
     - Wave = set of MTs whose dependencies are ALL completed
     - MTs in the same wave can run IN PARALLEL

  2. For each wave, launch all MTs concurrently (multiple Agent calls in one message):

     Per MT-{N}:
       a. Check Layer field in pm-spec.md
       b. IF simple (Domain/Application):
            → senior-backend directly (reads pm-spec.md)
       c. IF complex (Infra/Presentation/Cross-cutting):
            → senior-architect first, THEN senior-backend
       d. After backend → senior-qa
       e. If QA blocks → re-run senior-backend with fix instructions

  3. Wait for all MTs in the wave to complete, then start next wave.

EXIT: All waves completed → pipeline DONE

EXAMPLE (Products module, 7 MTs):
  Wave 1: MT-1 (domain VOs)                          ← 1 MT
  Wave 2: MT-2 (entities), MT-3 (exceptions)          ← 2 MTs parallel
  Wave 3: MT-4 (handlers), MT-5 (queries)             ← 2 MTs parallel
  Wave 4: MT-6 (repos+ORM+migration)                  ← 1 MT
  Wave 5: MT-7 (schemas+routers+DI)                   ← 1 MT
  Total: 5 sequential waves instead of 7 sequential MTs
```

**On-demand agents** (not in default loop, use when explicitly requested):
- `senior-reviewer` — "запусти code review для MT-{N}"
- `competitive-intel` — "исследуй как лидеры рынка делают X"
- `gap-analysis` — "сравни наш подход с лучшими практиками"

**Critical:** subagents cannot call other subagents. The main agent orchestrates the loop.

### Micro-task state tracking

```bash
bash .claude/hooks/pipeline-state.sh mt-status        # Progress table for all MTs
bash .claude/hooks/pipeline-state.sh resume-mt         # Show next MT action
bash .claude/hooks/pipeline-state.sh start-mt 3 senior-architect   # Mark agent started
bash .claude/hooks/pipeline-state.sh complete-mt 3 senior-architect # Mark agent done
bash .claude/hooks/pipeline-state.sh block-mt 3 senior-qa          # Block → backend fix
```

---

## 4. 🔍 Context7 — Dynamic Knowledge Retrieval

**Query Context7 BEFORE writing code when:**

- Integrating or updating any external library
- Implementing a pattern not used in this codebase before
- Writing infrastructure-layer code that depends on library-specific APIs
- Debugging a library-related error

**Workflow:**

```
resolve-library-id → query-docs
```

**Do NOT query Context7 for:**

- Pure domain logic (entities, value objects, events) — zero library imports
- Project-internal patterns already documented in this CLAUDE.md

**Agents that use Context7:** senior-pm (6), senior-architect (7), senior-backend (8), senior-reviewer (9), senior-qa (10)

---

## 5. ✅ Quality Gates — Mandatory Before Every Commit

```bash
uv run ruff check --fix .             # 1. Lint + auto-fix
uv run ruff format .                  # 2. Format
uv run mypy .                         # 3. Type check (strict)
uv run pytest tests/unit/ -v          # 4. Unit tests
uv run pytest tests/architecture/ -v  # 5. Architecture boundary tests
```

**Code review checklist (enforced by senior-reviewer):**

- [ ] Domain layer: zero framework imports (SQLAlchemy, FastAPI, Pydantic, Redis)
- [ ] No cross-module imports (events through outbox only)
- [ ] CQRS: command handlers (write, return None/ID) separate from query handlers (read, return DTOs)
- [ ] All writes through `IUnitOfWork.commit()` — never `session.commit()`
- [ ] Data Mapper: ORM models never leak into domain; repos map between layers
- [ ] Security: no hardcoded secrets, input validation at presentation layer
- [ ] Type coverage: all public functions fully annotated
- [ ] Google-style docstrings on all public classes/functions

**Severity:**

- 🔴 **Critical:** architecture violations, security, data corruption → must fix, blocks approval
- 🟠 **Major:** missing error handling, CQRS violations → must fix
- 🟡 **Minor:** naming, docstrings → fix if quick

---

## 6. 🏗️ Architecture Rules

### Layer dependency (arrows = allowed import direction)

```
Presentation → Application → Domain ← Infrastructure
```

### Non-negotiable invariants

1. **Domain purity** — entities use only `attrs`, `uuid`, `datetime`, `decimal`, stdlib
2. **No cross-module imports** — modules communicate via domain events through transactional outbox
3. **CQRS** — `CommandHandler` and `QueryHandler` are always separate classes
4. **Unit of Work** — all writes through `IUnitOfWork.commit()`
5. **Data Mapper** — repos translate between `attrs` entities and SQLAlchemy ORM models
6. **DI** — constructor injection via Dishka; no `container.resolve()` in business logic
7. **One aggregate per transaction** — never modify two aggregate roots in one UoW commit
8. **Events before commit** — domain events raised inside domain methods, persisted in outbox atomically
9. **Pydantic at boundaries only** — request/response schemas in `presentation/`, nowhere else

### Implementation order within a module

```
1. Domain       → entities, VOs, events, exceptions, repo interfaces
2. Application  → command/query DTOs, handlers (imports only domain + shared)
3. Infrastructure → ORM models, repo implementations, Dishka providers
4. Presentation → Pydantic schemas, FastAPI routers
5. Bootstrap    → register in container.py, mount routers
6. Tests        → unit, integration, e2e, architecture
```

---

## 7. 🧪 Testing

### Test categories

| Marker         | Scope                      | Speed | Infra          |
| -------------- | -------------------------- | ----- | -------------- |
| `unit`         | Domain + application       | ~6 s  | None           |
| `architecture` | Import boundaries          | ~1 s  | None           |
| `integration`  | Real DB + Redis + RabbitMQ | ~30 s | testcontainers |
| `e2e`          | Full HTTP round-trips      | ~15 s | testcontainers |

### Commands

```bash
uv run pytest tests/unit/ tests/architecture/ -v              # fast suite
uv run pytest tests/integration/ tests/e2e/ -v                # infra suite
uv run pytest tests/ --cov=src --cov-report=term-missing      # coverage (baseline: 88%)
```

### Test locations

```
tests/
├── unit/modules/{module}/domain/      ← entities, VOs, events
├── unit/modules/{module}/application/ ← handlers with mocks
├── architecture/                      ← import boundary enforcement
├── integration/modules/{module}/      ← repos, outbox, cache (testcontainers)
└── e2e/modules/{module}/              ← full API tests (testcontainers)
```

---

## 8. 🔧 Dev Commands

```bash
uv run ruff check --fix .                          # lint
uv run ruff format .                               # format
uv run mypy .                                      # type check
uv run alembic revision --autogenerate -m "desc"   # create migration
uv run alembic upgrade head                        # apply migrations
docker compose -f ../docker-compose.yml up -d       # start infrastructure
uv run uvicorn src.bootstrap.web:create_app --factory --reload --host 0.0.0.0 --port 8000
```

---

## 9. 🔌 Hooks Configuration

State updates are handled by the `SubagentStop` hook in `.claude/settings.json`.
The hook auto-detects the agent (exact or fuzzy match) and calls the appropriate
`pipeline-state.sh` command — `complete` for PRD agents, `complete-mt` for loop agents.

**Agent prompts must NOT define their own `hooks.Stop` in YAML frontmatter** — that would
cause `mark_complete` to fire twice (once from frontmatter, once from settings.json).

```json
{
  "hooks": {
    "SubagentStop": [
      {
        "matcher": "context-analyst|competitive-intel|gap-analysis|prd-writer|review-qa|senior-pm|senior-architect|senior-backend|senior-reviewer|senior-qa",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/on-agent-stop.sh",
            "timeout": 30
          }
        ]
      }
    ]
  },
  "permissions": {
    "allow": ["Command(.claude/hooks/*)"]
  }
}
```

**Hook files:**

- `.claude/hooks/pipeline-state.sh` — state manager (v2 with MT tracking)
  - PRD phase: `init`, `start`, `complete`, `status`, `next`, `resume`
  - MT phase: `init-mt`, `start-mt`, `complete-mt`, `block-mt`, `mt-status`, `resume-mt`
- `.claude/hooks/on-agent-stop.sh` — SubagentStop hook: auto-detects agent, updates state
- `.claude/hooks/error.log` — hook error log for debugging

---

## 10. 🧠 Context Window Protection

- All persistent rules live HERE in CLAUDE.md — conversation context is ephemeral
- Use `/compact` proactively when working on large chunks (>20 file operations)
- Delegate research and exploration to subagents — keeps main context clean
- Plans live in `docs/superpowers/plans/` and pipeline artifacts — they survive compaction
- After compaction, run `bash .claude/hooks/pipeline-state.sh status` to restore pipeline awareness
- Track context usage via `/context` command when sessions run long

---

## 11. 📁 Project Structure

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
├── agents/                       # Pipeline agents (3 modes)
│   ├── context-analyst.md        # feature — topic → brief
│   ├── competitive-intel.md      # on-demand — market research
│   ├── gap-analysis.md           # on-demand — decision matrix
│   ├── prd-writer.md             # feature — write PRD
│   ├── review-qa.md              # feature — validate PRD
│   ├── senior-pm.md              # feature — micro-task decomposition
│   ├── senior-architect.md       # feature — architecture per MT
│   ├── senior-backend.md         # feature + task — implementation
│   ├── senior-reviewer.md        # on-demand — code review
│   └── senior-qa.md              # feature + task — tests
├── hooks/
│   ├── pipeline-state.sh         # State manager (v2 — PRD + MT tracking)
│   ├── on-agent-stop.sh          # SubagentStop hook (fuzzy match + MT-aware)
│   └── error.log                 # Hook error log
├── pipeline-runs/
│   ├── current/
│   │   ├── state.json            # Pipeline + MT state
│   │   └── artifacts/            # Active pipeline outputs
│   │       ├── arch/             # Agent 7 plans (per MT)
│   │       ├── review/           # Agent 9 reviews (per MT)
│   │       └── qa-tests/         # Agent 10 tests (per MT)
│   └── archive/                  # Previous runs
└── settings.json                 # Hook configuration (single SubagentStop)

docs/
└── superpowers/
    └── plans/                    # Persistent plans (survive compaction)
```
