# Telegram Mini App ↔ IAM Auth Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the frontend Telegram Mini App to the backend IAM Multi-Provider Auth system — replacing the legacy `/api/v1/users/init/` call with the new `POST /auth/telegram` endpoint, implementing token pair management (access + refresh), Redux auth state, automatic token refresh with retry, and Next.js middleware route protection.

**Architecture:** The frontend is a Next.js 16 App Router application running as a Telegram Mini App. Authentication flows through a server-side Next.js API route (`/api/session/telegram/init`) that acts as a BFF (Backend-for-Frontend) proxy — it receives raw `initData` from the client, forwards it to the FastAPI backend via `Authorization: tma <initData>` header, and stores the returned token pair in httpOnly cookies. The client never sees raw tokens. RTK Query handles all API communication with automatic 401 → refresh → retry logic.

**Tech Stack:** Next.js 16.1 (App Router), React 19, Redux Toolkit 2.11 + RTK Query, TypeScript 5.x, Telegram WebApp SDK (vanilla `window.Telegram.WebApp`)

**Backend contract (already implemented):**

| Method | Endpoint | Auth Header | Request Body | Response (camelCase) |
|--------|----------|-------------|-------------|---------------------|
| POST | `/api/v1/auth/telegram` | `Authorization: tma <raw_initData>` | — | `{ accessToken, refreshToken, tokenType, isNewUser }` |
| POST | `/api/v1/auth/refresh` | — | `{ refreshToken }` | `{ accessToken, refreshToken, tokenType }` |
| POST | `/api/v1/auth/logout` | `Authorization: Bearer <JWT>` | — | `{ message }` |
| POST | `/api/v1/auth/logout/all` | `Authorization: Bearer <JWT>` | — | `{ message }` |

**Terminology:**
- **initData** — URL-encoded query string from `window.Telegram.WebApp.initData`, signed by Telegram with HMAC-SHA256
- **BFF route** — Next.js server-side API route that proxies requests to FastAPI backend, managing httpOnly cookies
- **Token pair** — `accessToken` (JWT, ~15 min) + `refreshToken` (opaque, 7 days for Telegram sessions)

---

## Scope & Non-Goals

### In scope
1. Rewrite `/api/session/telegram/init` BFF route to call `POST /api/v1/auth/telegram`
2. Implement `TelegramAuthBootstrap` client component (captures initData, calls BFF route)
3. Create `/api/session/refresh` BFF route for token rotation
4. Create `/api/session/logout` BFF route for session termination
5. Redux auth slice (`authSlice`) for client-side auth state
6. RTK Query `baseQuery` wrapper with 401 → refresh → retry
7. Next.js middleware for route protection
8. Debug auth flow preservation (local development without Telegram)

### Non-goals
- Backend changes (IAM is complete)
- OIDC / email-password login flows (future)
- User profile UI
- Onboarding flow for `isNewUser`

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| **Rewrite** | `app/api/session/telegram/init/route.ts` | BFF: forward raw initData → backend `/auth/telegram`, set cookie pair |
| **Create** | `app/api/session/refresh/route.ts` | BFF: read `lm_refresh_token` cookie → backend `/auth/refresh`, rotate cookies |
| **Rewrite** | `app/api/session/logout/route.ts` | BFF: read `lm_access_token` → backend `/auth/logout`, clear cookies |
| **Rewrite** | `components/blocks/telegram/TelegramAuthBootstrap.tsx` | Client component: capture initData on mount → call `/api/session/telegram/init` → dispatch Redux |
| **Create** | `lib/store/authSlice.ts` | Redux slice: `{ status, isNewUser, error }` + async thunks |
| **Rewrite** | `lib/store/api.ts` | RTK Query `baseQuery` with 401 → refresh → retry wrapper |
| **Rewrite** | `lib/store/store.ts` | Register `authSlice` reducer |
| **Rewrite** | `lib/auth/session.ts` | Cookie name constants, `isAuthenticated()` via cookie check |
| **Create** | `middleware.ts` | Next.js edge middleware: check `lm_access_token` cookie, redirect if missing |
| **Modify** | `lib/auth/browserDebugAuth.ts` | Ensure debug flow works with new BFF route contract |
| **Delete** | `app/api/auth/telegram/exchange/route.ts` | Legacy hybrid handoff — replaced by direct IAM flow |
| **Delete** | `app/api/auth/telegram/consume/route.ts` | Legacy hybrid handoff — replaced by direct IAM flow |
| **Delete** | `app/api/auth/telegram/_handoffStore.ts` | Legacy in-memory handoff store — no longer needed |

---

## Architecture Decisions

### AD-1: No initData validation in Next.js BFF

**Decision:** Remove HMAC-SHA256 validation from `session/telegram/init/route.ts`. Send raw initData directly to backend.

**Rationale:**
- Backend already validates via `aiogram.safe_parse_webapp_init_data()` with freshness check
- Eliminates `TG_BOT_TOKEN` duplication between Next.js and FastAPI
- Single source of truth for security validation (backend)
- Less code, fewer crypto dependencies on the frontend server

**Exception:** Debug auth path (`BROWSER_DEBUG_AUTH`) still needs special handling — it bypasses initData entirely and must produce a valid session through the backend.

### AD-2: Two httpOnly cookies (access + refresh)

**Decision:** Store `accessToken` in `lm_access_token` cookie and `refreshToken` in `lm_refresh_token` cookie. Both httpOnly, Secure (prod), SameSite=Lax.

**Rationale:**
- httpOnly prevents XSS token theft
- Separate cookies allow the backend proxy (`/api/backend/[...path]`) to send only the access token as Bearer header
- Refresh token cookie is only sent to `/api/session/refresh` (path-scoped would be ideal but complicates proxy)

**Cookie spec:**

| Cookie | Value | httpOnly | Secure | SameSite | Path | Max-Age |
|--------|-------|----------|--------|----------|------|---------|
| `lm_access_token` | JWT string | true | prod only | Lax | `/` | 900 (15 min) |
| `lm_refresh_token` | opaque string | true | prod only | Lax | `/` | 604800 (7 days) |

### AD-3: RTK Query `baseQuery` wrapper with silent refresh

**Decision:** Wrap the existing `fetchBaseQuery` with a re-auth layer. On 401 response: call `/api/session/refresh` once, retry the original request. If refresh also fails: dispatch `authSlice.actions.sessionExpired()` and let middleware redirect.

**Rationale:**
- Transparent to all RTK Query endpoints — no per-endpoint auth logic
- Single retry prevents infinite loops
- Redux state update triggers UI response (redirect/overlay)

### AD-4: Next.js middleware for route protection

**Decision:** Edge middleware checks for `lm_access_token` cookie existence (not JWT validation). If missing, redirect to a loading/auth page.

**Rationale:**
- Edge middleware cannot do full JWT validation (no access to `SECRET_KEY`)
- Cookie existence is sufficient: if the cookie is set, the backend proxy will validate the actual JWT
- Expired JWTs will be caught by RTK Query's 401 handler which triggers refresh

### AD-5: Debug auth compatibility

**Decision:** When `BROWSER_DEBUG_AUTH=true` and running on localhost, `TelegramAuthBootstrap` sends a debug user payload to the BFF route. The BFF route must handle this by calling the backend with a debug-specific flow.

**Implementation:** The BFF route accepts `{ debugUser: { tg_id, username } }` in the request body. When debug auth is enabled, it constructs a synthetic `Authorization: tma <initData>` using test data signed with the bot token (server-side). Alternatively, for local development the backend can expose a dev-only endpoint. The simplest approach: in debug mode, send the debug user's `tg_id` and `username` to a backend endpoint that creates/finds the identity without initData validation.

> **Note:** This is dev-only and MUST be disabled in production via environment variable checks.

---

## Sequence Diagrams

### Happy Path: First Launch (New User)

```
Telegram Client          TelegramAuthBootstrap       /api/session/telegram/init      FastAPI /auth/telegram
     │                           │                            │                              │
     │  mount Mini App           │                            │                              │
     │────────────────────────▶  │                            │                              │
     │                           │                            │                              │
     │                    read initData from                  │                              │
     │                    window.Telegram.WebApp.initData     │                              │
     │                           │                            │                              │
     │                    dispatch(authSlice.initStart())     │                              │
     │                           │                            │                              │
     │                           │  POST { initData: raw }    │                              │
     │                           │──────────────────────────▶ │                              │
     │                           │                            │                              │
     │                           │                            │  POST, Authorization: tma <raw>
     │                           │                            │─────────────────────────────▶│
     │                           │                            │                              │
     │                           │                            │  HMAC-SHA256 validate         │
     │                           │                            │  Create Identity + LinkedAccount
     │                           │                            │  Create Session               │
     │                           │                            │                              │
     │                           │                            │  200 { accessToken,           │
     │                           │                            │        refreshToken,          │
     │                           │                            │        isNewUser: true }      │
     │                           │                            │◀─────────────────────────────│
     │                           │                            │                              │
     │                           │  200 { ok, isNewUser }     │                              │
     │                           │  Set-Cookie: lm_access_token=<jwt>                        │
     │                           │  Set-Cookie: lm_refresh_token=<opaque>                    │
     │                           │◀──────────────────────────│                              │
     │                           │                            │                              │
     │                    dispatch(authSlice.initSuccess({    │                              │
     │                      isNewUser: true                   │                              │
     │                    }))                                  │                              │
     │                           │                            │                              │
     │  render authenticated UI  │                            │                              │
     │◀──────────────────────── │                            │                              │
```

### Token Refresh (RTK Query interceptor)

```
RTK Query endpoint       baseQueryWithReauth       /api/session/refresh       FastAPI /auth/refresh
     │                           │                         │                         │
     │  GET /api/backend/orders  │                         │                         │
     │──────────────────────────▶│                         │                         │
     │                           │                         │                         │
     │                    proxy forwards Bearer JWT        │                         │
     │                    → backend returns 401            │                         │
     │                           │                         │                         │
     │                    detect 401, attempt refresh      │                         │
     │                           │                         │                         │
     │                           │  POST (cookies auto)    │                         │
     │                           │────────────────────────▶│                         │
     │                           │                         │                         │
     │                           │                         │  POST { refreshToken }  │
     │                           │                         │────────────────────────▶│
     │                           │                         │                         │
     │                           │                         │  Token rotation          │
     │                           │                         │  200 { accessToken,      │
     │                           │                         │        refreshToken }    │
     │                           │                         │◀────────────────────────│
     │                           │                         │                         │
     │                           │  200 Set-Cookie (both)  │                         │
     │                           │◀────────────────────────│                         │
     │                           │                         │                         │
     │                    retry original GET /orders       │                         │
     │                    with new access token cookie     │                         │
     │                           │                         │                         │
     │  200 { orders: [...] }    │                         │                         │
     │◀──────────────────────────│                         │                         │
```

---

## Tasks

### Task 1: Auth Slice (Redux state)

**Files:**
- Create: `frontend/main/lib/store/authSlice.ts`
- Modify: `frontend/main/lib/store/store.ts`

- [ ] **Step 1: Create authSlice with initial state and reducers**

```typescript
// lib/store/authSlice.ts
import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

type AuthStatus = "idle" | "loading" | "authenticated" | "expired" | "error";

interface AuthState {
  status: AuthStatus;
  isNewUser: boolean;
  error: string | null;
}

const initialState: AuthState = {
  status: "idle",
  isNewUser: false,
  error: null,
};

export const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    initStart(state) {
      state.status = "loading";
      state.error = null;
    },
    initSuccess(state, action: PayloadAction<{ isNewUser: boolean }>) {
      state.status = "authenticated";
      state.isNewUser = action.payload.isNewUser;
      state.error = null;
    },
    initFailure(state, action: PayloadAction<string>) {
      state.status = "error";
      state.error = action.payload;
    },
    sessionExpired(state) {
      state.status = "expired";
    },
    logout(state) {
      state.status = "idle";
      state.isNewUser = false;
      state.error = null;
    },
  },
});

export const { initStart, initSuccess, initFailure, sessionExpired, logout } =
  authSlice.actions;

export const selectAuthStatus = (state: { auth: AuthState }) => state.auth.status;
export const selectIsAuthenticated = (state: { auth: AuthState }) =>
  state.auth.status === "authenticated";
export const selectIsNewUser = (state: { auth: AuthState }) => state.auth.isNewUser;
export const selectAuthError = (state: { auth: AuthState }) => state.auth.error;
```

- [ ] **Step 2: Register authSlice in store**

Modify `lib/store/store.ts` — add `auth: authSlice.reducer` to the reducer map:

```typescript
// lib/store/store.ts
import { configureStore } from "@reduxjs/toolkit";
import { api } from "./api";
import { authSlice } from "./authSlice";

export const makeStore = () =>
  configureStore({
    reducer: {
      [api.reducerPath]: api.reducer,
      auth: authSlice.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
  });

export type AppStore = ReturnType<typeof makeStore>;
export type RootState = ReturnType<AppStore["getState"]>;
export type AppDispatch = AppStore["dispatch"];
```

- [ ] **Step 3: Verify store compiles**

Run: `cd frontend/main && npx tsc --noEmit --pretty 2>&1 | head -30`
Expected: No errors related to authSlice or store.

- [ ] **Step 4: Commit**

```bash
git add frontend/main/lib/store/authSlice.ts frontend/main/lib/store/store.ts
git commit -m "feat(frontend): add auth Redux slice with status machine"
```

---

### Task 2: BFF Route — Telegram Init (rewrite)

**Files:**
- Rewrite: `frontend/main/app/api/session/telegram/init/route.ts`

This is the critical integration point. Replaces legacy `/api/v1/users/init/` with new IAM endpoint.

- [ ] **Step 1: Rewrite the route handler**

```typescript
// app/api/session/telegram/init/route.ts
import { NextRequest, NextResponse } from "next/server";

import {
  isBrowserDebugAuthEnabled,
  normalizeBrowserDebugUser,
} from "@/lib/auth/browserDebugAuth";

const ACCESS_COOKIE = "lm_access_token";
const REFRESH_COOKIE = "lm_refresh_token";

function getBackendBaseUrl(): string {
  const raw = process.env.BACKEND_API_BASE_URL;
  if (!raw || typeof raw !== "string" || !raw.trim()) {
    throw new Error("Missing BACKEND_API_BASE_URL");
  }
  return raw.trim().replace(/\/+$/, "");
}

function isProduction(): boolean {
  return process.env.NODE_ENV === "production";
}

function getCookieDomain(): string | undefined {
  const domain = process.env.COOKIE_DOMAIN;
  if (typeof domain !== "string") return undefined;
  const d = domain.trim();
  if (!d) return undefined;

  if (
    d.includes("://") ||
    d.includes("/") ||
    d.includes(":") ||
    d.includes(" ")
  ) {
    return undefined;
  }

  const normalized = d.startsWith(".") ? d.slice(1) : d;
  if (normalized === "localhost" || normalized === "vercel.app")
    return undefined;

  return d;
}

function isLocalBrowserDebugRequest(req: NextRequest): boolean {
  if (!isBrowserDebugAuthEnabled()) return false;

  const hostHeader =
    req.headers.get("x-forwarded-host") || req.headers.get("host") || "";
  const host =
    req.nextUrl?.hostname ||
    hostHeader
      .split(",")
      .map((part: string) => part.trim())
      .filter(Boolean)[0]
      ?.split(":")[0] ||
    "";

  const h = String(host || "").trim().toLowerCase();

  return (
    h === "localhost" ||
    h === "127.0.0.1" ||
    h === "::1" ||
    h.endsWith(".local") ||
    (() => {
      const raw = process.env.BROWSER_DEBUG_AUTH_ALLOWED_HOSTS;
      if (typeof raw !== "string" || !raw.trim()) return false;
      const rules = raw
        .split(/[,\s]+/g)
        .map((x: string) => x.trim().toLowerCase())
        .filter(Boolean);
      return rules.some((rule: string) => {
        if (rule === h) return true;
        if (rule.startsWith("*.") && h.endsWith(rule.slice(1))) return true;
        if (rule.startsWith(".") && h.endsWith(rule)) return true;
        return false;
      });
    })()
  );
}

function serializeCookie(
  name: string,
  value: string,
  opts: {
    maxAge?: number;
    domain?: string;
    path?: string;
    httpOnly?: boolean;
    secure?: boolean;
    sameSite?: string;
  },
): string {
  const parts = [`${encodeURIComponent(name)}=${encodeURIComponent(value)}`];
  if (opts.maxAge) parts.push(`Max-Age=${Math.floor(opts.maxAge)}`);
  if (opts.domain) parts.push(`Domain=${opts.domain}`);
  if (opts.path) parts.push(`Path=${opts.path}`);
  if (opts.httpOnly) parts.push("HttpOnly");
  if (opts.secure) parts.push("Secure");
  if (opts.sameSite) parts.push(`SameSite=${opts.sameSite}`);
  return parts.join("; ");
}

function setTokenCookies(
  res: NextResponse,
  accessToken: string,
  refreshToken: string,
): void {
  const domain = getCookieDomain();
  const secure = isProduction();

  res.headers.append(
    "Set-Cookie",
    serializeCookie(ACCESS_COOKIE, accessToken, {
      httpOnly: true,
      secure,
      sameSite: "Lax",
      path: "/",
      domain,
      maxAge: 900, // 15 minutes
    }),
  );

  res.headers.append(
    "Set-Cookie",
    serializeCookie(REFRESH_COOKIE, refreshToken, {
      httpOnly: true,
      secure,
      sameSite: "Lax",
      path: "/",
      domain,
      maxAge: 60 * 60 * 24 * 7, // 7 days (matches backend TELEGRAM_REFRESH_TOKEN_EXPIRE_DAYS)
    }),
  );
}

export async function POST(req: NextRequest): Promise<NextResponse> {
  let backendBase: string;
  try {
    backendBase = getBackendBaseUrl();
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Server config error" },
      { status: 500 },
    );
  }

  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const initData =
    typeof body?.initData === "string" ? (body.initData as string).trim() : "";

  // --- Debug auth path (dev only) ---
  if (!initData && isLocalBrowserDebugRequest(req)) {
    const debugUser = normalizeBrowserDebugUser(
      body?.debugUser as Record<string, unknown> | undefined,
    );
    if (debugUser) {
      // In debug mode, call backend with a synthetic initData or a dev endpoint.
      // For now, we use the legacy init endpoint as a debug fallback.
      const debugRes = await fetch(`${backendBase}/api/v1/users/init/`, {
        method: "POST",
        headers: { accept: "application/json", "content-type": "application/json" },
        body: JSON.stringify({
          init_data: {
            user: { username: debugUser.username, id: String(debugUser.tg_id) },
          },
        }),
      });

      const debugJson = await debugRes.text().then((t) => {
        try { return JSON.parse(t); } catch { return null; }
      });

      if (!debugRes.ok) {
        return NextResponse.json(
          { error: "Debug backend init failed", details: debugJson },
          { status: 502 },
        );
      }

      const accessToken = debugJson?.accessToken;
      if (typeof accessToken !== "string" || !accessToken) {
        return NextResponse.json(
          { error: "Debug backend did not return accessToken" },
          { status: 502 },
        );
      }

      const res = NextResponse.json(
        { ok: true, isNewUser: false, debug: true },
        { status: 200 },
      );

      // Debug flow may not return refreshToken — use accessToken for both cookies
      const refreshToken =
        typeof debugJson?.refreshToken === "string"
          ? debugJson.refreshToken
          : accessToken;

      setTokenCookies(res, accessToken, refreshToken);
      return res;
    }
  }

  // --- Production path: forward raw initData to backend IAM ---
  if (!initData) {
    return NextResponse.json(
      { error: "initData is required" },
      { status: 400 },
    );
  }

  const upstreamUrl = `${backendBase}/api/v1/auth/telegram`;

  let upstreamRes: Response;
  try {
    upstreamRes = await fetch(upstreamUrl, {
      method: "POST",
      headers: {
        accept: "application/json",
        authorization: `tma ${initData}`,
      },
    });
  } catch (e) {
    return NextResponse.json(
      { error: "Backend unreachable", detail: e instanceof Error ? e.message : "unknown" },
      { status: 502 },
    );
  }

  const text = await upstreamRes.text();
  let json: Record<string, unknown> | null = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    json = null;
  }

  if (!upstreamRes.ok) {
    return NextResponse.json(
      {
        error: "Backend auth failed",
        status: upstreamRes.status,
        details: json ?? text,
      },
      { status: upstreamRes.status === 401 ? 401 : 502 },
    );
  }

  const accessToken = json?.accessToken;
  const refreshToken = json?.refreshToken;
  const isNewUser = json?.isNewUser === true;

  if (typeof accessToken !== "string" || !accessToken) {
    return NextResponse.json(
      { error: "Backend did not return accessToken", details: json },
      { status: 502 },
    );
  }

  if (typeof refreshToken !== "string" || !refreshToken) {
    return NextResponse.json(
      { error: "Backend did not return refreshToken", details: json },
      { status: 502 },
    );
  }

  const res = NextResponse.json(
    { ok: true, isNewUser },
    { status: 200 },
  );

  setTokenCookies(res, accessToken, refreshToken);
  return res;
}
```

- [ ] **Step 2: Verify the route compiles**

Run: `cd frontend/main && npx tsc --noEmit --pretty 2>&1 | head -30`
Expected: No type errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/main/app/api/session/telegram/init/route.ts
git commit -m "feat(frontend): rewrite telegram init BFF route for IAM /auth/telegram"
```

---

### Task 3: BFF Route — Token Refresh

**Files:**
- Create: `frontend/main/app/api/session/refresh/route.ts`

- [ ] **Step 1: Create the refresh route**

```typescript
// app/api/session/refresh/route.ts
import { NextRequest, NextResponse } from "next/server";

const ACCESS_COOKIE = "lm_access_token";
const REFRESH_COOKIE = "lm_refresh_token";

function getBackendBaseUrl(): string {
  const raw = process.env.BACKEND_API_BASE_URL;
  if (!raw || typeof raw !== "string" || !raw.trim()) {
    throw new Error("Missing BACKEND_API_BASE_URL");
  }
  return raw.trim().replace(/\/+$/, "");
}

function isProduction(): boolean {
  return process.env.NODE_ENV === "production";
}

function getCookieDomain(): string | undefined {
  const domain = process.env.COOKIE_DOMAIN;
  if (typeof domain !== "string") return undefined;
  const d = domain.trim();
  if (!d) return undefined;
  if (d.includes("://") || d.includes("/") || d.includes(":") || d.includes(" "))
    return undefined;
  const normalized = d.startsWith(".") ? d.slice(1) : d;
  if (normalized === "localhost" || normalized === "vercel.app") return undefined;
  return d;
}

function serializeCookie(
  name: string,
  value: string,
  opts: { maxAge?: number; domain?: string; path?: string; httpOnly?: boolean; secure?: boolean; sameSite?: string },
): string {
  const parts = [`${encodeURIComponent(name)}=${encodeURIComponent(value)}`];
  if (opts.maxAge) parts.push(`Max-Age=${Math.floor(opts.maxAge)}`);
  if (opts.domain) parts.push(`Domain=${opts.domain}`);
  if (opts.path) parts.push(`Path=${opts.path}`);
  if (opts.httpOnly) parts.push("HttpOnly");
  if (opts.secure) parts.push("Secure");
  if (opts.sameSite) parts.push(`SameSite=${opts.sameSite}`);
  return parts.join("; ");
}

function clearCookie(name: string): string {
  return serializeCookie(name, "", {
    maxAge: 0,
    path: "/",
    httpOnly: true,
    secure: isProduction(),
    sameSite: "Lax",
    domain: getCookieDomain(),
  });
}

export async function POST(req: NextRequest): Promise<NextResponse> {
  const refreshToken = req.cookies.get(REFRESH_COOKIE)?.value;

  if (!refreshToken) {
    return NextResponse.json(
      { error: "No refresh token" },
      { status: 401 },
    );
  }

  let backendBase: string;
  try {
    backendBase = getBackendBaseUrl();
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Server config error" },
      { status: 500 },
    );
  }

  let upstreamRes: Response;
  try {
    upstreamRes = await fetch(`${backendBase}/api/v1/auth/refresh`, {
      method: "POST",
      headers: {
        accept: "application/json",
        "content-type": "application/json",
      },
      body: JSON.stringify({ refreshToken }),
    });
  } catch (e) {
    return NextResponse.json(
      { error: "Backend unreachable", detail: e instanceof Error ? e.message : "unknown" },
      { status: 502 },
    );
  }

  const text = await upstreamRes.text();
  let json: Record<string, unknown> | null = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    json = null;
  }

  if (!upstreamRes.ok) {
    // Refresh failed — clear cookies, force re-auth
    const res = NextResponse.json(
      { error: "Refresh failed", status: upstreamRes.status },
      { status: 401 },
    );
    res.headers.append("Set-Cookie", clearCookie(ACCESS_COOKIE));
    res.headers.append("Set-Cookie", clearCookie(REFRESH_COOKIE));
    return res;
  }

  const newAccessToken = json?.accessToken;
  const newRefreshToken = json?.refreshToken;

  if (
    typeof newAccessToken !== "string" || !newAccessToken ||
    typeof newRefreshToken !== "string" || !newRefreshToken
  ) {
    return NextResponse.json(
      { error: "Backend did not return token pair" },
      { status: 502 },
    );
  }

  const res = NextResponse.json({ ok: true }, { status: 200 });
  const domain = getCookieDomain();
  const secure = isProduction();

  res.headers.append(
    "Set-Cookie",
    serializeCookie(ACCESS_COOKIE, newAccessToken, {
      httpOnly: true, secure, sameSite: "Lax", path: "/", domain,
      maxAge: 900,
    }),
  );
  res.headers.append(
    "Set-Cookie",
    serializeCookie(REFRESH_COOKIE, newRefreshToken, {
      httpOnly: true, secure, sameSite: "Lax", path: "/", domain,
      maxAge: 60 * 60 * 24 * 7,
    }),
  );

  return res;
}
```

- [ ] **Step 2: Verify compiles**

Run: `cd frontend/main && npx tsc --noEmit --pretty 2>&1 | head -30`

- [ ] **Step 3: Commit**

```bash
git add frontend/main/app/api/session/refresh/route.ts
git commit -m "feat(frontend): add /api/session/refresh BFF route for token rotation"
```

---

### Task 4: BFF Route — Logout

**Files:**
- Create: `frontend/main/app/api/session/logout/route.ts`

- [ ] **Step 1: Create the logout route**

```typescript
// app/api/session/logout/route.ts
import { NextRequest, NextResponse } from "next/server";

const ACCESS_COOKIE = "lm_access_token";
const REFRESH_COOKIE = "lm_refresh_token";

function getBackendBaseUrl(): string {
  const raw = process.env.BACKEND_API_BASE_URL;
  if (!raw || typeof raw !== "string" || !raw.trim()) {
    throw new Error("Missing BACKEND_API_BASE_URL");
  }
  return raw.trim().replace(/\/+$/, "");
}

function isProduction(): boolean {
  return process.env.NODE_ENV === "production";
}

function getCookieDomain(): string | undefined {
  const domain = process.env.COOKIE_DOMAIN;
  if (typeof domain !== "string") return undefined;
  const d = domain.trim();
  if (!d) return undefined;
  if (d.includes("://") || d.includes("/") || d.includes(":") || d.includes(" "))
    return undefined;
  const normalized = d.startsWith(".") ? d.slice(1) : d;
  if (normalized === "localhost" || normalized === "vercel.app") return undefined;
  return d;
}

function clearCookie(name: string): string {
  const parts = [`${encodeURIComponent(name)}=`];
  parts.push("Max-Age=0");
  parts.push("Path=/");
  parts.push("HttpOnly");
  if (isProduction()) parts.push("Secure");
  parts.push("SameSite=Lax");
  const domain = getCookieDomain();
  if (domain) parts.push(`Domain=${domain}`);
  return parts.join("; ");
}

export async function POST(req: NextRequest): Promise<NextResponse> {
  const accessToken = req.cookies.get(ACCESS_COOKIE)?.value;

  let backendBase: string | undefined;
  try {
    backendBase = getBackendBaseUrl();
  } catch {
    // Even if backend is unreachable, clear cookies locally
  }

  // Best-effort backend logout (session revocation)
  if (accessToken && backendBase) {
    try {
      await fetch(`${backendBase}/api/v1/auth/logout`, {
        method: "POST",
        headers: {
          accept: "application/json",
          authorization: `Bearer ${accessToken}`,
        },
      });
    } catch {
      // Ignore — we still clear cookies regardless
    }
  }

  const res = NextResponse.json({ ok: true }, { status: 200 });
  res.headers.append("Set-Cookie", clearCookie(ACCESS_COOKIE));
  res.headers.append("Set-Cookie", clearCookie(REFRESH_COOKIE));
  return res;
}
```

- [ ] **Step 2: Update `lib/auth/session.ts`**

```typescript
// lib/auth/session.ts
export const ACCESS_COOKIE_NAME = "lm_access_token";
export const REFRESH_COOKIE_NAME = "lm_refresh_token";

export function getAccessTokenCookieName(): string {
  return ACCESS_COOKIE_NAME;
}

export function getRefreshTokenCookieName(): string {
  return REFRESH_COOKIE_NAME;
}

export async function logout(): Promise<void> {
  await fetch("/api/session/logout", { method: "POST", credentials: "include" });
}
```

- [ ] **Step 3: Verify compiles**

Run: `cd frontend/main && npx tsc --noEmit --pretty 2>&1 | head -30`

- [ ] **Step 4: Commit**

```bash
git add frontend/main/app/api/session/logout/route.ts frontend/main/lib/auth/session.ts
git commit -m "feat(frontend): add logout BFF route with cookie clearing"
```

---

### Task 5: RTK Query — baseQuery with auto-refresh

**Files:**
- Rewrite: `frontend/main/lib/store/api.ts`

- [ ] **Step 1: Add re-auth wrapper to baseQuery**

```typescript
// lib/store/api.ts
import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import type {
  BaseQueryFn,
  FetchArgs,
  FetchBaseQueryError,
} from "@reduxjs/toolkit/query";
import { sessionExpired } from "./authSlice";

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "/api/backend";

const backendBaseQuery = fetchBaseQuery({
  baseUrl,
  credentials: "include",
});

const appBaseQuery = fetchBaseQuery({
  baseUrl: "",
  credentials: "include",
});

const rawBaseQuery: BaseQueryFn<
  string | FetchArgs,
  unknown,
  FetchBaseQueryError
> = async (args, api, extraOptions) => {
  const url = typeof args === "string" ? args : args?.url;

  if (typeof url === "string" && url.startsWith("/api/session/")) {
    return appBaseQuery(args, api, extraOptions);
  }

  return backendBaseQuery(args, api, extraOptions);
};

const baseQueryWithReauth: BaseQueryFn<
  string | FetchArgs,
  unknown,
  FetchBaseQueryError
> = async (args, api, extraOptions) => {
  let result = await rawBaseQuery(args, api, extraOptions);

  if (result.error && result.error.status === 401) {
    // Attempt silent refresh
    const refreshResult = await rawBaseQuery(
      { url: "/api/session/refresh", method: "POST" },
      api,
      extraOptions,
    );

    if (refreshResult.error) {
      // Refresh failed — session is dead
      api.dispatch(sessionExpired());
      return result;
    }

    // Retry the original request with fresh cookies
    result = await rawBaseQuery(args, api, extraOptions);
  }

  return result;
};

export const api = createApi({
  reducerPath: "api",
  baseQuery: baseQueryWithReauth,
  tagTypes: ["User", "Products", "Product", "Categories", "Brands"],
  endpoints: () => ({}),
});
```

- [ ] **Step 2: Verify compiles**

Run: `cd frontend/main && npx tsc --noEmit --pretty 2>&1 | head -30`

- [ ] **Step 3: Commit**

```bash
git add frontend/main/lib/store/api.ts
git commit -m "feat(frontend): add 401 → refresh → retry logic to RTK Query baseQuery"
```

---

### Task 6: TelegramAuthBootstrap (client component)

**Files:**
- Rewrite: `frontend/main/components/blocks/telegram/TelegramAuthBootstrap.tsx`

- [ ] **Step 1: Implement the auth bootstrap component**

```tsx
// components/blocks/telegram/TelegramAuthBootstrap.tsx
"use client";

import { useEffect, useRef, useState } from "react";

import {
  isBrowserDebugAuthEnabled,
  getBrowserDebugUser,
} from "@/lib/auth/browserDebugAuth";
import { useAppDispatch, useAppSelector } from "@/lib/store/hooks";
import {
  initStart,
  initSuccess,
  initFailure,
  selectAuthStatus,
} from "@/lib/store/authSlice";

/**
 * Reads initData from all available sources.
 *
 * Why not use useTelegramContext().initData?
 * The context derives initData from a ref inside useEffect. Due to React's
 * effect ordering (children fire before parents), this component's effect
 * runs BEFORE TelegramProvider's effect sets the ref. Reading directly from
 * window.Telegram.WebApp avoids this timing issue entirely.
 */
function getInitData(): string {
  // 1. Direct SDK access (most reliable — available synchronously after script load)
  const fromSdk = window.Telegram?.WebApp?.initData;
  if (typeof fromSdk === "string" && fromSdk) return fromSdk;

  // 2. Global set by TelegramProvider (fallback)
  const fromGlobal = window.__LM_TG_INIT_DATA__;
  if (typeof fromGlobal === "string" && fromGlobal) return fromGlobal;

  return "";
}

export default function TelegramAuthBootstrap(): null {
  const dispatch = useAppDispatch();
  const authStatus = useAppSelector(selectAuthStatus);
  const calledRef = useRef(false);

  useEffect(() => {
    // Only run once, and only if we haven't already authenticated
    if (calledRef.current) return;
    if (authStatus === "authenticated" || authStatus === "loading") return;

    const rawInitData = getInitData();
    const isDebug = isBrowserDebugAuthEnabled() && !rawInitData;

    if (!rawInitData && !isDebug) {
      // Not in Telegram and not in debug mode — nothing to do
      return;
    }

    calledRef.current = true;
    dispatch(initStart());

    const body: Record<string, unknown> = {};

    if (rawInitData) {
      body.initData = rawInitData;
    } else if (isDebug) {
      body.debugUser = getBrowserDebugUser();
    }

    fetch("/api/session/telegram/init", {
      method: "POST",
      headers: { "content-type": "application/json" },
      credentials: "include",
      body: JSON.stringify(body),
    })
      .then(async (res) => {
        if (!res.ok) {
          const errBody = await res.json().catch(() => ({}));
          throw new Error(errBody?.error || `Auth failed: ${res.status}`);
        }
        return res.json();
      })
      .then((data) => {
        dispatch(
          initSuccess({ isNewUser: data?.isNewUser === true }),
        );
      })
      .catch((err) => {
        dispatch(initFailure(err instanceof Error ? err.message : "Auth error"));
        calledRef.current = false; // Allow retry
      });
  }, [dispatch, authStatus, initData]);

  return null;
}
```

- [ ] **Step 2: Verify compiles**

Run: `cd frontend/main && npx tsc --noEmit --pretty 2>&1 | head -30`

- [ ] **Step 3: Commit**

```bash
git add frontend/main/components/blocks/telegram/TelegramAuthBootstrap.tsx
git commit -m "feat(frontend): implement TelegramAuthBootstrap with initData → BFF → Redux flow"
```

---

### Task 7: Next.js Middleware (route protection)

**Files:**
- Create: `frontend/main/middleware.ts`

- [ ] **Step 1: Create edge middleware**

```typescript
// middleware.ts
import { NextResponse, type NextRequest } from "next/server";

const ACCESS_COOKIE = "lm_access_token";

function isPublicPath(pathname: string): boolean {
  // API routes handle their own auth logic
  if (pathname.startsWith("/api/")) return true;
  // Static assets
  if (pathname.startsWith("/_next/")) return true;
  if (pathname.startsWith("/favicon")) return true;
  return false;
}

export function middleware(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;

  if (isPublicPath(pathname)) {
    return NextResponse.next();
  }

  // In a Telegram Mini App we do NOT redirect unauthenticated users.
  // The app must load first so TelegramAuthBootstrap can capture initData
  // from window.Telegram.WebApp and complete the auth flow.
  // After auth completes (cookies set), subsequent requests carry the JWT.
  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization)
     * - favicon.ico
     */
    "/((?!_next/static|_next/image|favicon.ico).*)",
  ],
};
```

> **Note:** We intentionally do NOT redirect unauthenticated users. In a Telegram Mini App, the first page load is always unauthenticated — the app must load, capture `initData`, and complete the auth flow. The middleware sets `x-auth-status` header for SSR components that might want to show loading states.

- [ ] **Step 2: Verify compiles**

Run: `cd frontend/main && npx tsc --noEmit --pretty 2>&1 | head -30`

- [ ] **Step 3: Commit**

```bash
git add frontend/main/middleware.ts
git commit -m "feat(frontend): add Next.js edge middleware for auth status headers"
```

---

### Task 8: Cleanup legacy handoff routes

**Files:**
- Delete: `frontend/main/app/api/auth/telegram/exchange/route.ts`
- Delete: `frontend/main/app/api/auth/telegram/consume/route.ts`
- Delete: `frontend/main/app/api/auth/telegram/_handoffStore.ts`

- [ ] **Step 1: Remove legacy files**

```bash
rm frontend/main/app/api/auth/telegram/exchange/route.ts
rm frontend/main/app/api/auth/telegram/consume/route.ts
rm frontend/main/app/api/auth/telegram/_handoffStore.ts
```

- [ ] **Step 2: Remove the empty directory if no other files remain**

```bash
# Check if directory is empty, then remove
ls frontend/main/app/api/auth/telegram/ 2>/dev/null
# If empty:
rmdir frontend/main/app/api/auth/telegram/ 2>/dev/null
rmdir frontend/main/app/api/auth/ 2>/dev/null
```

- [ ] **Step 3: Verify the build still works**

Run: `cd frontend/main && npx tsc --noEmit --pretty 2>&1 | head -30`

- [ ] **Step 4: Commit**

```bash
git add -A frontend/main/app/api/auth/
git commit -m "chore(frontend): remove legacy telegram handoff routes (replaced by IAM flow)"
```

---

### Task 9: Remove `lib/auth/telegram.ts` server validation

**Files:**
- Delete: `frontend/main/lib/auth/telegram.ts`

Per AD-1, initData validation is now handled exclusively by the backend. This file contained HMAC-SHA256 validation and JWT signing for the legacy handoff flow.

- [ ] **Step 1: Check for remaining imports**

```bash
cd frontend/main && grep -r "lib/auth/telegram" --include="*.ts" --include="*.tsx" . | grep -v node_modules
```

If any imports remain (besides the deleted handoff routes), update them before deleting.

- [ ] **Step 2: Delete the file**

```bash
rm frontend/main/lib/auth/telegram.ts
```

- [ ] **Step 3: Verify compiles**

Run: `cd frontend/main && npx tsc --noEmit --pretty 2>&1 | head -30`

- [ ] **Step 4: Commit**

```bash
git add frontend/main/lib/auth/telegram.ts
git commit -m "chore(frontend): remove client-side initData validation (backend handles it)"
```

---

### Task 10: Integration Verification

- [ ] **Step 1: Full TypeScript check**

```bash
cd frontend/main && npx tsc --noEmit --pretty
```

Expected: Zero errors.

- [ ] **Step 2: Dev server smoke test**

```bash
cd frontend/main && npm run dev
```

Open `http://localhost:3000` in browser with `BROWSER_DEBUG_AUTH=true`.
Expected: Console shows auth flow completing, Redux state transitions to `authenticated`.

- [ ] **Step 3: Verify cookie pair is set**

Open DevTools → Application → Cookies → `localhost`.
Expected:
- `lm_access_token` — JWT string, httpOnly
- `lm_refresh_token` — opaque string, httpOnly

- [ ] **Step 4: Verify RTK Query requests include Bearer token**

Open DevTools → Network tab → trigger any API call (e.g. navigate to catalog).
Check `/api/backend/*` requests.
Expected: The backend proxy reads `lm_access_token` from cookie and attaches `Authorization: Bearer <jwt>` header.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "test(frontend): verify telegram auth integration end-to-end"
```

---

## Appendix A: Backend API Response Shapes (CamelCase)

The backend uses `CamelModel` which serializes to camelCase JSON. All responses from `/api/v1/auth/*` follow this convention.

```typescript
// POST /api/v1/auth/telegram → TelegramTokenResponse
{
  "accessToken": "eyJhbGciOiJIUzI1NiJ9...",
  "refreshToken": "dGhpcyBpcyBhIHRlc3Q...",
  "tokenType": "bearer",
  "isNewUser": true
}

// POST /api/v1/auth/refresh → TokenResponse
{
  "accessToken": "eyJhbGciOiJIUzI1NiJ9...",
  "refreshToken": "bmV3IHJlZnJlc2g...",
  "tokenType": "bearer"
}

// POST /api/v1/auth/logout → MessageResponse
{
  "message": "Logged out successfully"
}
```

## Appendix B: Environment Variables

No new environment variables required. The existing ones are sufficient:

| Variable | Used By | Purpose |
|----------|---------|---------|
| `BACKEND_API_BASE_URL` | BFF routes | Backend URL for API proxy |
| `COOKIE_DOMAIN` | BFF routes | Cookie domain scope |
| `BROWSER_DEBUG_AUTH` | BFF + Bootstrap | Enable debug auth |
| `NEXT_PUBLIC_BROWSER_DEBUG_AUTH` | Client components | Client-side debug flag |
| `BROWSER_DEBUG_AUTH_ALLOWED_HOSTS` | BFF routes | Allowed debug hosts |

**Removed dependency:** `TG_BOT_TOKEN` is no longer needed by Next.js — backend handles initData validation.

## Appendix C: Key Insight — Why No Redirect on Unauthenticated

In a standard web app, the middleware would redirect `/profile` → `/login`. In a Telegram Mini App this is wrong because:

1. The app always loads unauthenticated (no cookies on first visit)
2. `window.Telegram.WebApp.initData` is only available after the page renders
3. `TelegramAuthBootstrap` captures initData and completes auth during mount
4. After auth completes (cookies set), all subsequent navigations are authenticated

The correct pattern: render the app immediately, show a loading state while `authSlice.status === "loading"`, then show content when `authenticated`.
