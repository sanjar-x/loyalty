# Loyality — Loyalty Marketplace

Modular monolith with three deployable services and two frontends.

## Components

| Component      | Path               | Tech                                            | Port | Deployment |
| -------------- | ------------------ | ----------------------------------------------- | ---- | ---------- |
| Backend        | `backend/`         | FastAPI, Python 3.14, Clean Architecture        | 8080 | Railway    |
| Image Backend  | `image_backend/`   | FastAPI, Python 3.14, Pillow, aiobotocore       | 8080 | Railway    |
| Frontend Main  | `frontend/main/`   | Next.js 16, TypeScript, React 19, Redux Toolkit | 3000 | Netlify    |
| Frontend Admin | `frontend/admin/`  | Next.js 16, JSX, Tailwind CSS 4                 | 3000 | Netlify    |
| Telegram Bot   | `backend/src/bot/` | Aiogram 3, FSM states                           | —    | Railway    |

Each component has its own `CLAUDE.md` with specific commands, architecture, and patterns. Read it when working in that directory.

## Component Identity Map

When running Claude Code from a subdirectory, identify which component you are in:

| Working directory contains | Component ID     | Vault tag                            |
| -------------------------- | ---------------- | ------------------------------------ |
| `backend/src/modules/`     | `backend`        | `[project/loyality, backend]`        |
| `image_backend/`           | `image-backend`  | `[project/loyality, image-backend]`  |
| `frontend/main/`           | `frontend-main`  | `[project/loyality, frontend-main]`  |
| `frontend/admin/`          | `frontend-admin` | `[project/loyality, frontend-admin]` |
| Root `loyality/`           | `project`        | `[project/loyality]`                 |

Use the **Vault tag** column when writing notes to the Knowledge vault — always include the component tag.

## Infrastructure

```bash
# From backend/ or image_backend/:
docker compose up -d    # Postgres 18, Redis 8.4, RabbitMQ 4.2, MinIO
```

## Cross-Service Communication

```
Frontend Main ──cookie──► BFF proxy ──Bearer──► Backend API (/api/v1/*)
Frontend Admin ──cookie──► BFF proxy ──Bearer──► Backend API (/api/v1/*)
                           BFF proxy ──API-Key──► Image Backend (/api/v1/media/*)
Backend ──X-API-Key──► Image Backend (delete only)
Telegram Bot ──direct──► Backend API
```

Auth: JWT (HS256) + RBAC (admin → manager → customer). Telegram Mini App: HMAC-SHA256.
Error envelope: `{"error": {"code", "message", "details", "request_id"}}`.

## Knowledge Base (Obsidian Vault) — ALWAYS FOLLOW

Vault: `/home/sanjar/Desktop/Knowledge/` (via `additionalDirectories`)
Project docs: `/home/sanjar/Desktop/Knowledge/Projects/loyality/`

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
├── backend/                         ← backend-specific docs
├── image-backend/                   ← image backend-specific docs
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
component: backend|image-backend|frontend-main|frontend-admin|project
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
