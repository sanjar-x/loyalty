# Loyality — Loyalty Marketplace

uv-workspace monorepo. Each deployable artefact lives under `apps/` with its own `pyproject.toml`, Dockerfile, and Railway service config; `apps/backend/` doubles as the FastAPI web service AND the `loyality` workspace member that every other app re-exports from. See [[ADR-008 Multi-Package Modular Monorepo]] for the rationale.

## Components

| Component       | Path                              | Package name           | Tech                                              | Port | Deployment |
| --------------- | --------------------------------- | ---------------------- | ------------------------------------------------- | ---- | ---------- |
| Backend / Web   | `apps/backend/`                   | `backend`              | FastAPI HTTP + library (no torch)                 | 8080 | Railway    |
| Bot             | `apps/bot/`                       | `telegram-bot`         | Aiogram 3 polling (not yet deployed)              | —    | (planned)  |
| Core worker     | `apps/workers/core/`              | `core-worker`          | TaskIQ worker, non-image queues                   | —    | Railway    |
| Image storage   | `apps/workers/image/storage/`     | `image-storage-worker` | (planned) Pillow + S3, no torch                   | —    | (Phase 5)  |
| Image rmbg      | `apps/workers/image/rmbg/`        | `image-rmbg-worker`    | TaskIQ + torch/transformers/timm/kornia           | —    | Railway    |
| Scheduler       | `apps/workers/scheduler/`         | `scheduler-worker`     | TaskIQ scheduler (cron)                           | —    | Railway    |
| Frontend Admin  | `frontend/admin/`                 | (NextJS, separate repo)| Next.js 16, JSX, Tailwind 4                       | 3000 | Netlify    |
| Frontend Main   | `frontend/main/`                  | (NextJS, separate repo)| Next.js 16, TypeScript, React 19                  | 3000 | Netlify    |

Each component has its own `CLAUDE.md` with specific commands, architecture, and patterns. Read it when working in that directory.

## uv workspace

```bash
# From repo root:
uv sync --all-groups                                       # shared .venv at <root>/.venv
uv tree --package <package-name>                           # dependency graph of one app
uv export --package <package-name> --no-dev --format requirements-txt
                                                           # exact list a Docker build will install
```

Docker build per app:

```bash
docker build -f apps/<path>/Dockerfile -t <image-name> .   # context = monorepo root
```

Verified build isolation (Phase 1):
- `backend`, `core-worker`, `scheduler-worker`, `telegram-bot` — **0** lines matching `^torch==` in their export
- `image-rmbg-worker` — 5 lines (torch + torchvision + transformers + timm + kornia)

## Component Identity Map

When running Claude Code from a subdirectory, identify which component you are in:

| Working directory contains | Component ID     | Vault tag                            |
| -------------------------- | ---------------- | ------------------------------------ |
| `apps/backend/src/modules/`| `backend`        | `[project/loyality, backend]`        |
| `frontend/main/`           | `frontend-main`  | `[project/loyality, frontend-main]`  |
| `frontend/admin/`          | `frontend-admin` | `[project/loyality, frontend-admin]` |
| Root `loyality/`           | `project`        | `[project/loyality]`                 |

Use the **Vault tag** column when writing notes to the Knowledge vault — always include the component tag.

## Infrastructure

```bash
# From backend/:
docker compose up -d    # Postgres 18, Redis 8.4, RabbitMQ 4.2, MinIO
```

## Cross-Service Communication

```
Frontend Main ──cookie──► BFF proxy ──Bearer──► Backend API (/api/v1/*)
Frontend Admin ──cookie──► BFF proxy ──Bearer──► Backend API (/api/v1/*)
                                                    └─ /api/v1/admin/media/* (image module)
Telegram Bot ──direct──► Backend API
```

Image lifecycle (S3 + Pillow processing) lives inside the backend as the
``image`` bounded-context module — formerly a standalone ``image_backend``
microservice, consolidated in PR #31 / REC-026 (2026-05-08).

Auth: JWT (HS256) + RBAC (admin → manager → customer). Telegram Mini App: HMAC-SHA256.
Error envelope: `{"error": {"code", "message", "details", "request_id"}}`.

## Knowledge Base (Obsidian Vault) — ALWAYS FOLLOW

Vault: `/home/sanjar/Desktop/knowledge-base/` (via `additionalDirectories`)
Project docs: `/home/sanjar/Desktop/knowledge-base/Projects/loyality/`

### When to write to vault (PROACTIVE — do automatically)

- Research completed on any topic → Research note
- Feature/module designed → update FRD + TRD sections
- Architectural decision made → new ADR
- Reusable concept discovered → Note in Notes/
- Bug/integration issue found → update Known Issues in dashboard
- **When in doubt — save. Structured info is always better than lost context.**

### File placement

**Vault structure:**
```
Projects/loyality/
├── Loyality Project.md              ← dashboard
├── Loyality BRD.md                  ← project-level
├── Loyality FRD.md                  ← project-level (sections per module)
├── Loyality TRD.md                  ← project-level (all components)
├── ADR-{NNN} *.md                   ← cross-cutting ADRs
├── backend/                         ← backend-specific docs (incl. image module)
├── frontend-main/                   ← customer app-specific docs
└── frontend-admin/                  ← admin panel-specific docs
```

**Routing rules — where to save based on component:**

| Type                | Scope = project                                     | Scope = component                                     |
| ------------------- | --------------------------------------------------- | ----------------------------------------------------- |
| Research            | `Projects/loyality/Research - {Topic}.md`           | `Projects/loyality/{component}/Research - {Topic}.md` |
| BRD, FRD, TRD       | `Projects/loyality/Loyality {Type}.md`              | (update project-level, add section)                   |
| ADR (cross-cutting) | `Projects/loyality/ADR-{NNN} {Title}.md`            | —                                                     |
| ADR (component)     | —                                                   | `Projects/loyality/{component}/ADR-{NNN} {Title}.md`  |
| SPEC                | `Projects/loyality/SPEC - {Topic}.md`               | `Projects/loyality/{component}/SPEC - {Topic}.md`     |
| Sprint              | `Projects/loyality/Sprint {N}.md`                   | —                                                     |
| Meeting             | `Projects/loyality/Meeting {YYYY-MM-DD} {Topic}.md` | —                                                     |
| Knowledge note      | `Notes/{Concept}.md`                                | `Notes/{Concept}.md` (always project-independent)     |

**How to decide scope:** If the document is about ONE component → component folder. If it spans multiple or is about the project architecture → project root.

### Required frontmatter

```yaml
---
tags: [project/loyality, {component-id}]  # component-id from Identity Map above
type: research|brd|frd|trd|adr|spec|sprint|meeting|note
date: YYYY-MM-DD
status: draft|active|accepted|archived
project: "[[Loyality Project]]"           # wikilink to dashboard
component: backend|frontend-main|frontend-admin|project
---
```

For Notes/ (reusable, project-independent): omit `project` and `component`, use flat tags like `#postgresql`, `#cqrs`.

### Formatting rules

- `[[wikilinks]]` for ALL internal vault references
- Mermaid for diagrams, tables for structured data
- Callouts: `> [!warning]`, `> [!info]`, `> [!tip]`
- Code blocks with language tags
- Russian text, English technical terms
- Self-contained opening paragraph
- `## Related` section at the bottom with links to dashboard + related docs
- Update `[[Loyality Project]]` dashboard when adding new documents

### Slash commands

- `/research {topic}` — research and save to vault
- `/document {type} {topic}` — create/update BRD, FRD, TRD, ADR, SPEC
- `/note {concept}` — save reusable knowledge note
- `/sync-vault` — sync current work state to all vault docs
