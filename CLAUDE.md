# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## AI Agent Orchestration & Plugin Rules

This section defines the operational pipeline for multi-agent development in this project. All agents and sessions MUST follow these rules to prevent context degradation, ensure quality, and maximize parallelism.

### 1. Development Lifecycle Pipeline

Every implementation chunk follows this strict sequence:

```
Plan → Brainstorm → Implement (subagent-driven) → Review → Update CLAUDE.md
```

| Phase | Skill / Plugin | Trigger |
|---|---|---|
| **Plan** | `superpowers:writing-plans` | Any multi-step task or new feature (≥3 files or ≥2 layers touched) |
| **Brainstorm** | `superpowers:brainstorming` | Before any creative work — new features, components, architectural decisions |
| **Implement** | `superpowers:executing-plans` or `superpowers:subagent-driven-development` | When a written plan exists with independent tasks |
| **Review** | `superpowers:requesting-code-review` + `code-review:code-review` | After implementation, before any git commit |
| **Update Context** | `claude-md-management:revise-claude-md` | After each completed chunk to capture new patterns, modules, or conventions |

### 2. Superpowers — Chunk Execution Rules

**When to use `superpowers:executing-plans`:**

- A written plan exists in `docs/superpowers/plans/`
- The plan has checkbox (`- [ ]`) steps to track
- Work spans multiple files across different layers (domain, application, infrastructure, presentation)
**When to use `superpowers:subagent-driven-development`:**
- The plan contains 2+ independent tasks with no shared state
- Tasks can be worked on in parallel without sequential dependencies
- Example: domain entities + ORM models can be built in parallel subagents with worktree isolation
**When to use `superpowers:writing-plans`:**
- Before touching code on any feature that spans ≥3 files or ≥2 architectural layers
- When requirements are ambiguous and need decomposition
- Plans go in `docs/superpowers/plans/YYYY-MM-DD-<feature>.md`
**Mandatory rules:**
- Never skip the planning phase for non-trivial work — even "simple" CRUD touches 4 layers in this architecture
- Use `superpowers:verification-before-completion` before claiming any chunk is done
- Use `superpowers:test-driven-development` when implementing domain logic or command handlers
- Subagents MUST use `isolation: "worktree"` when editing files to prevent conflicts

### 3. Context7 — Dynamic Knowledge Retrieval

**Mandatory triggers — query Context7 BEFORE writing code when:**

- Integrating or updating any external library (SQLAlchemy, FastAPI, Dishka, TaskIQ, Pydantic, Alembic, pytest, attrs, structlog, PyJWT, pwdlib, aiobotocore)
- Implementing a pattern you haven't used in this codebase before
- Writing infrastructure-layer code that depends on library-specific APIs
- Debugging a library-related error

**How to use:**

1. `resolve-library-id` — find the Context7-compatible library ID
2. `query-docs` — retrieve up-to-date docs with a specific query (e.g., "SQLAlchemy async session factory pattern", "Dishka provider scope lifecycle")
3. Apply the retrieved patterns — never rely on memorized APIs that may be outdated

**What NOT to query:**

- Pure domain logic (entities, value objects, events) — these have zero library imports
- Project-internal patterns already documented in this CLAUDE.md

### 4. Code Review — Mandatory Quality Gates

**Before any git commit, ALL of the following must pass:**

1. **Lint & Format:** `uv run ruff check --fix . && uv run ruff format .`
2. **Type Check:** `uv run mypy .` (for modified modules at minimum)
3. **Unit Tests:** `uv run pytest tests/unit/ -v` (must pass, no skips on modified modules)
4. **Architecture Tests:** `uv run pytest tests/architecture/ -v` (boundary violations = hard block)
5. **Agent Code Review:** Invoke `superpowers:requesting-code-review` or the `code-review:code-review` skill
**Code review checklist (from Context7 agent patterns):**

- Clean Architecture violations: no infrastructure imports in domain/application layers
- Cross-module boundary violations: no direct imports between modules (except allowed `user.presentation → identity.presentation`)
- Domain entity purity: attrs dataclasses only, no SQLAlchemy/Pydantic in domain
- UoW discipline: all writes go through `IUnitOfWork`, aggregates registered before commit
- Data Mapper integrity: ORM models never leak into domain; repositories map between them
- Security: no hardcoded secrets, proper input validation at presentation layer
- CQRS separation: commands mutate state, queries are read-only
**Review severity levels:**

- **CRITICAL** (must fix): Security vulnerabilities, architecture violations, data corruption risks
- **MAJOR** (should fix): Missing error handling, CQRS violations, missing UoW registration
- **MINOR** (nice to fix): Naming inconsistencies, missing type hints on new code

### 6. Feature Dev & Engineering — Code Generation Rules

**When to use `feature-dev:feature-dev`:**

- Implementing a new bounded context module from scratch
- Adding a new aggregate root with full CQRS stack (entity → commands/queries → repository → router)
**Implementation order within a module (always follow this sequence):**

1. Domain layer first — entities, value objects, events, exceptions, repository interfaces
2. Application layer — command/query handlers (import only from domain)
3. Infrastructure layer — ORM models, repository implementations, Dishka providers
4. Presentation layer — Pydantic schemas, FastAPI routers, DI dependencies
5. Bootstrap integration — register providers in container, mount routers in web.py
6. Tests — unit (domain + application), integration (repositories), e2e (API endpoints), architecture (boundaries)

**Subagent parallelism opportunities within this sequence:**

- Steps 1-2 can run in parallel (domain has no deps, application imports only domain interfaces)
- Step 3 depends on steps 1-2 (implements domain interfaces)
- Steps 4-5 depend on step 3
- Step 6 can partially parallelize (unit tests after step 2, integration after step 3)

### 7. Plugin Development — Extension Rules

**When to use `plugin-dev:*` skills:**

- Creating new hooks for automated validation (e.g., architecture boundary checks on every edit)
- Adding new slash commands for repeated workflows
- Building custom agents for project-specific tasks

**Project-specific hook opportunities:**

- `PostToolUse` on `Write|Edit` → run `ruff check` on the modified file
- `PreToolUse` on `Bash(git commit*)` → verify lint + type check + tests pass
- Architecture boundary validation hook → prevent cross-module imports at edit time

### 8. Context Window Protection

**Rules to prevent context degradation (from Context7 best practices):**

- Store all persistent rules in this CLAUDE.md — conversation context is ephemeral
- Use `/compact` proactively when working on large chunks (>20 file operations)
- Delegate research and exploration to subagents — keeps main context clean
- Use `superpowers:subagent-driven-development` for parallel work instead of sequential exploration
- Track context usage via `/context` command when sessions run long
- Plans live in `docs/superpowers/plans/` (not in conversation) so they survive compaction
- After compaction, critical decisions persist here in CLAUDE.md, not in conversation history

## Project Overview

E-commerce — async REST API built with FastAPI, following DDD / Clean Architecture / CQRS / Modular Monolith patterns.
