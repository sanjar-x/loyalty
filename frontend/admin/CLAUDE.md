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

Admin panel for a loyalty marketplace. Next.js 16 App Router, JavaScript/JSX (no TypeScript), Tailwind CSS 4.

### Data Flow (BFF pattern)

Browser never calls the backend directly. Two-layer proxy:

1. **Client-side**: `services/*.js` call local `/api/*` routes via `fetch` with `credentials: 'include'`
2. **Server-side**: `app/api/` route handlers call backend via `backendFetch()` (`lib/api-client.js`) or image service via `imageBackendFetch()` (`lib/image-api-client.js`)

Some services (e.g. `services/products.js:getProducts()`) fall back to seed data from `data/` when API is unavailable.

### Auth

- **Middleware-like proxy**: `src/proxy.js` handles token refresh on `/admin/*` routes — decodes JWT, checks expiry, refreshes via backend `/api/v1/auth/refresh`, sets httpOnly cookies
- **Client-side**: `useAuth()` hook from `hooks/useAuth.jsx` — Context-based, fetches `/api/auth/me` on mount. `AuthProvider` wraps the admin layout
- JWT tokens stored in httpOnly cookies (`access_token` 15min, `refresh_token` 30d), managed by `lib/auth.js`

### Key Conventions

- **Path alias**: `@/*` maps to `src/*` (via jsconfig.json + webpack alias in next.config.js)
- **Class merging**: Always use `cn()` from `@/lib/utils` — never `clsx()` directly. `cn` wraps clsx + twMerge
- **i18n for product data**: Objects `{ru: "...", en: "..."}`. Extract with `i18n(obj)`, construct with `buildI18nPayload(ru, en)` — when `en` is empty, copies `ru` as fallback
- **SVG icons**: Import from `src/assets/icons/*.svg` as React components (via `@svgr/webpack`)
- **Dates**: Use `@/lib/dayjs` (pre-configured with ru locale, plugins: isSameOrAfter, isSameOrBefore, localizedFormat). Format with `formatDateTime()` from `@/lib/utils`
- **Currency**: `formatCurrency(value)` returns `"1 234 ₽"` format
- **Russian plurals**: `pluralizeRu(count, one, few, many)`

### Product Status FSM

`draft → enriching → ready_for_review → published → archived`. Transitions and labels in `lib/constants.js`. Status changes go through `PATCH /api/catalog/products/[productId]/status`.

### Media Upload Flow (3 steps)

1. `reserveMediaUpload({contentType, filename})` → presigned S3 URL + storageObjectId
2. `uploadToS3(presignedUrl, file)` → direct upload to MinIO/S3
3. `confirmMedia(storageObjectId)` → then `pollMediaStatus()` until COMPLETED/FAILED

### Product Creation

Multi-step orchestration in `useSubmitProduct` hook: create product → bulk assign attrs → generate SKU matrix → patch individual SKU prices → upload media (3 concurrent) → change status. Form state managed separately by `useProductForm` hook (reducer-based, no API calls).

### Design Tokens

Custom `app-*` color palette in `tailwind.config.js` (bg, panel, border, text, muted, sidebar, success, danger, etc.). Use these instead of raw Tailwind colors for UI consistency.

### Security Headers

Configured in `next.config.js`: CSP, HSTS, X-Frame-Options DENY, nosniff, strict referrer policy, permissions policy.

## Environment Variables

```
BACKEND_URL=http://127.0.0.1:8000          # Main API
IMAGE_BACKEND_URL=http://127.0.0.1:8001    # Image service
IMAGE_BACKEND_API_KEY=dev-api-key           # Image service auth
```
