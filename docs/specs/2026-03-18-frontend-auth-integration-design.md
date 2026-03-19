# Frontend Auth Integration — Design Spec

**Date:** 2026-03-18
**Scope:** Auth-only (login, logout, refresh, protected routes). Mock data unchanged.
**Approach:** BFF (Backend-for-Frontend) with httpOnly cookies + Next.js Middleware.

---

## 1. Architecture Overview

```
Browser                    Next.js Server (Route Handlers)         Backend API
  |                              |                                    |
  |-- POST /api/auth/login ----->|                                    |
  |   {email, password}          |-- POST /api/v1/auth/login -------->|
  |                              |<-- {accessToken, refreshToken} ----|
  |                              |                                    |
  |                              |-- Set-Cookie: access_token (httpOnly, 15min)
  |                              |-- Set-Cookie: refresh_token (httpOnly, 30d)
  |<-- 200 {success: true} -----|
  |                              |
  |-- GET /admin/orders -------->|                                    |
  |                              |-- middleware.js checks cookie       |
  |                              |-- cookie present -> pass through    |
  |<-- HTML page ----------------|                                    |
  |                              |
  |-- GET /admin/orders -------->|  (no cookie)                       |
  |                              |-- middleware.js: no cookie          |
  |<-- 307 -> /login ------------|                                    |
  |                              |
  |-- POST /api/auth/refresh --->|  (automatic on 401)                |
  |                              |-- POST /api/v1/auth/refresh ------>|
  |                              |<-- {newAccess, newRefresh} --------|
  |                              |-- Set-Cookie: updated tokens        |
  |<-- 200 ---------------------|
```

Key decisions:
- Next.js Route Handlers (`/api/auth/*`) act as BFF proxy — client never talks to backend directly for auth
- Tokens live in httpOnly cookies — JavaScript has no access
- Middleware protects all `/admin/*` routes at Edge Runtime level
- On expired access token — automatic refresh via refresh_token cookie

---

## 2. File Structure

### New files (9)

| File | Type | Purpose |
|------|------|---------|
| `src/middleware.js` | Edge Runtime | Redirect unauthenticated -> `/login` |
| `src/app/login/page.jsx` | Client Component | Email + password form |
| `src/app/api/auth/login/route.js` | Route Handler | Proxy to backend, set cookies |
| `src/app/api/auth/logout/route.js` | Route Handler | Call backend logout, clear cookies |
| `src/app/api/auth/refresh/route.js` | Route Handler | Token rotation, update cookies |
| `src/app/api/auth/me/route.js` | Route Handler | Return identity from access_token |
| `src/lib/auth.js` | Server utility | Cookie helpers, JWT payload decode |
| `src/lib/api-client.js` | Shared utility | Base fetch to `BACKEND_URL` |
| `src/hooks/useAuth.js` | Client hook | `useAuth()` -> `{ user, logout, isLoading }` |

### Modified files (1)

| File | Change |
|------|--------|
| `src/app/admin/layout.jsx` | Add `AuthProvider` wrapper + logout button in sidebar |

Note: `BACKEND_URL` is a server-side env var available via `process.env.BACKEND_URL` by default in Next.js — no `next.config.js` change needed.

### New env file (1)

`.env.local` with `BACKEND_URL=http://127.0.0.1:8000`

---

## 3. Middleware (`src/middleware.js`)

```
Flow:
1. Get access_token from cookies
2. If missing -> redirect /login
3. If present -> decode payload (base64, no crypto verification)
4. If exp < now -> attempt refresh directly against backend:
   - Get refresh_token from cookies
   - Fetch POST BACKEND_URL/api/v1/auth/refresh directly (bypasses BFF route handler)
   - Success -> set updated cookies on NextResponse, pass request through
   - Fail -> delete both cookies, redirect /login
5. Pass request through

Matcher config:
  export const config = {
    matcher: ['/admin/:path*']
  }
```

JWT is NOT signature-verified in middleware (Edge Runtime has no Node.js crypto). Only `exp` is checked. Real verification happens on backend with each API call.

**Important:** Middleware calls the backend refresh endpoint directly (not the internal `/api/auth/refresh` route handler) to avoid self-referential requests in Edge Runtime.

---

## 4. Login Page (`src/app/login/page.jsx`)

UI:
- Centered card on app-bg (#efeff0) background
- Email input + Password input
- "Войти" button
- Error display by backend error code

Flow:
1. User enters email + password
2. POST /api/auth/login (internal Route Handler)
3. Success -> `router.push('/admin/orders')`
4. Error -> display message by code:
   - `INVALID_CREDENTIALS` -> "Неверный email или пароль"
   - `IDENTITY_DEACTIVATED` -> "Аккаунт деактивирован"
   - `MAX_SESSIONS_EXCEEDED` -> "Превышен лимит сессий"

---

## 5. Route Handlers (BFF Proxy)

### POST `/api/auth/login`

1. Extract `{email, password}` from request body
2. Fetch `POST BACKEND_URL/api/v1/auth/login` with camelCase body
3. On backend 200:
   - Extract `accessToken`, `refreshToken` from response
   - Set cookies:
     - `access_token`: httpOnly, secure, sameSite=lax, path=/, maxAge=900 (15 min)
     - `refresh_token`: httpOnly, secure, sameSite=lax, path=/, maxAge=2592000 (30 days)
   - Return 200 `{success: true}`
4. On backend error -> proxy error response as-is

### POST `/api/auth/refresh`

1. Get `refresh_token` from cookies
2. If missing -> 401
3. Fetch `POST BACKEND_URL/api/v1/auth/refresh` with `{refreshToken: cookie_value}`
4. On 200 -> update both cookies with new values
5. On error -> delete both cookies, return 401

### POST `/api/auth/logout`

1. Get `access_token` from cookies
2. If access_token present:
   - Fetch `POST BACKEND_URL/api/v1/auth/logout` with `Authorization: Bearer access_token`
   - If backend returns 401 (token expired) — skip backend call, proceed to cookie cleanup
3. Delete both cookies (regardless of backend response)
4. Return 200 `{success: true}`

**Note:** Logout is best-effort on backend side. Even if the access token expired and backend rejects the call, cookies are always cleared client-side. The session will expire naturally on the backend.

### GET `/api/auth/me`

1. Get `access_token` from cookies
2. If missing -> 401
3. Decode payload (base64) -> extract `sub` (identityId), `sid` (sessionId)
4. Return `{identityId, sessionId}`

---

## 6. Cookie Configuration

| Cookie | Path | maxAge | httpOnly | secure | sameSite |
|--------|------|--------|----------|--------|----------|
| `access_token` | `/` | 900 (15m) | yes | yes* | lax |
| `refresh_token` | `/` | 2592000 (30d) | yes | yes* | lax |

*`secure: true` in production, `false` in dev (http://localhost)

Both cookies use `path=/` so middleware can read `refresh_token` on `/admin/*` requests for silent refresh. The refresh token is still protected: httpOnly (no JS access), secure (HTTPS only in prod), and the raw value is never exposed to the client.

---

## 7. `useAuth()` Hook

```javascript
// Returns:
{
  user: { identityId } | null,   // data from /api/auth/me
  isLoading: boolean,             // initial check in progress
  isAuthenticated: boolean,       // user !== null
  logout: () => Promise<void>     // POST /api/auth/logout -> redirect /login
}

// Internals:
// - On mount -> GET /api/auth/me
// - On 401 -> user = null (middleware already redirected)
// - logout() -> POST /api/auth/logout -> router.push('/login')
```

---

## 8. Changes to Existing Files

### `src/app/admin/layout.jsx`

- Wrap children in `<AuthProvider>` (thin provider based on `useAuth`)
- Add "Выйти" (Logout) button at bottom of Sidebar, calls `logout()`

### `.env.local` (new)

```
BACKEND_URL=http://127.0.0.1:8000
```

---

## 9. Error Handling

Backend error envelope:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {}
  }
}
```

Route Handlers proxy this structure to the client. Login page maps codes to Russian UI messages.

Relevant codes for auth flow:

| HTTP | Code | UI Message |
|------|------|------------|
| 401 | `INVALID_CREDENTIALS` | Неверный email или пароль |
| 401 | `INVALID_TOKEN` | (redirect to login, clear cookies) |
| 401 | `TOKEN_EXPIRED` | (silent refresh, no UI) |
| 401 | `SESSION_EXPIRED` | Сессия истекла (redirect to login) |
| 401 | `SESSION_REVOKED` | Сессия отозвана (redirect to login) |
| 401 | `REFRESH_TOKEN_REUSE` | Обнаружено повторное использование токена (redirect to login, clear cookies) |
| 403 | `IDENTITY_DEACTIVATED` | Аккаунт деактивирован |
| 429 | `MAX_SESSIONS_EXCEEDED` | Превышен лимит сессий (макс. 5) |

---

## 10. Security Considerations

- **XSS protection**: tokens in httpOnly cookies, inaccessible to JavaScript
- **CSRF**: sameSite=lax + POST-only mutations + custom `X-Requested-With: XMLHttpRequest` header on all BFF requests (extra layer — sameSite=lax covers most vectors, custom header blocks the rest since browsers don't attach custom headers on cross-origin form submissions)
- **Token exposure**: both cookies are httpOnly (no JS access) and secure (HTTPS in prod)
- **No client-side secrets**: `BACKEND_URL` stays server-side, never in client bundle
- **Refresh token rotation**: backend rotates on each refresh, old token invalidated
- **Graceful degradation**: if refresh fails, both cookies cleared, redirect to login
