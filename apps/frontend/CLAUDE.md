# Frontend — Loyality Project

**Component:** `frontend` | **Vault tag:** `[project/loyality, frontend]`

Parent directory for both frontends. See `../CLAUDE.md` for project overview, cross-service architecture, and Knowledge Base vault rules.

## Overview

Two independent Next.js 16 apps sharing no code between them:

- **main/** — Customer-facing Telegram Mini App (TypeScript, React 19, TanStack Query, Zustand, ky, Zod). Deployed on Netlify.
- **admin/** — Admin panel (JSX/JavaScript, Tailwind CSS 4, Feature-Sliced Design). Uses `--webpack` flag for dev/build because `@svgr/webpack` is not Turbopack-compatible.

Both use `npm` as package manager (package-lock.json present).

> `frontend/main/AGENTS.md` warns: **"This is NOT the Next.js you know"** — APIs and conventions in Next.js 16 differ from training-data assumptions. Read `node_modules/next/dist/docs/` before writing code.

## Commands

### Frontend Main (working directory: `frontend/main/`)

```bash
npm install
npm run dev          # next dev (port 3000)
npm run build        # next build
npm run start        # production server
npm run lint         # eslint --max-warnings=0
npm run typecheck    # tsc --noEmit
npm run format       # prettier --write .
npm test             # vitest (unit/component) — see vitest.config.ts
npm run plop         # generate components/hooks from templates/*.hbs
```

### Frontend Admin (working directory: `frontend/admin/`)

```bash
npm install
npm run dev          # next dev --webpack (port 3000)
npm run build        # next build --webpack
npm run lint         # eslint .
npm run typecheck    # tsc --noEmit (LSP only — code is JSX)
npm test             # vitest run
npm run format       # prettier --write .
```

## Environment Variables

### main/.env

```
BACKEND_API_BASE_URL=http://localhost:8080   # Backend API (server-side only)
NEXT_PUBLIC_APP_URL=http://localhost:3000
BROWSER_DEBUG_AUTH=true                       # Dev-only: mock auth without Telegram/backend
NEXT_PUBLIC_BROWSER_DEBUG_AUTH=true
COOKIE_DOMAIN=                                # Leave empty for localhost
DADATA_TOKEN=...                              # Address suggestion service
DADATA_SECRET=...
AUTH_SECRET=...                               # ≥32 chars
```

Validation: `src/env.ts` uses `@t3-oss/env-nextjs` with Zod schemas — invalid env at startup fails fast.

### admin/.env.local

```
BACKEND_URL=http://127.0.0.1:8080
IMAGE_BACKEND_URL=http://127.0.0.1:8080
IMAGE_BACKEND_API_KEY=dev-api-key
```

## Architecture

### main/ — Telegram Mini App

**Project structure** (code lives under `src/`):

```
src/
├── app/                  — Next.js App Router (pages + /api BFF routes)
│   ├── _providers/       — Client-side root providers
│   ├── api/              — Catch-all BFF proxy to BACKEND_API_BASE_URL
│   ├── cart/, catalog/, checkout/, favorites/, invite-friends/,
│   │   poizon/, product/, profile/, promo/, search/
│   ├── error.tsx, global-error.tsx, not-found.tsx, layout.tsx, page.tsx
├── features/             — Feature slices (auth, cart, catalog, favorites,
│                            home, orders, product, profile, referrals,
│                            search, telegram, user)
├── components/
│   ├── layout/           — container, header, footer
│   ├── providers/        — query-provider, theme-provider, toast-provider
│   └── ui/               — Shared UI primitives
├── lib/
│   ├── api-client.ts     — ky-based browser client
│   ├── api-server.ts     — server-side client (Bearer from cookies)
│   ├── auth-events.ts    — auth state event bus
│   ├── query-client.ts   — TanStack Query setup
│   ├── query-keys.ts     — typed query key factories
│   ├── utils.ts          — cn(), helpers
│   └── format/           — price/date formatters
├── stores/               — Zustand stores (cart-store, ui-store)
├── schemas/              — Zod schemas (DTO validation)
├── config/, constants/, hooks/, mocks/, styles/, types/
├── env.ts                — @t3-oss/env-nextjs + Zod validation
└── proxy.ts              — Edge middleware: CSRF defense + security headers
```

**Path alias**: `@/*` maps to `src/*`.

**State management**:
- **Server state** — `@tanstack/react-query` (`QueryClient` in `lib/query-client.ts`, hooks in feature slices).
- **Client state** — `zustand` (`stores/cart-store.ts`, `stores/ui-store.ts`).
- **Auth slice** — `features/auth/store.ts` (Zustand) + `features/auth/server.ts` (server-only token helpers).

**HTTP client**: `ky` (`lib/api-client.ts` for browser, `lib/api-server.ts` for server). Auto-reauth on 401 lives in the BFF layer.

**Auth flow**: Telegram initData → `POST /api/auth/telegram` (BFF route) → backend validates HMAC → JWT tokens stored in httpOnly cookies. Auth state propagated via `lib/auth-events.ts`. Debug mode available via `BROWSER_DEBUG_AUTH=true`.

**Backend proxy**: All backend calls go through `app/api/` route handlers — they attach Bearer token from cookies and forward to `BACKEND_API_BASE_URL`.

**Styling**: CSS Modules + global CSS variables in `app/globals.css`. **Tailwind CSS 4** is also installed (via `@tailwindcss/postcss`), so utility classes are available.

**Telegram integration**: `features/telegram/` exports `TelegramProvider`, runtime/dom/state helpers, and typed `window.Telegram.WebApp` shims.

**Tooling**:
- **Vitest** for unit/component tests (`vitest.config.ts` — jsdom env, react plugin)
- **Playwright** for e2e (`playwright.config.ts`, scenarios under `e2e/`)
- **Plop** generators (`plopfile.ts` + `templates/*.hbs`) for components, hooks, server actions
- **Husky + lint-staged + commitlint** (conventional commits)
- **MSW** for request mocking in tests
- **eslint-plugin-boundaries** to enforce slice import rules

### admin/ — Admin Panel

Uses **Feature-Sliced Design (FSD)** under `src/`. See `frontend/admin/docs/ARCHITECTURE.md` for layering rules.

```
src/
├── app/                — Next.js App Router (pages + /api BFF handlers)
├── widgets/            — Composite UI (Sidebar, PageStub)
├── features/           — User actions (auth, order-filter, pricing,
│                          product-archive, product-filter, product-form,
│                          product-status-change)
├── entities/           — Business entities (brand, category, order, product,
│                          promocode, referral, review, role, staff,
│                          supplier, user)
├── shared/             — api/, auth/, hooks/, lib/, mocks/, query/, ui/
├── assets/icons/       — SVGs imported as React components (@svgr/webpack)
└── middleware.js       — Edge middleware: JWT refresh on /admin/*
```

**Layer dependency rules** (enforced by ESLint `eslint-plugin-boundaries`):

| Layer       | May import from                                 |
| ----------- | ----------------------------------------------- |
| `app/`      | `widgets`, `features`, `entities`, `shared`     |
| `widgets/`  | `features`, `entities`, `shared`                |
| `features/` | `entities` (via index), `shared`, own internals |
| `entities/` | other `entities` (via index), `shared`          |
| `shared/`   | `shared` only                                   |

**Slice public API**: every `entities/<x>` and `features/<x>` exposes only `index.js`. Deep imports break ESLint. `entities/category/server.js` is a server-only entry (uses `next/headers`).

**Path alias**: `@/*` maps to `src/*` (jsconfig.json + webpack alias in next.config.js).

**Auth**:
- **Edge middleware** (`src/middleware.js`) — JWT refresh on `/admin/*`, sets httpOnly cookies.
- **Client-side** — `useAuth()` from `@/features/auth` (Context + `/api/auth/me` on mount).
- Tokens: `access_token` (15 min), `refresh_token` (30 d), managed by `@/shared/auth/cookies`.

**Data fetching**: TanStack Query (`@/shared/query`). Slice `api/` modules call local `/api/*` routes; `app/api/` route handlers proxy to backend via `backendFetch()` (`@/shared/api/api-client`) or image service via `imageBackendFetch()` (`@/shared/api/image-api-client`).

**Styling**: Tailwind CSS 4 + CSS Modules. Custom design tokens (`app-*`) in `tailwind.config.js`. **Always use `cn()` from `@/shared/lib/utils`** — never `clsx()` directly.

**i18n pattern**: Entity data is `{ru, en}` objects. Use `i18n(obj)` and `buildI18nPayload(ru, en)`.

**Product status FSM**: `draft → enriching → ready_for_review → published → archived`. Transitions in `@/entities/product` (`PRODUCT_STATUS_TRANSITIONS`). Status changes via `PATCH /api/catalog/products/[productId]/status`.

**Media upload flow** (3 steps): reserve presigned S3 URL → direct upload → confirm/poll image backend status. All exposed through `@/entities/product`.

**OpenAPI snapshots** (synced backend schemas) live in `frontend/admin/openapi/`:
- `backend.json`, `backend-mini.json`, `image-backend.json`

**Why `--webpack`**: `@svgr/webpack` is required for SVG-as-component imports and is not Turbopack-compatible.

### Shared Patterns

- Both apps use BFF (Backend-for-Frontend) — the browser never calls the backend directly.
- Auth tokens stored in httpOnly cookies, managed by API routes.
- Both connect to the same backend API at `/api/v1/*`.
- Backend error envelope: `{"error": {"code", "message", "details", "requestId"}}` (camelCase wire format).
