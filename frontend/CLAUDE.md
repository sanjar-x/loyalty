# Frontend — Loyality Project

**Component:** `frontend` | **Vault tag:** `[project/loyality, frontend]`

Parent directory for both frontends. See `../CLAUDE.md` for project overview, cross-service architecture, and Knowledge Base vault rules.

## Overview

Two independent Next.js 16 apps sharing no code between them:

- **main/** — Customer-facing Telegram Mini App (TypeScript, React 19, Redux Toolkit). Deployed on Netlify.
- **admin/** — Admin panel (JavaScript/JSX, Tailwind CSS 4, CSS Modules). Uses `--webpack` flag for dev/build.

Both use `npm` as package manager (package-lock.json present).

## Commands

### Frontend Main (working directory: `frontend/main/`)

```bash
npm install
npm run dev      # next dev (port 3000)
npm run build    # next build
npm run lint     # eslint (core-web-vitals config)
```

### Frontend Admin (working directory: `frontend/admin/`)

```bash
npm install
npm run dev      # next dev --webpack (port 3000)
npm run build    # next build --webpack
npm run lint     # eslint .
npm run format   # prettier --write .
```

## Environment Variables

### main/.env

```
BACKEND_API_BASE_URL=http://localhost:8000   # Backend API (server-side only)
BROWSER_DEBUG_AUTH=true                       # Dev-only: mock auth without Telegram/backend
NEXT_PUBLIC_BROWSER_DEBUG_AUTH=true
COOKIE_DOMAIN=                                # Leave empty for localhost
DADATA_TOKEN=...                              # Address suggestion service
DADATA_SECRET=...
```

### admin/.env.local

```
BACKEND_URL=http://127.0.0.1:8000
IMAGE_BACKEND_URL=http://127.0.0.1:8001
IMAGE_BACKEND_API_KEY=dev-api-key
```

## Architecture

### main/ — Telegram Mini App

**Project structure** (no `src/` directory — files at project root):

```
app/              — App Router pages and API routes
components/
  blocks/         — Feature components (cart, catalog, product, search, telegram, reviews, etc.)
  ios/            — iOS WebView workarounds (InputFocusFix)
  layout/         — Layout components
  providers/      — StoreProvider (Redux)
  ui/             — Shared UI primitives (Button, BottomSheet) with CSS Modules
lib/
  auth/           — Cookie helpers, token management (server-side)
  format/         — Utility formatters (price, date, cn, brand-image, product-image)
  hooks/          — Custom hooks (useItemFavorites)
  store/          — Redux store, RTK Query API, authSlice
  telegram/       — Telegram WebApp SDK wrapper, TelegramProvider, hooks
  types/          — TypeScript types (api, catalog, user, auth, ui, telegram-globals)
middleware.ts     — Edge middleware: CSRF defense + security headers for Telegram iframe
```

**Path alias**: `@/*` maps to project root (e.g. `@/lib/store/api` → `./lib/store/api`).

**State management**: Redux Toolkit + RTK Query.
- Store: `lib/store/store.ts` — two reducers: `api` (RTK Query) + `auth` (authSlice)
- API client: `lib/store/api.ts` — `createApi` with auto-reauth on 401 (mutex-based token refresh)
- Typed hooks: `lib/store/hooks.ts` — `useAppDispatch`, `useAppSelector`
- Tag types: `User`, `Products`, `Product`, `Categories`, `Brands`

**Auth flow**: Telegram initData → `POST /api/auth/telegram` (BFF route) → backend validates HMAC → JWT tokens stored in httpOnly cookies. RTK Query base query auto-refreshes on 401. Debug mode available via `BROWSER_DEBUG_AUTH=true`.

**Backend proxy**: All backend calls go through `app/api/backend/[...path]/route.ts` — a catch-all BFF proxy that attaches Bearer token from cookies and forwards to `BACKEND_API_BASE_URL`.

**Styling**: CSS Modules (`.module.css` files) + global CSS variables in `globals.css`. No Tailwind.

**Root layout** wraps: `StoreProvider` → `TelegramProvider` → `TelegramAuthBootstrap` + `InputFocusFix` + `WebViewErrorAlert`.

### admin/ — Admin Panel

**Project structure** (code inside `src/`):

```
src/
  app/
    admin/          — Protected admin pages (products, orders, users, reviews, returns, settings/)
    api/            — BFF proxy routes mirroring backend API structure
    login/          — Login page
  assets/icons/     — SVG icons (imported as React components via @svgr/webpack)
  components/
    admin/          — Feature components per page (products, orders, reviews, settings/, users)
    ui/             — Shared UI primitives (Badge, Modal, Pagination, SearchInput, etc.)
  data/             — Seed/mock data files for development (fallback when API unavailable)
  hooks/            — Custom hooks (useAuth, useProductForm, useSubmitProduct, useOrderFilters, etc.)
  services/         — Client-side fetch wrappers calling local /api/* routes
  lib/
    api-client.js   — Server-side backendFetch() for main API
    image-api-client.js — Server-side imageBackendFetch() for image service
    auth.js         — Cookie-based JWT token management
    utils.js        — cn(), formatCurrency(), pluralizeRu(), i18n(), buildI18nPayload()
    constants.js    — Status labels, product FSM transitions
```

**Path alias**: `@/*` maps to `src/*` (e.g. `@/lib/utils` → `src/lib/utils.js`).

**No TypeScript** — all files are `.js`/`.jsx`. Uses jsconfig.json for path aliases.

**Auth**: Context-based via `useAuth()` hook from `hooks/useAuth.jsx`. AuthProvider wraps admin layout, fetches `/api/auth/me` on mount.

**API pattern**: All API calls go through Next.js API routes (`src/app/api/`) which proxy to backend using `backendFetch()`. API routes handle auth cookies server-side. Image uploads go through `imageBackendFetch()` with API key auth.

**Styling**: Tailwind CSS 4 + CSS Modules for complex layouts. Custom design tokens defined as `app-*` colors in `tailwind.config.js`. **Always use `cn()` from `@/lib/utils`** for conditional classes — never use `clsx()` directly (cn wraps clsx + twMerge).

**SVG imports**: `@svgr/webpack` configured in `next.config.js` — import SVGs directly as React components.

**i18n pattern**: Product data uses `{ru: "...", en: "..."}` objects. Use `i18n(obj)` to extract display value, `buildI18nPayload(ru, en)` to construct.

**Why `--webpack`**: Admin uses `@svgr/webpack` for SVG component imports, which requires webpack bundler instead of Turbopack.

**Product status FSM**: `draft → enriching → ready_for_review → published → archived`. Transitions defined in `lib/constants.js` (`PRODUCT_STATUS_TRANSITIONS`). Status changes go through `PATCH /api/catalog/products/[productId]/status`.

**Media upload flow** (3 steps): (1) reserve upload via image backend → get presigned S3 URL, (2) upload file directly to S3/MinIO, (3) confirm/poll image backend for processing status.

**Data fetching layers**: `services/` (client-side, calls `/api/*` routes) → `app/api/` route handlers (server-side, calls backend via `backendFetch()`). Some services fall back to seed data from `data/` when API is unavailable.

### Shared Patterns

- Both apps use BFF (Backend-for-Frontend) pattern — browser never calls the backend directly
- Auth tokens stored in httpOnly cookies, managed by API routes
- Both connect to the same backend API at `/api/v1/*`
- Backend error envelope: `{"error": {"code", "message", "details", "request_id"}}`
