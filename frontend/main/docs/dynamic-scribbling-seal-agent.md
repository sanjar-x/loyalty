# Auth Consolidation Plan: Feature Sliced Design

## Goal

Move all auth-related code scattered across `src/lib/auth/`, `src/stores/auth-store.ts`,
and `src/types/auth.ts` into `src/features/auth/`, following the self-contained feature
pattern established by `src/features/telegram/`.

---

## Target Directory Structure

```
src/features/auth/
├── index.ts                          # public barrel (client-safe exports only)
├── server.ts                         # server-only barrel (cookie-helpers, server utils)
├── types.ts                          # all auth types (moved from src/types/auth.ts)
├── store.ts                          # Zustand store (moved from src/stores/auth-store.ts)
├── lib/
│   ├── debug.ts                      # moved from src/lib/auth/debug.ts
│   ├── events.ts                     # moved from src/lib/auth/events.ts
│   ├── cookies.ts                    # moved from src/lib/auth/cookies.ts
│   └── cookie-helpers.ts             # moved from src/lib/auth/cookie-helpers.ts
├── components/
│   └── telegram-auth-bootstrap.tsx   # existing, updated imports + named export
├── api/                              # (empty scaffold - keep for future use)
└── hooks/                            # (empty scaffold - keep for future use)
```

### Key Design Decisions

**1. Two barrels (`index.ts` + `server.ts`) instead of one.**

The critical constraint: server-side route handlers cannot safely import a barrel
that re-exports `'use client'` modules. `cookie-helpers.ts` imports `NextResponse`
(server-only). Mixing it in the same barrel with `'use client'` store/component
exports would break. Solution:

- `index.ts` — exports types, store, debug, events, cookies, component (all client-safe)
- `server.ts` — exports cookie-helpers + re-exports cookie constants (server-only consumers)

This follows Next.js conventions: features that span client/server use separate entry points.

**2. `lib/` subfolder for utility modules.**

The 4 files from `src/lib/auth/` are not hooks, components, or API query layers. They are
internal implementation utilities. Placing them in `lib/` within the feature preserves their
nature while keeping the feature self-contained.

**3. `types.ts` at feature root (matching telegram feature pattern).**

The telegram feature has `types.ts` at its root. Auth follows the same convention.

**4. `store.ts` at feature root.**

No existing feature keeps stores locally yet, but the empty scaffold directories in
`src/features/auth/` signal intended consolidation. The telegram feature is fully
self-contained; auth should follow suit. The store has only one consumer file outside
auth (`telegram-auth-bootstrap.tsx` — which IS inside auth), so this is clean.

---

## Step-by-Step Implementation

### Phase 1: Create new files in target locations (6 operations)

#### 1.1 Create `src/features/auth/types.ts`
- Copy contents of `src/types/auth.ts` verbatim (all 6 type exports)
- No import changes needed (it has no imports)

#### 1.2 Create `src/features/auth/store.ts`
- Copy contents of `src/stores/auth-store.ts`
- Change import: `import type { AuthStatus } from '@/types/auth'` → `import type { AuthStatus } from './types'`
- Keep `'use client'` directive

#### 1.3 Create `src/features/auth/lib/debug.ts`
- Copy contents of `src/lib/auth/debug.ts` verbatim (no import changes needed — it has no external imports)

#### 1.4 Create `src/features/auth/lib/events.ts`
- Copy contents of `src/lib/auth/events.ts` verbatim (no import changes needed)

#### 1.5 Create `src/features/auth/lib/cookies.ts`
- Copy contents of `src/lib/auth/cookies.ts` verbatim (no import changes needed)

#### 1.6 Create `src/features/auth/lib/cookie-helpers.ts`
- Copy contents of `src/lib/auth/cookie-helpers.ts`
- Change internal import: `import { ACCESS_COOKIE, REFRESH_COOKIE } from "./cookies"` → `import { ACCESS_COOKIE, REFRESH_COOKIE } from './cookies'` (same — relative path still works since both files move together into `lib/`)

### Phase 2: Update the component (1 operation)

#### 2.1 Update `src/features/auth/components/telegram-auth-bootstrap.tsx`
- Change to named export: `export default function` → `export function`
- Update imports:
  - `from '@/lib/auth/debug'`        → `from '../lib/debug'`
  - `from '@/lib/auth/events'`       → `from '../lib/events'`
  - `from '@/stores/auth-store'`     → `from '../store'`
  - `from '@/types/auth'`            → `from '../types'`

### Phase 3: Write the two barrel files (2 operations)

#### 3.1 Rewrite `src/features/auth/index.ts`

```ts
// =============================================================================
// Barrel export — features/auth (client-safe)
// =============================================================================

// Types
export type {
  AuthProvider,
  AuthStatus,
  TokenPair,
  Identity,
  Session,
  TelegramAuthResponse,
} from './types';

// Store
export { useAuthStore } from './store';

// Lib — debug
export {
  isBrowserDebugAuthEnabled,
  getBrowserDebugUser,
  getBrowserDebugTelegramUser,
  normalizeBrowserDebugUser,
} from './lib/debug';
export type { BrowserDebugUser } from './lib/debug';

// Lib — events
export { emitAuthExpired, onAuthExpired } from './lib/events';

// Lib — cookies (client-safe: constants + logout fn)
export { ACCESS_COOKIE, REFRESH_COOKIE, logout } from './lib/cookies';

// Components
export { TelegramAuthBootstrap } from './components/telegram-auth-bootstrap';
```

#### 3.2 Create `src/features/auth/server.ts`

```ts
// =============================================================================
// Server-only barrel — features/auth
// Use this import path in route handlers: `@/features/auth/server`
// =============================================================================

export {
  ACCESS_COOKIE,
  REFRESH_COOKIE,
  getBackendBaseUrl,
  isProduction,
  shouldSecureCookie,
  getCookieDomain,
  serializeCookie,
  clearCookieHeader,
  setTokenCookies,
  clearTokenCookies,
} from './lib/cookie-helpers';

// Re-export debug utilities (used by telegram route handler)
export {
  isBrowserDebugAuthEnabled,
  normalizeBrowserDebugUser,
} from './lib/debug';
```

### Phase 4: Update external consumers (7 import rewrites)

#### 4.1 `src/features/telegram/provider.tsx` (lines 13-15)
```diff
- import {
-   isBrowserDebugAuthEnabled,
-   getBrowserDebugTelegramUser,
- } from '@/lib/auth/debug';
+ import {
+   isBrowserDebugAuthEnabled,
+   getBrowserDebugTelegramUser,
+ } from '@/features/auth';
```

#### 4.2 `src/features/telegram/components/telegram-environment-alert.tsx` (line 5)
```diff
- import { isBrowserDebugAuthEnabled } from '@/lib/auth/debug';
+ import { isBrowserDebugAuthEnabled } from '@/features/auth';
```

#### 4.3 `src/lib/api-client.ts` (line 3)
```diff
- import { emitAuthExpired } from "@/lib/auth/events";
+ import { emitAuthExpired } from "@/features/auth";
```

#### 4.4 `src/app/api/auth/telegram/route.ts` (lines 3-11)
```diff
- import {
-   getBackendBaseUrl,
-   isProduction,
-   setTokenCookies,
- } from "@/lib/auth/cookie-helpers";
- import {
-   isBrowserDebugAuthEnabled,
-   normalizeBrowserDebugUser,
- } from "@/lib/auth/debug";
+ import {
+   getBackendBaseUrl,
+   isProduction,
+   setTokenCookies,
+   isBrowserDebugAuthEnabled,
+   normalizeBrowserDebugUser,
+ } from "@/features/auth/server";
```

#### 4.5 `src/app/api/auth/logout/route.ts` (lines 3-7)
```diff
- import {
-   ACCESS_COOKIE,
-   getBackendBaseUrl,
-   clearTokenCookies,
- } from "@/lib/auth/cookie-helpers";
+ import {
+   ACCESS_COOKIE,
+   getBackendBaseUrl,
+   clearTokenCookies,
+ } from "@/features/auth/server";
```

#### 4.6 `src/app/api/auth/refresh/route.ts` (lines 3-8)
```diff
- import {
-   REFRESH_COOKIE,
-   getBackendBaseUrl,
-   setTokenCookies,
-   clearTokenCookies,
- } from "@/lib/auth/cookie-helpers";
+ import {
+   REFRESH_COOKIE,
+   getBackendBaseUrl,
+   setTokenCookies,
+   clearTokenCookies,
+ } from "@/features/auth/server";
```

#### 4.7 `src/app/api/backend/[...path]/route.ts` (line 4)
```diff
- import { ACCESS_COOKIE, getBackendBaseUrl } from "@/lib/auth/cookie-helpers";
+ import { ACCESS_COOKIE, getBackendBaseUrl } from "@/features/auth/server";
```

### Phase 5: Remove stale re-export (1 operation)

#### 5.1 Update `src/types/index.ts` (line 2)
- Remove: `export type * from "./auth"`
- Confirmed: no consumer imports auth types via `@/types` barrel (all use `@/types/auth` directly, and those 2 consumers are within the auth feature itself)

### Phase 6: Delete old files (5 operations)

#### 6.1 Delete `src/types/auth.ts`
#### 6.2 Delete `src/stores/auth-store.ts`
#### 6.3 Delete `src/lib/auth/debug.ts`
#### 6.4 Delete `src/lib/auth/events.ts`
#### 6.5 Delete `src/lib/auth/cookies.ts`
#### 6.6 Delete `src/lib/auth/cookie-helpers.ts`
#### 6.7 Delete `src/lib/auth/` directory (now empty)

### Phase 7: Remove empty scaffold `types/` directory

#### 7.1 Delete `src/features/auth/types/` directory
- Types now live in `src/features/auth/types.ts` (file at root, not dir)
- The empty directory would be confusing alongside the file

---

## Import Map Summary (Before → After)

| Consumer | Old import | New import |
|---|---|---|
| `telegram/provider.tsx` | `@/lib/auth/debug` | `@/features/auth` |
| `telegram/.../telegram-environment-alert.tsx` | `@/lib/auth/debug` | `@/features/auth` |
| `lib/api-client.ts` | `@/lib/auth/events` | `@/features/auth` |
| `components/providers/telegram-provider.tsx` | `@/features/auth` | `@/features/auth` (no change) |
| `app/api/auth/telegram/route.ts` | `@/lib/auth/cookie-helpers` + `@/lib/auth/debug` | `@/features/auth/server` |
| `app/api/auth/logout/route.ts` | `@/lib/auth/cookie-helpers` | `@/features/auth/server` |
| `app/api/auth/refresh/route.ts` | `@/lib/auth/cookie-helpers` | `@/features/auth/server` |
| `app/api/backend/[...path]/route.ts` | `@/lib/auth/cookie-helpers` | `@/features/auth/server` |
| `types/index.ts` | `export type * from "./auth"` | removed |

## Risk Assessment

**Low risk:**
- All changes are pure refactors (move + re-path). No logic changes.
- The server/client split is the only architectural decision, and it directly mirrors the existing split (`cookie-helpers.ts` was always server-only, never imported by client code).

**Verify after implementation:**
- `npx tsc --noEmit` — type-check passes
- `npx next build` — build succeeds (catches any server/client boundary violations)
- Grep for any remaining `@/lib/auth/` or `@/stores/auth-store` or `@/types/auth` imports — should find zero

## File Operations Count
- **Create:** 6 files (types.ts, store.ts, lib/debug.ts, lib/events.ts, lib/cookies.ts, lib/cookie-helpers.ts) + 1 (server.ts) = 7
- **Rewrite:** 2 files (index.ts, telegram-auth-bootstrap.tsx)
- **Edit imports:** 5 files (4 route handlers + api-client + 2 telegram files = 7 edits in 6 files... wait let me recount)
  - telegram/provider.tsx — edit
  - telegram/components/telegram-environment-alert.tsx — edit
  - lib/api-client.ts — edit
  - app/api/auth/telegram/route.ts — edit
  - app/api/auth/logout/route.ts — edit
  - app/api/auth/refresh/route.ts — edit
  - app/api/backend/[...path]/route.ts — edit
  - types/index.ts — edit (remove 1 line)
  Total: 8 external file edits
- **Delete:** 5 files + 1 empty dir + 1 empty scaffold dir = 7 deletions

**Grand total: 24 discrete file operations**
