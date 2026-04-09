# Consolidate auth module into `src/features/auth/`

## Context

Auth code is scattered across 4 directories (`features/auth/`, `stores/`, `types/`, `lib/auth/`) while the project's Feature Sliced Design (demonstrated by `features/telegram/`) calls for self-contained features. The empty scaffold dirs (`api/`, `hooks/`, `types/`) inside `features/auth/` confirm this was the intended structure. This refactor moves all auth-related code into a single feature module.

## Target structure

```
src/features/auth/
  index.ts                          # barrel (client-safe exports)
  types.ts                          # from src/types/auth.ts
  store.ts                          # from src/stores/auth-store.ts
  lib/
    debug.ts                        # from src/lib/auth/debug.ts
    events.ts                       # from src/lib/auth/events.ts
    cookies.ts                      # from src/lib/auth/cookies.ts
    cookie-helpers.ts               # from src/lib/auth/cookie-helpers.ts
  components/
    telegram-auth-bootstrap.tsx     # stays, default→named export
```

Empty scaffold dirs `api/`, `hooks/`, `types/` are removed (recreate when needed).

## Barrel design (`index.ts`)

Exports client-safe public API only:
- Types: `AuthProvider`, `AuthStatus`, `TokenPair`, `Identity`, `Session`, `TelegramAuthResponse`
- Store: `useAuthStore`
- Component: `TelegramAuthBootstrap` (named export)
- Lib: `isBrowserDebugAuthEnabled`, `getBrowserDebugUser`, `getBrowserDebugTelegramUser`, `BrowserDebugUser`, `emitAuthExpired`, `onAuthExpired`, `ACCESS_COOKIE`, `REFRESH_COOKIE`, `logout`

Server-side routes import directly from `@/features/auth/lib/cookie-helpers` — no server barrel needed (`cookie-helpers.ts` uses `type NextResponse` which is stripped at compile time, but the functions themselves are server-only by usage).

## Step-by-step

### Phase 1: Create new files (6 files)

1. **`src/features/auth/types.ts`** — copy verbatim from `src/types/auth.ts`
2. **`src/features/auth/store.ts`** — copy from `src/stores/auth-store.ts`, change import `@/types/auth` → `./types`
3. **`src/features/auth/lib/debug.ts`** — copy verbatim from `src/lib/auth/debug.ts`
4. **`src/features/auth/lib/events.ts`** — copy verbatim from `src/lib/auth/events.ts`
5. **`src/features/auth/lib/cookies.ts`** — copy verbatim from `src/lib/auth/cookies.ts`
6. **`src/features/auth/lib/cookie-helpers.ts`** — copy verbatim from `src/lib/auth/cookie-helpers.ts` (internal `./cookies` import stays valid)

### Phase 2: Update component (1 file)

7. **`src/features/auth/components/telegram-auth-bootstrap.tsx`**:
   - `@/lib/auth/debug` → `../lib/debug`
   - `@/lib/auth/events` → `../lib/events`
   - `@/stores/auth-store` → `../store`
   - `@/types/auth` → `../types`
   - `export default function` → `export function` (named export)

### Phase 3: Rewrite barrel (1 file)

8. **`src/features/auth/index.ts`** — comprehensive barrel with organized sections

### Phase 4: Update external consumers (8 files)

9. **`src/features/telegram/provider.tsx`**: `@/lib/auth/debug` → `@/features/auth`
10. **`src/features/telegram/components/telegram-environment-alert.tsx`**: `@/lib/auth/debug` → `@/features/auth`
11. **`src/lib/api-client.ts`**: `@/lib/auth/events` → `@/features/auth`
12. **`src/app/api/auth/telegram/route.ts`**: `@/lib/auth/cookie-helpers` → `@/features/auth/lib/cookie-helpers`, `@/lib/auth/debug` → `@/features/auth/lib/debug`
13. **`src/app/api/auth/logout/route.ts`**: `@/lib/auth/cookie-helpers` → `@/features/auth/lib/cookie-helpers`
14. **`src/app/api/auth/refresh/route.ts`**: `@/lib/auth/cookie-helpers` → `@/features/auth/lib/cookie-helpers`
15. **`src/app/api/backend/[...path]/route.ts`**: `@/lib/auth/cookie-helpers` → `@/features/auth/lib/cookie-helpers`
16. **`src/types/index.ts`**: remove line `export type * from "./auth"`

Note: `src/components/providers/telegram-provider.tsx` — NO change needed (already imports from `@/features/auth`).

### Phase 5: Delete old files (6 files + 1 dir + 3 empty dirs)

17. Delete `src/types/auth.ts`
18. Delete `src/stores/auth-store.ts`
19. Delete `src/lib/auth/debug.ts`
20. Delete `src/lib/auth/events.ts`
21. Delete `src/lib/auth/cookies.ts`
22. Delete `src/lib/auth/cookie-helpers.ts`
23. Delete `src/lib/auth/` directory
24. Delete empty dirs: `src/features/auth/api/`, `src/features/auth/hooks/`, `src/features/auth/types/`

## Verification

1. `grep -r '@/lib/auth/' src/` — should return 0 matches
2. `grep -r '@/stores/auth-store' src/` — should return 0 matches
3. `grep -r '@/types/auth' src/` — should return 0 matches
4. `pnpm tsc --noEmit` — should pass
5. `pnpm build` — should succeed (catches server/client boundary violations)
