# SPEC: Project Foundation Setup

> Enterprise-grade Next.js 16 frontend application foundation.
> Frontend-only BFF (Backend for Frontend) / proxy layer.
> ORM, database, server-side business logic — on backend services side.
>
> Based on research: `docs/research/01..05`
> Date: 2026-04-05

---

## Table of Contents

- [0. Current State](#0-current-state)
- [1. Package Manager Migration](#1-package-manager-migration)
- [2. Project Structure](#2-project-structure)
- [3. TypeScript Configuration](#3-typescript-configuration)
- [4. Tailwind CSS v4 Design Tokens](#4-tailwind-css-v4-design-tokens)
- [5. shadcn/ui Setup](#5-shadcnui-setup)
- [6. ESLint v9 + Prettier](#6-eslint-v9--prettier)
- [7. Environment Variables](#7-environment-variables)
- [8. Next.js Configuration & Caching](#8-nextjs-configuration--caching)
- [9. Git Hooks](#9-git-hooks)
- [10. Testing Infrastructure](#10-testing-infrastructure)
- [11. Core Libraries](#11-core-libraries)
- [12. npm Scripts](#12-npm-scripts)
- [13. CI/CD Pipeline](#13-cicd-pipeline)
- [14. Code Generation (Plop.js)](#14-code-generation-plopjs)
- [15. Out of Scope (Phase 2+)](#15-out-of-scope-phase-2)
- [Appendix A: Full Dependency List](#appendix-a-full-dependency-list)
- [Appendix B: File Tree After Setup](#appendix-b-file-tree-after-setup)

---

## 0. Current State

Fresh `npx create-next-app@latest new` project:

| Aspect           | Current                           | Target                                        |
| ---------------- | --------------------------------- | --------------------------------------------- |
| Next.js          | 16.2.2                            | 16.2.2 (keep)                                 |
| React            | 19.2.4                            | 19.2.4 (keep)                                 |
| Package manager  | npm (package-lock.json)           | pnpm 10                                       |
| Directory layout | `app/` in root                    | `src/app/` with `src/`                        |
| TypeScript       | `strict: true` only               | Full strict + extra flags                     |
| Tailwind CSS     | v4 (basic)                        | v4 with design token system                   |
| ESLint           | v9 minimal                        | Full flat config                              |
| Components       | None                              | shadcn/ui (Base UI)                           |
| Caching          | Default (no config)               | `cacheComponents: true` (PPR + `'use cache'`) |
| Proxy            | None (`middleware.ts` deprecated) | `proxy.ts` (auth, CSP — Phase 2)              |
| Testing          | None                              | Vitest + Playwright + MSW                     |
| Git hooks        | None                              | Husky + lint-staged                           |
| CI/CD            | None                              | GitHub Actions                                |

---

## 1. Package Manager Migration

**Decision:** npm → pnpm 10

**Rationale:** strict dependency resolution, -60% disk via content-addressable store, enterprise standard (research 04, sec 3).

**Actions:**

1. Delete `package-lock.json` and `node_modules/`
2. Create `.npmrc`:
   ```
   engine-strict=true
   auto-install-peers=true
   strict-peer-dependencies=false
   shamefully-hoist=false
   ```
3. Add to `package.json`:
   ```json
   "packageManager": "pnpm@10.7.0",
   "engines": { "node": ">=22.0.0", "pnpm": ">=10.0.0" }
   ```
4. Run `pnpm install`
5. Enable corepack: `corepack enable && corepack prepare pnpm@10.7.0 --activate`

---

## 2. Project Structure

**Decision:** Hybrid Feature-based + Layer-based architecture (research 01, sec 2.7)

**Rationale:** `src/` separates source from config. Feature modules encapsulate business domains. Shared layers (`components/`, `lib/`, `hooks/`) provide reusable infrastructure. No barrel files (research 04, sec 4.2 — Atlassian: 75% faster builds after removal).

### 2.1 Move to `src/` directory

Move `app/` → `src/app/`. Update `tsconfig.json` paths accordingly.

### 2.2 Target directory structure

```
src/
├── app/                          # Next.js App Router (file-based routing)
│   ├── layout.tsx                # Root layout: <html>, <body>, providers, fonts
│   ├── page.tsx                  # Home page (/)
│   ├── not-found.tsx             # Global 404
│   ├── error.tsx                 # Global error boundary
│   ├── global-error.tsx          # Root layout error boundary
│   ├── globals.css               # Tailwind directives + @theme tokens
│   │
│   ├── (marketing)/              # Route Group: public pages
│   │   └── layout.tsx            # Header + Footer layout
│   ├── (dashboard)/              # Route Group: protected pages
│   │   └── layout.tsx            # Sidebar + Topbar layout
│   ├── (auth)/                   # Route Group: authentication
│   │   └── layout.tsx            # Centered card layout
│   └── api/                      # Route Handlers (uncached by default in Next.js 16)
│       ├── health/route.ts       # Health check endpoint
│       └── webhooks/             # Webhook receivers
│
├── components/                   # Reusable UI components (NO business logic)
│   ├── ui/                       # shadcn/ui primitives (Button, Input, Dialog...)
│   ├── layout/                   # Structural: Header, Sidebar, Footer, Breadcrumbs
│   ├── shared/                   # Composed: PageHeader, EmptyState, ConfirmDialog
│   └── providers/                # Client providers: Theme, QueryClient, Toast
│
├── features/                     # Business feature modules (self-contained)
│   └── [feature-name]/
│       ├── components/           # Feature-specific components
│       ├── hooks/                # Feature-specific hooks
│       ├── actions/              # Server Actions (proxy to backend)
│       ├── api/                  # API client for backend service
│       ├── schemas/              # Zod validation schemas
│       └── types/                # Feature-specific types
│
├── lib/                          # Infrastructure code
│   ├── api-client.ts             # Browser HTTP client (ky)
│   ├── api-server.ts             # Server HTTP client (ky, BFF proxy)
│   ├── query-client.ts           # TanStack Query client factory
│   ├── query-keys.ts             # Query key factory (hierarchical)
│   ├── utils.ts                  # cn() utility
│   └── dal.ts                    # Data Access Layer (auth + proxy)
│
├── hooks/                        # Global custom hooks
├── stores/                       # Zustand stores (client state)
├── schemas/                      # Global Zod schemas (env, pagination, common)
├── types/                        # Global TypeScript types
├── config/                       # App configuration (feature flags, endpoints)
├── constants/                    # Magic values: roles, statuses, limits
└── proxy.ts                      # Next.js Proxy (auth, CSP, rate limit) — renamed from middleware.ts in v16
```

### 2.3 File naming conventions

| Type            | Convention             | Example              |
| --------------- | ---------------------- | -------------------- |
| React component | `kebab-case.tsx`       | `pricing-card.tsx`   |
| React hook      | `use-kebab-case.ts`    | `use-media-query.ts` |
| Server Action   | `kebab-case.ts`        | `create-checkout.ts` |
| Zod schema      | `kebab-case.schema.ts` | `login.schema.ts`    |
| API client      | `kebab-case.client.ts` | `auth.client.ts`     |
| Types           | `kebab-case.types.ts`  | `billing.types.ts`   |
| Test (unit)     | `kebab-case.test.tsx`  | `button.test.tsx`    |
| Test (E2E)      | `kebab-case.spec.ts`   | `auth.spec.ts`       |

### 2.4 Architectural boundaries

Features do NOT import from other features. Components do NOT import from features. Enforced via `eslint-plugin-boundaries`.

```
app/ → can import: everything
features/ → can import: components, hooks, lib, types, config, constants, schemas
            → can import: self (same feature)
            → CANNOT import: other features
components/ → can import: components, hooks, lib, types, config, constants
hooks/ → can import: lib, types, config, constants
lib/ → can import: types, config, constants
types/ → can import: types only
```

### 2.5 Error boundaries & special files

| File               | Purpose                                                                          |
| ------------------ | -------------------------------------------------------------------------------- |
| `error.tsx`        | Route error boundary (`unstable_retry` for recovery — replaces `reset` in v16.2) |
| `global-error.tsx` | Root layout error boundary (must include `<html>`, `<body>`)                     |
| `not-found.tsx`    | 404 page (can be async Server Component)                                         |
| `loading.tsx`      | Suspense fallback per route segment                                              |

> **Note:** `unstable_catchError` from `next/error` enables component-level error boundaries (not tied to route segments). Use for reusable error wrappers inside layouts.

---

## 3. TypeScript Configuration

**Decision:** Progressive strict mode (research 04, sec 1).

Replace current `tsconfig.json`:

```jsonc
{
  "$schema": "https://json-schema.store/tsconfig",
  "compilerOptions": {
    // STRICT MODE
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noImplicitOverride": true,
    "forceConsistentCasingInFileNames": true,

    // MODULE SYSTEM
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "ES2023"],
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "esModuleInterop": true,

    // NEXT.JS
    "jsx": "react-jsx",
    "incremental": true,
    "skipLibCheck": true,
    "noEmit": true,

    // PATH ALIASES
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"],
    },
    "plugins": [{ "name": "next" }],
  },
  "include": [
    "next-env.d.ts",
    "**/*.ts",
    "**/*.tsx",
    ".next/types/**/*.ts",
    ".next/dev/types/**/*.ts",
    "**/*.mts",
  ],
  "exclude": ["node_modules", ".next", "dist", "coverage"],
}
```

**Key changes from default:**

- `target`: ES2017 → ES2022
- `noUncheckedIndexedAccess`: array/object indexing returns `T | undefined`
- `paths`: `@/*` → `./src/*` (not `./*`)

**Deferred to Phase 2:** `verbatimModuleSyntax` (high impact — forces `import type { X }` everywhere, breaks many copy-paste examples from docs and shadcn/ui; add after component library is stable), `exactOptionalPropertyTypes`, `noPropertyAccessFromIndexSignature`

---

## 4. Tailwind CSS v4 Design Tokens

**Decision:** Three-tier token architecture with OKLCH colors (research 03, Part 2).

### 4.1 CSS file structure

```
src/
├── app/
│   └── globals.css               # Entry point: imports + @custom-variant
└── styles/
    └── tokens/
        ├── primitives.css        # Level 1: raw values (colors, scales)
        └── semantic.css          # Level 2: semantic mappings
```

### 4.2 globals.css

```css
@import 'tailwindcss';
@import '../styles/tokens/primitives.css';
@import '../styles/tokens/semantic.css';

@custom-variant dark (&:where([data-theme="dark"], [data-theme="dark"] *));
```

### 4.3 Primitive tokens (primitives.css)

OKLCH color palette (blue-based brand, neutral grays) + spacing (4px grid) + typography scale + shadows + radii. Full set per research 03, Part 2 sec 1.2.

### 4.4 Semantic tokens (semantic.css)

shadcn/ui compatible semantic variables: `--color-background`, `--color-foreground`, `--color-primary`, `--color-primary-foreground`, `--color-secondary`, `--color-muted`, `--color-accent`, `--color-destructive`, `--color-border`, `--color-ring`, `--color-sidebar`, etc.

### 4.5 Dark theme

Overrides in `[data-theme="dark"]` selector (NOT `.dark` class — prevents hydration mismatch per research 03).

---

## 5. shadcn/ui Setup

**Decision:** shadcn/ui with Base UI primitives (research 03, Part 1 sec 4).

**Rationale:** Base UI — single package, active MUI development, built-in multi-select/combobox. shadcn/ui abstracts the primitive layer, so switching is minimal.

### 5.1 Initialization

```bash
pnpm dlx shadcn@latest init
# Primitives: Base UI
# Style: New York
# CSS variables: yes
```

### 5.2 Initial component set (foundation phase)

```bash
pnpm dlx shadcn@latest add button input textarea label select \
  checkbox switch dialog sheet dropdown-menu popover tooltip \
  avatar badge card separator skeleton spinner \
  sidebar breadcrumb tabs command \
  sonner scroll-area collapsible \
  form table
```

### 5.3 cn() utility

```typescript
// src/lib/utils.ts
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

---

## 6. ESLint v9 + Prettier

**Decision:** ESLint v9 flat config + typescript-eslint v8 + Prettier with tailwind plugin (research 04, sec 2-3).

### 6.1 ESLint (eslint.config.mjs)

Plugins:

- `typescript-eslint` (v8, `projectService`)
- `eslint-plugin-import-x` (import ordering, no-cycle)
- `eslint-plugin-boundaries` (architecture enforcement)
- `eslint-plugin-react-hooks`
- `eslint-plugin-jsx-a11y`
- `eslint-config-prettier` (conflict resolution, LAST in chain)
- `eslint-config-next` (Next.js specific rules via compat)

Key rules:

- `@typescript-eslint/consistent-type-imports`: warn
- `@typescript-eslint/no-floating-promises`: error
- `@typescript-eslint/no-explicit-any`: error
- `import-x/order`: enforced group ordering with newlines
- `import-x/no-cycle`: error (maxDepth: 4)
- `boundaries/dependencies`: feature isolation per sec 2.4

### 6.2 Prettier (.prettierrc)

```json
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "all",
  "printWidth": 100,
  "bracketSpacing": true,
  "arrowParens": "always",
  "endOfLine": "lf",
  "plugins": ["prettier-plugin-tailwindcss"],
  "tailwindFunctions": ["cn", "cva", "clsx", "twMerge"]
}
```

---

## 7. Environment Variables

**Decision:** `@t3-oss/env-nextjs` + Zod (research 04, Part 3 sec 2).

### 7.1 src/env.ts

Type-safe env validation with server/client separation. Fails at startup, not runtime.

Server vars: `API_BASE_URL`, `AUTH_SERVICE_URL`, `AUTH_SECRET`, `NODE_ENV`
Client vars: `NEXT_PUBLIC_APP_URL`

### 7.2 .env files

```
.env.example          # Template with empty values (committed)
.env.local            # Local secrets (gitignored)
```

---

## 8. Next.js Configuration & Caching

**Decision:** Enable `cacheComponents` for the new caching model with PPR (Next.js 16 breaking change).

**Rationale:** Next.js 16 replaces automatic `fetch` caching with an explicit `'use cache'` directive model. Route Handlers are uncached by default. This is the single most impactful architectural change in v16.

### 8.1 next.config.ts

```typescript
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  cacheComponents: true, // enables 'use cache', PPR, <Activity>
};

export default nextConfig;
```

`cacheComponents: true` enables:

- `'use cache'` directive (function, component, or file level)
- `cacheLife()` for cache duration profiles
- `cacheTag()` for tag-based invalidation
- Partial Prerendering (PPR) — static shell + streamed dynamic content
- React `<Activity>` component for navigation state preservation

### 8.2 Caching patterns

| Pattern            | How                                                       | When                                                      |
| ------------------ | --------------------------------------------------------- | --------------------------------------------------------- |
| Cache a function   | `'use cache'` + `cacheLife('hours')` at function body top | API proxy helpers, data fetching                          |
| Cache a component  | `'use cache'` at component body top                       | Static sections of pages                                  |
| Cache a file       | `'use cache'` at file top                                 | Utility modules with cacheable exports                    |
| Uncached (dynamic) | Wrap in `<Suspense>` — NO `'use cache'`                   | Components using `cookies()`, `headers()`, `searchParams` |

### 8.3 Suspense requirement (critical constraint)

Components accessing runtime APIs (`cookies()`, `headers()`, `searchParams`, `params`) **MUST** be wrapped in `<Suspense>`. Without this, build fails:

> `"Uncached data was accessed outside of <Suspense>"`

This affects layout and page architecture. Push dynamic data access into leaf components wrapped in `<Suspense>`, keep layouts static.

### 8.4 Route Handlers

Route Handlers are **uncached by default** in Next.js 16. To cache a GET handler: `export const dynamic = 'force-static'`.

Use `RouteContext` helper type for typed params:

```typescript
import type { NextRequest } from 'next/server';
import type { RouteContext } from 'next/server';

export async function GET(_req: NextRequest, ctx: RouteContext<'/api/users/[id]'>) {
  const { id } = await ctx.params;
  return Response.json({ id });
}
```

Types are auto-generated during `next dev`, `next build`, or `next typegen`.

### 8.5 Proxy (formerly Middleware)

Next.js 16.0.0 renamed `middleware.ts` → `proxy.ts`:

- Export: `export function proxy(request: NextRequest) { ... }`
- Type: `NextProxy` available for shorthand typing
- Runtime: **Node.js by default** (stable since v15.5.0 — no longer Edge-only)
- Location: `src/proxy.ts` (inside `src/` when using src directory)
- Codemod: `npx @next/codemod@canary middleware-to-proxy .`

> **Security:** Never rely on Proxy alone for auth — always verify inside Server Functions too.

### 8.6 Deferred caching features (Phase 2+)

- `cacheHandlers`: custom cache storage (Redis) with distributed tag coordination
- Named cache profiles: `'use cache: remote'`, `'use cache: sessions'`
- `deploymentId` config for cross-deployment cache coordination

---

## 9. Git Hooks

**Decision:** Husky v9 + lint-staged + commitlint (research 04, Part 2 sec 1).

### 9.1 Hooks

| Hook         | Action                            |
| ------------ | --------------------------------- |
| `pre-commit` | `lint-staged` (ESLint + Prettier) |
| `commit-msg` | `commitlint` (conventional)       |
| `pre-push`   | `pnpm typecheck`                  |

### 9.2 lint-staged config

```json
{
  "*.{ts,tsx}": ["eslint --fix --max-warnings=0", "prettier --write"],
  "*.{json,md,yml,yaml}": ["prettier --write"],
  "*.css": ["prettier --write"]
}
```

### 9.3 commitlint config

Conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`, `ci:`, `perf:`, `style:`.
Subject max length: 72. No trailing period.

---

## 10. Testing Infrastructure

**Decision:** Vitest (unit/integration) + Playwright (E2E) + MSW v2 (API mocking) (research 04, Part 2 sec 2-5).

### 10.1 Vitest

Config: `vitest.config.ts`

- Environment: jsdom
- Setup: `vitest.setup.ts` (jest-dom, Next.js router mock, MSW server)
- Coverage: v8 provider, 80% thresholds (branches, functions, lines, statements)
- Include: `src/**/*.{test,spec}.{ts,tsx}`
- Colocation: tests next to source files (`button.test.tsx` beside `button.tsx`)

### 10.2 Playwright

Config: `playwright.config.ts`

- Projects: chromium (required), firefox, webkit, mobile-chrome
- Auth setup: shared `storageState` across projects
- WebServer: `pnpm build && pnpm start` (production build, NOT dev)
- Test dir: `e2e/` in root
- Artifacts: trace on first retry, screenshot on failure

### 10.3 MSW v2

Structure:

```
src/mocks/
├── handlers/
│   └── index.ts
├── browser.ts        # setupWorker (dev)
├── server.ts         # setupServer (Vitest)
└── index.ts          # Conditional init
```

MSW handlers mock backend API endpoints. Server Actions tested directly in Vitest (mock `apiServer`).

### 10.4 Testing strategy

| Layer             | Tool                | Approach                       |
| ----------------- | ------------------- | ------------------------------ |
| Utils, helpers    | Vitest              | Pure function tests            |
| Zod schemas       | Vitest              | Valid/invalid input            |
| Server Actions    | Vitest + mock api   | Mock `apiServer`, test logic   |
| Custom hooks      | Vitest + renderHook | Behavior testing               |
| Client Components | Vitest + RTL        | User interaction testing       |
| Async RSC (pages) | Playwright          | Full page rendering            |
| User flows        | Playwright          | Registration, CRUD, navigation |

---

## 11. Core Libraries

### 11.1 Server state: TanStack Query v5

- `@tanstack/react-query` + `@tanstack/react-query-devtools`
- QueryClient factory: singleton on client, new per request on server
- Default `staleTime: 60_000`, `gcTime: 5 * 60_000`
- `refetchOnWindowFocus: false`
- Provider in `src/components/providers/query-provider.tsx`

### 11.2 Client state: Zustand v5

- `zustand` + `zustand/middleware` (devtools, persist, immer)
- Separate stores by domain: `ui-store.ts`, `auth-store.ts`
- `createSelectors` pattern for auto-generated selectors
- SSR-safe hydration via `useStoreHydration` hook

### 11.3 Forms: React Hook Form + Zod

- `react-hook-form` + `@hookform/resolvers`
- `zod` for shared validation (client + server)
- One schema → used in Server Action validation + form resolver + TypeScript inference

### 11.4 HTTP client: ky

- `ky` — lightweight, hooks (beforeRequest, afterResponse), timeout, retry
- Two instances: `api-client.ts` (browser), `api-server.ts` (server/BFF proxy)

### 11.5 Icons: Lucide React

- `lucide-react` — 1500+ icons, tree-shakeable, shadcn/ui standard
- Named imports only, NEVER `import * as Icons`

### 11.6 Theme: next-themes

- `next-themes` — `attribute="data-theme"`, `defaultTheme="system"`, `enableSystem`
- Prevents hydration mismatch (data-attribute, not class)

### 11.7 Animations: Motion

- `motion` (ex Framer Motion) — AnimatePresence, layout animations, gestures
- `tailwindcss-motion` — CSS-only animations for Server Components

### 11.8 Fonts: next/font

- `Geist` (sans) + `Geist_Mono` (monospace) — Next.js 16 default
- CSS variables: `--font-geist-sans`, `--font-geist-mono`
- Integration with Tailwind v4 `@theme`

---

## 12. npm Scripts

```json
{
  "dev": "next dev --turbopack",
  "build": "next build",
  "start": "next start",
  "lint": "eslint .",
  "lint:fix": "eslint . --fix",
  "format": "prettier --write .",
  "format:check": "prettier --check .",
  "typecheck": "tsc --noEmit",
  "test": "vitest",
  "test:run": "vitest run",
  "test:coverage": "vitest run --coverage",
  "test:e2e": "playwright test",
  "test:e2e:ui": "playwright test --ui",
  "test:e2e:install": "playwright install --with-deps",
  "generate": "plop",
  "generate:component": "plop component",
  "generate:hook": "plop hook",
  "generate:action": "plop action",
  "typegen": "next typegen",
  "analyze": "ANALYZE=true next build",
  "clean": "rm -rf .next node_modules/.cache",
  "prepare": "husky"
}
```

---

## 13. CI/CD Pipeline

**Decision:** GitHub Actions, fan-out/fan-in strategy (research 04, Part 3 sec 1).

### 13.1 Workflow: `.github/workflows/ci.yml`

```
Trigger: push to main/develop, pull_request to main/develop
Concurrency: cancel-in-progress per branch

Jobs:
  install → cache pnpm + node_modules + .next/cache
    ↓
  lint        (parallel) — eslint + prettier check
  typecheck   (parallel) — tsc --noEmit
  test-unit   (parallel) — vitest run --coverage
  test-e2e    (parallel) — playwright test (chromium only)
    ↓
  build       (after lint + typecheck + test-unit) — next build
```

### 13.2 Key optimizations

- `concurrency.cancel-in-progress` — saves 30-40% CI minutes
- `pnpm/action-setup@v4` + `cache: 'pnpm'` — install ~40s with warm cache
- `--frozen-lockfile` — reproducible installs
- Playwright installs only chromium in CI

---

## 14. Code Generation (Plop.js)

**Decision:** Plop.js with TypeScript plopfile (research 04, Part 3 sec 5).

### 14.1 Generators

| Generator   | Creates                            |
| ----------- | ---------------------------------- |
| `component` | `.tsx` + `.test.tsx` in target dir |
| `hook`      | `use-*.ts` + `use-*.test.ts`       |
| `action`    | Server Action with Zod schema      |
| `feature`   | Full feature module scaffold       |

### 14.2 Templates directory

```
templates/
├── component.tsx.hbs
├── component.test.tsx.hbs
├── hook.ts.hbs
├── hook.test.ts.hbs
├── server-action.ts.hbs
└── feature/
    ├── components/.gitkeep.hbs
    ├── hooks/.gitkeep.hbs
    ├── actions/.gitkeep.hbs
    ├── schemas/.gitkeep.hbs
    └── types/.gitkeep.hbs
```

---

## 15. Out of Scope (Phase 2+)

These items are researched but NOT part of the foundation phase:

| Item                               | Phase | Reason                                                                |
| ---------------------------------- | ----- | --------------------------------------------------------------------- |
| Auth.js v5 setup                   | 2     | Requires auth backend service ready                                   |
| Proxy guards (auth/CSP/RBAC)       | 2     | Depends on auth implementation                                        |
| `forbidden.js` / `unauthorized.js` | 2     | Experimental file conventions for 403/401 — pairs with Auth.js + RBAC |
| `verbatimModuleSyntax`             | 2     | High impact — add after shadcn/ui is stable                           |
| `cacheHandlers` (Redis)            | 2     | Custom distributed cache storage                                      |
| next-intl (i18n)                   | 2     | Adds `[locale]` segment complexity                                    |
| Sentry                             | 2     | Needs DSN and org setup                                               |
| OpenTelemetry                      | 2     | Infrastructure dependency                                             |
| Storybook                          | 2     | After component library stabilizes                                    |
| Chromatic visual testing           | 2     | After Storybook                                                       |
| Recharts / Tremor                  | 2     | When dashboard pages are built                                        |
| TanStack Table                     | 2     | When data table pages are built                                       |
| Rate limiting (Upstash)            | 2     | Needs Redis instance                                                  |
| Monorepo (Turborepo)               | 3     | Only if 2+ applications emerge                                        |
| SEO (sitemap, robots, OG)          | 2     | When public pages are built                                           |
| `global-not-found.js`              | 2     | Experimental — for multi-root-layout apps                             |
| Real-time (SSE/WebSocket)          | 3     | When real-time features are needed                                    |
| Feature flags                      | 3     | When A/B testing is needed                                            |

---

## Appendix A: Full Dependency List

### Production dependencies

```
next                          # 16.2.2 (keep)
react                         # 19.2.4 (keep)
react-dom                     # 19.2.4 (keep)
@tanstack/react-query         # Server state management
zustand                       # Client state management
immer                         # Immutable updates for Zustand
react-hook-form               # Form management
@hookform/resolvers           # Zod resolver for RHF
zod                           # Validation (client + server)
ky                            # HTTP client
next-themes                   # Dark/light/system theme
motion                        # Animations (ex Framer Motion)
lucide-react                  # Icons (1500+, tree-shakeable)
sonner                        # Toast notifications
@t3-oss/env-nextjs            # Type-safe env variables
class-variance-authority      # Component variants (cva)
clsx                          # Conditional classes
tailwind-merge                # Tailwind class conflict resolution
```

### Development dependencies

```
# Already installed (keep)
tailwindcss                   # ^4
@tailwindcss/postcss          # ^4
typescript                    # ^5
eslint                        # ^9
@types/node                   # ^20
@types/react                  # ^19
@types/react-dom              # ^19

# ESLint ecosystem
eslint-config-next            # Keep (16.2.2) — exports flat config natively
@eslint/js                    # Base recommended
typescript-eslint             # v8, parser + plugin
eslint-plugin-import-x        # Import ordering, no-cycle
eslint-import-resolver-typescript
eslint-plugin-boundaries      # Architecture enforcement
eslint-plugin-react-hooks     # Hooks rules
eslint-plugin-jsx-a11y        # Accessibility
eslint-config-prettier        # Disable conflicting rules

# Prettier
prettier
prettier-plugin-tailwindcss   # Class sorting

# Git hooks
husky                         # Git hooks manager
lint-staged                   # Lint only staged files
@commitlint/cli               # Commit message validation
@commitlint/config-conventional

# Testing
vitest                        # Unit/integration test runner
@vitejs/plugin-react          # React support for Vitest
vite-tsconfig-paths            # Path alias support
@testing-library/react        # Component testing
@testing-library/dom
@testing-library/jest-dom      # DOM matchers
@testing-library/user-event    # User interaction simulation
jsdom                         # Browser environment for Vitest
msw                           # API mocking
@playwright/test              # E2E testing

# TanStack Query devtools
@tanstack/react-query-devtools

# Animation plugin
tailwindcss-motion            # CSS-only animations

# Code generation
plop                          # Scaffolding generator

# Bundle analysis (choose one based on bundler)
@next/bundle-analyzer         # Webpack mode bundle visualization
# Note: Turbopack has built-in analyzer — @next/bundle-analyzer may not work with --turbopack
```

---

## Appendix B: File Tree After Setup

```
new/
├── .github/
│   └── workflows/
│       └── ci.yml
├── .husky/
│   ├── pre-commit
│   ├── commit-msg
│   └── pre-push
├── docs/
│   ├── research/             # Existing research documents
│   └── SPEC.md               # This file
├── e2e/                      # Playwright E2E tests
│   ├── fixtures/
│   └── example.spec.ts
├── public/
│   └── favicon.ico
├── src/
│   ├── app/
│   │   ├── (auth)/
│   │   │   └── layout.tsx
│   │   ├── (dashboard)/
│   │   │   └── layout.tsx
│   │   ├── (marketing)/
│   │   │   └── layout.tsx
│   │   ├── api/
│   │   │   └── health/
│   │   │       └── route.ts
│   │   ├── globals.css
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── not-found.tsx
│   │   ├── error.tsx
│   │   └── global-error.tsx
│   ├── components/
│   │   ├── ui/               # shadcn/ui components
│   │   ├── layout/
│   │   ├── shared/
│   │   └── providers/
│   │       ├── theme-provider.tsx
│   │       ├── query-provider.tsx
│   │       └── toast-provider.tsx
│   ├── features/             # Business feature modules (empty initially)
│   ├── hooks/
│   ├── lib/
│   │   ├── api-client.ts
│   │   ├── api-server.ts
│   │   ├── query-client.ts
│   │   ├── query-keys.ts
│   │   └── utils.ts
│   ├── stores/
│   │   └── ui-store.ts
│   ├── schemas/
│   ├── types/
│   ├── config/
│   ├── constants/
│   ├── styles/
│   │   └── tokens/
│   │       ├── primitives.css
│   │       └── semantic.css
│   ├── mocks/
│   │   ├── handlers/
│   │   │   └── index.ts
│   │   ├── browser.ts
│   │   └── server.ts
│   ├── env.ts
│   └── proxy.ts
├── templates/                # Plop.js templates
│   ├── component.tsx.hbs
│   ├── component.test.tsx.hbs
│   ├── hook.ts.hbs
│   ├── hook.test.ts.hbs
│   └── server-action.ts.hbs
├── .env.example
├── .gitignore                # Must include next-env.d.ts (Next.js 16 recommendation)
├── .npmrc
├── .prettierrc
├── .prettierignore
├── commitlint.config.js
├── components.json           # shadcn/ui config
├── eslint.config.mjs
├── next.config.ts
├── package.json
├── playwright.config.ts
├── plopfile.ts
├── pnpm-lock.yaml
├── postcss.config.mjs
├── tsconfig.json
├── vitest.config.ts
└── vitest.setup.ts
```
