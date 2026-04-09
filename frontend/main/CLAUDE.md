# Frontend Main — Loyality Project

**Component:** `frontend-main` | **Vault tag:** `[project/loyality, frontend-main]`

Customer-facing Telegram Mini App. Part of a larger project — see `../../CLAUDE.md` for project overview, cross-service architecture, and Knowledge Base vault rules.

When saving research/documents to the vault, use `component: frontend-main` in frontmatter and include `frontend-main` in tags.

## Overview

Next.js 16, TypeScript, React 19, Redux Toolkit. Deployed on Netlify. No `src/` directory — code lives at project root.

## Commands

```bash
npm install          # install dependencies
npm run dev          # next dev (port 3000)
npm run build        # next build
npm run lint         # eslint (core-web-vitals config)
```

No test runner configured. Audit scripts available: `node scripts/audit-unused-public-assets.mjs`, `node scripts/audit-unused-source-files.mjs`.

## Environment Variables

```
BACKEND_API_BASE_URL=http://localhost:8080   # Backend API (server-side only)
BROWSER_DEBUG_AUTH=true                       # Dev-only: mock auth without Telegram
NEXT_PUBLIC_BROWSER_DEBUG_AUTH=true
COOKIE_DOMAIN=                                # Leave empty for localhost
DADATA_TOKEN=...                              # Address suggestion service
DADATA_SECRET=...
```

## Architecture

### Path Alias

`@/*` maps to project root (e.g. `@/lib/store/api` → `./lib/store/api`). Configured in `tsconfig.json`.

### BFF Proxy Pattern

Browser never calls the backend directly. All requests flow through Next.js API routes:

- `app/api/backend/[...path]/route.ts` — catch-all proxy to `BACKEND_API_BASE_URL`. Attaches Bearer token from httpOnly cookies. 25s timeout. Forwards only safe headers (accept, content-type, accept-language).
- `app/api/auth/{telegram,refresh,logout}/` — auth-specific BFF routes managing JWT cookie lifecycle.
- `app/api/dadata/{suggest,clean}/` — address suggestion proxy to DaData API.

### Auth Flow

1. Telegram WebApp SDK loads via `<Script strategy="beforeInteractive">` in root layout.
2. `TelegramProvider` reads `window.Telegram.WebApp`, publishes initData to window globals + custom event `lm:telegram:initdata`.
3. `TelegramAuthBootstrap` captures initData, sends `POST /api/auth/telegram` to BFF.
4. BFF validates initData with backend, sets httpOnly cookies (`loyalty_access` / `loyalty_refresh`).
5. RTK Query `baseQueryWithReauth` auto-refreshes on 401 via mutex pattern (prevents token stampede).
6. Debug mode: set `BROWSER_DEBUG_AUTH=true` to bypass Telegram entirely in development.

### State Management (Redux Toolkit + RTK Query)

- Store: `lib/store/store.ts` — two slices: `api` (RTK Query) + `auth` (authSlice).
- API: `lib/store/api.ts` — `createApi` with dual base queries (auth routes → local, everything else → `/api/backend`).
- Tag types for cache invalidation: `User`, `Products`, `Product`, `Categories`, `Brands`.
- Typed hooks: `useAppDispatch`, `useAppSelector` from `lib/store/hooks.ts`.
- Auth states: `idle` → `loading` → `authenticated` | `expired` | `error`.

### Telegram SDK Integration

Comprehensive wrapper in `lib/telegram/`:

- `TelegramProvider` — React context providing WebApp instance, user, theme, viewport, safe areas. Auto-sets CSS custom properties (`--tg-theme-*`, `--tg-viewport-*`, `--tg-safe-area-*`).
- 25+ hooks for Telegram features: `useTelegram`, `useMainButton`, `useBackButton`, `useHaptic`, `usePopup`, `useQrScanner`, `useBiometric`, `useFullscreen`, etc.
- Mobile-specific: auto-expand, request fullscreen, disable vertical swipes on iOS/Android.

### Styling

- CSS Modules (`.module.css` files) + global CSS variables in `globals.css`.
- **No Tailwind** — unlike the admin panel.
- Fonts: Inter (400/500/600/700), BebasNeue (700) — self-hosted in `/public/fonts/`.
- Telegram theme colors available as `--tg-theme-*` CSS variables (set by TelegramProvider).
- `cn()` utility from `lib/format/cn.ts` wraps `clsx` (no `twMerge` — not needed without Tailwind).

### Root Layout Component Tree

```
html → body → StoreProvider → TelegramProvider → TelegramAuthBootstrap + InputFocusFix + {children} + WebViewErrorAlert
```

### Key Conventions

- **Error hierarchy**: `AppError` → `ApiError` (status-based), `NetworkError` in `lib/errors.ts`.
- **Format utilities** in `lib/format/`: `price.ts`, `date.ts`, `cn.ts`, `brand-image.ts`, `product-image.ts`.
- **Type definitions** in `lib/types/`: `api.ts`, `catalog.ts`, `user.ts`, `auth.ts`, `ui.ts`, `telegram-globals.d.ts`.
- **Feature components** organized by domain in `components/blocks/`: cart, catalog, favorites, home, product, profile, promo, reviews, search, telegram.
- **UI primitives**: `components/ui/` — Button, BottomSheet (with CSS Modules).
- **Layout components**: `components/layout/` — Header, Footer, Layout.
- **iOS workarounds**: `components/ios/InputFocusFix` — fixes focus behavior in iOS WebViews.

### Edge Middleware

`middleware.ts` runs on all non-static routes:
- CSRF defense: validates Origin header on POST requests to `/api/auth/*`.
- Security headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: SAMEORIGIN` (for Telegram iframe embedding), `Referrer-Policy: strict-origin-when-cross-origin`.

### Pages

App Router pages in `app/`: catalog, product, checkout, favorites, invite-friends, poizon, profile, promo, search, trash.
