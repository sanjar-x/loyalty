# Frontend Admin — Loyality Project

**Component:** `frontend-admin` | **Vault tag:** `[project/loyality, frontend-admin]`

Admin panel for the Loyality marketplace. Part of a larger project — see `../../CLAUDE.md` for project overview, cross-service architecture, and Knowledge Base vault rules.

When saving research/documents to the vault, use `component: frontend-admin` in frontmatter and include `frontend-admin` in tags.

## Commands

```bash
npm run dev      # next dev --webpack (port 3000)
npm run build    # next build --webpack
npm run lint     # eslint .
npm run format   # prettier --write .
npm run format:check  # prettier --check .
```

Uses `--webpack` because `@svgr/webpack` requires webpack instead of Turbopack.

## Architecture

Next.js 16 App Router, JavaScript/JSX (no TypeScript), Tailwind CSS 4. Code follows **Feature-Sliced Design (FSD)** under `src/`. See `docs/ARCHITECTURE.md` for the full layering rules and decision checklist.

### Source layout

```
src/
├── app/                     # Next.js routes (pages + /api BFF handlers)
├── widgets/                 # composite UI assembled from features/entities (Sidebar, PageStub)
├── features/                # user actions / business interactions
│   ├── auth/                                  hooks/, index.js
│   ├── order-filter/                          ui/, model/, index.js
│   ├── pricing/                               ui/, model/, api/, lib/, index.js
│   ├── product-archive/                       ui/, index.js
│   ├── product-filter/                        ui/, model/, index.js
│   ├── product-form/                          model/, index.js
│   └── product-status-change/                 ui/, index.js
├── entities/                # business entities (cards, reads, models)
│   ├── brand/                                 api/, index.js
│   ├── category/                              ui/, api/, index.js, server.js
│   ├── order/                                 ui/, api/, lib/, index.js
│   ├── product/                               ui/, api/, lib/, index.js
│   ├── promocode/                             ui/, api/, index.js
│   ├── referral/                              api/, index.js
│   ├── review/                                ui/, api/, index.js
│   ├── role/                                  ui/, index.js
│   ├── staff/                                 api/, index.js
│   ├── supplier/                              api/, index.js
│   └── user/                                  ui/, api/, index.js
├── shared/                  # cross-cutting, no business logic
│   ├── ui/                  # Badge, Modal, Pagination, SearchInput, StarsRow, Metric, CopyMark, DateRangePicker
│   ├── lib/                 # cn, formatters, dayjs, stats (calculatePeriodStats, isWithinRange, …), pluralizeRu, i18n, copyToClipboard
│   ├── api/                 # api-client, image-api-client, server-cache, geo
│   ├── auth/                # cookies.js (httpOnly cookie helpers)
│   ├── hooks/               # useToast, useOutsideClick, useBodyScrollLock
│   └── mocks/               # dev-only seed data
├── assets/icons/            # SVGs imported as React components
└── middleware.js            # Next.js Edge middleware: JWT refresh for /admin/*
```

### Slice anatomy

Every slice (`entities/<x>` or `features/<x>`) has the same internal segments:

```
<slice>/
├── ui/         # React components
├── model/      # hooks, business state (reducers, providers)
├── api/        # client/server fetch wrappers
├── lib/        # pure utilities, constants
├── config/     # static config (rare)
└── index.js    # public API — the only valid import path from outside
```

The `index.js` (barrel) is the slice's contract. Outside code does:

```js
// ✓
import { ProductRow } from '@/entities/product';
import { useProductFilters } from '@/features/product-filter';

// ✗ — ESLint will reject these
import { ProductRow } from '@/entities/product/ui/ProductRow';
import { useProductFilters } from '@/features/product-filter/model/useProductFilters';
```

`category` ships an extra `server.js` entry for server-only code (uses `next/headers`). Import it explicitly: `@/entities/category/server`.

### Layer dependency rules (enforced by ESLint)

| Layer       | May import from                                 |
| ----------- | ----------------------------------------------- |
| `app/`      | `widgets`, `features`, `entities`, `shared`     |
| `widgets/`  | `features`, `entities`, `shared`                |
| `features/` | `entities` (via index), `shared`, own internals |
| `entities/` | other `entities` (via index), `shared`          |
| `shared/`   | `shared` only                                   |

Cross-feature and cross-entity deep imports are forbidden. Lift shared code to `shared/*` or `entities/*` (or compose at the `widgets/` level).

### Data Flow (BFF pattern)

Browser never calls the backend directly. Two-layer proxy:

1. **Client-side**: feature/entity `api/*.js` call local `/api/*` routes via `fetch` with `credentials: 'include'`.
2. **Server-side**: `app/api/` route handlers call backend via `backendFetch()` (`@/shared/api/api-client`) or image service via `imageBackendFetch()` (`@/shared/api/image-api-client`).

Some entity APIs (e.g. `entities/product/api/products.js:getProducts()`) fall back to seed data from `@/shared/mocks/*` when the live API is unavailable.

### Auth

- **Edge middleware**: `src/middleware.js` handles token refresh on `/admin/*` — decodes JWT, checks expiry, refreshes via backend `/api/v1/auth/refresh`, sets httpOnly cookies. Matched via `config.matcher`.
- **Client-side**: `useAuth()` from `@/features/auth` — Context-based, fetches `/api/auth/me` on mount. `AuthProvider` wraps the admin layout.
- JWT tokens stored in httpOnly cookies (`access_token` 15 min, `refresh_token` 30 d), managed by `@/shared/auth/cookies`.

### Key Conventions

- **Path alias**: `@/*` maps to `src/*` (via jsconfig.json + webpack alias in next.config.js).
- **Class merging**: always `cn()` from `@/shared/lib/utils` — never `clsx()` directly. `cn` wraps clsx + twMerge.
- **i18n for entity data**: objects `{ru: "...", en: "..."}`. Extract with `i18n(obj)`, construct with `buildI18nPayload(ru, en)` — when `en` is empty, copies `ru` as fallback.
- **SVG icons**: import from `src/assets/icons/*.svg` as React components (via `@svgr/webpack`).
- **Dates**: use `@/shared/lib/dayjs` (pre-configured with ru locale, plugins: isSameOrAfter, isSameOrBefore, localizedFormat). Format with `formatDateTime()` from `@/shared/lib/utils`.
- **Currency**: `formatCurrency(value)` returns `"1 234 ₽"` format.
- **Russian plurals**: `pluralizeRu(count, one, few, many)`.

### Product Status FSM

`draft → enriching → ready_for_review → published → archived`. Transitions and labels in `@/entities/product` (`PRODUCT_STATUS_TRANSITIONS`, `PRODUCT_STATUS_LABELS`). Status changes go through `PATCH /api/catalog/products/[productId]/status`.

### Media Upload Flow (3 steps)

1. `reserveMediaUpload({contentType, filename})` → presigned S3 URL + storageObjectId
2. `uploadToS3(presignedUrl, file)` → direct upload to MinIO/S3
3. `confirmMedia(storageObjectId)` → then `subscribeMediaStatus()` until COMPLETED/FAILED

All exposed through `@/entities/product`.

### Product Creation

Multi-step orchestration in `useSubmitProduct` hook (`@/features/product-form`): create product → bulk-assign attrs → generate SKU matrix → patch individual SKU prices → upload media (3 concurrent) → change status. Form state managed separately by `useProductForm` (reducer-based, no API calls).

### Design Tokens

Custom `app-*` color palette in `tailwind.config.js` (bg, panel, border, text, muted, sidebar, success, danger, etc.). Use these instead of raw Tailwind colors.

### Security Headers

Configured in `next.config.js`: CSP, HSTS, X-Frame-Options DENY, nosniff, strict referrer policy, permissions policy.

## Environment Variables

```
BACKEND_URL=http://127.0.0.1:8080          # Main API
IMAGE_BACKEND_URL=http://127.0.0.1:8080    # Image service
IMAGE_BACKEND_API_KEY=dev-api-key          # Image service auth
```

## OpenAPI snapshots

Synced backend schemas live in `openapi/`:

- `openapi/backend.json` — full backend OpenAPI
- `openapi/backend-mini.json` — trimmed backend snapshot
- `openapi/image-backend.json` — image service OpenAPI

## Documentation

`docs/ARCHITECTURE.md` — layer rules, slice anatomy, "where to put new code" checklist (read this first when onboarding).
`docs/product-creation-flow.md` — multi-step product creation orchestration.
