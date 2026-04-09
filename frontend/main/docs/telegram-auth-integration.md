# Telegram Auth Integration — Backend API Spec for Frontend

## Overview

Backend uses **Telegram Mini App initData** for authentication. The frontend gets `initData` from `window.Telegram.WebApp.initData` and sends it to the backend. The backend validates the HMAC-SHA256 signature, creates/finds the user, and returns JWT tokens.

---

## Auth Endpoints

Base URL: `{API_BASE}/api/v1/auth`

### 1. Telegram Login (Primary Flow)

```
POST /api/v1/auth/telegram
```

**Headers:**
```
Authorization: tma <window.Telegram.WebApp.initData>
Content-Type: application/json
```

> **Important:** The scheme is `tma`, NOT `Bearer`. The value is the raw `initData` query string from Telegram SDK.

**Request body:** None

**Response (200):**
```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiJ9...",
  "refreshToken": "Dxe-2aCgJuqH...",
  "tokenType": "bearer",
  "isNewUser": true
}
```

**Errors:**
| Status | Meaning |
|--------|---------|
| 401 | Invalid initData signature, expired (>5 min old), or missing user |
| 403 | Account deactivated |

---

### 2. Refresh Token

```
POST /api/v1/auth/refresh
```

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "refreshToken": "Dxe-2aCgJuqH..."
}
```

**Response (200):**
```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiJ9...",
  "refreshToken": "NEW-rotated-token...",
  "tokenType": "bearer"
}
```

> **Important:** Refresh token **rotates** on every use. Always store the new `refreshToken` from the response. Reusing an old refresh token will **revoke ALL sessions** (security measure).

**Errors:**
| Status | Meaning |
|--------|---------|
| 401 | Token expired, revoked, or reuse detected |

---

### 3. Logout

```
POST /api/v1/auth/logout
Authorization: Bearer <accessToken>
```

**Response (200):**
```json
{
  "message": "Logged out successfully"
}
```

---

### 4. Logout All Sessions

```
POST /api/v1/auth/logout/all
Authorization: Bearer <accessToken>
```

---

## Token Lifecycle

| Token | Lifetime | Storage Recommendation |
|-------|----------|----------------------|
| `accessToken` (JWT) | **15 minutes** | In-memory (variable/zustand/redux) |
| `refreshToken` (opaque) | **7 days** | `localStorage` or secure storage |

### JWT Payload (decoded accessToken)
```json
{
  "sub": "uuid-identity-id",
  "sid": "uuid-session-id",
  "tv": 1,
  "exp": 1710001500,
  "iat": 1710000600,
  "jti": "uuid-unique-per-token"
}
```

---

## Frontend Auth Flow

```
┌──────────────────────────────────────────────────────┐
│ 1. App loads inside Telegram                         │
│    window.Telegram.WebApp.initData → raw string      │
├──────────────────────────────────────────────────────┤
│ 2. POST /api/v1/auth/telegram                        │
│    Header: Authorization: tma <initData>             │
├──────────────────────────────────────────────────────┤
│ 3. Receive { accessToken, refreshToken, isNewUser }  │
│    - Store accessToken in memory                     │
│    - Store refreshToken in localStorage              │
│    - Dispatch authSuccess({ isNewUser })              │
├──────────────────────────────────────────────────────┤
│ 4. All API calls:                                    │
│    Header: Authorization: Bearer <accessToken>       │
├──────────────────────────────────────────────────────┤
│ 5. On 401 response → try refresh:                    │
│    POST /api/v1/auth/refresh { refreshToken }        │
│    - Update both tokens                              │
│    - Retry original request                          │
├──────────────────────────────────────────────────────┤
│ 6. If refresh fails → logout, re-auth via initData   │
└──────────────────────────────────────────────────────┘
```

---

## Implementation Checklist

### Auth Service (`lib/api/auth.ts`)
- [ ] `loginTelegram()` — sends `tma <initData>` header, returns tokens
- [ ] `refreshToken()` — sends refresh token, returns new token pair
- [ ] `logout()` — revokes current session

### Token Management
- [ ] Store `accessToken` in memory (Redux `authSlice` or variable)
- [ ] Store `refreshToken` in `localStorage`
- [ ] Auto-refresh: intercept 401 responses, call refresh, retry request
- [ ] Queue concurrent requests during refresh (avoid multiple refresh calls)
- [ ] On refresh failure: clear tokens, dispatch `logout()`, re-trigger Telegram auth

### API Client (Axios/Fetch interceptor)
- [ ] Attach `Authorization: Bearer <accessToken>` to every request
- [ ] 401 interceptor with token refresh + request retry
- [ ] Prevent refresh token reuse (single refresh at a time)

### Auth Bootstrap (on app mount)
- [ ] Check if running inside Telegram (`window.Telegram?.WebApp?.initData`)
- [ ] If has `initData` → call `loginTelegram()`
- [ ] If has stored `refreshToken` but no `initData` → try `refreshToken()`
- [ ] Handle `isNewUser: true` — redirect to onboarding if needed

---

## Existing Frontend Code

The frontend already has:
- **`lib/types/auth.ts`** — `TokenPair`, `Identity`, `Session` types
- **`lib/store/authSlice.ts`** — Redux slice with `authStart`, `authSuccess`, `authFailure`, `sessionExpired`, `logout` actions and selectors
- **`lib/telegram/`** — Telegram WebApp SDK hooks (see `docs/superpowers/specs/2026-03-20-telegram-webapp-sdk-design.md`)

Use these existing primitives. Do NOT create parallel auth state management.

---

## Response Format

All backend responses use **camelCase** keys (configured via `CamelModel` base class). No need to transform keys on the frontend.

---

## CORS

Backend allows these origins (configure in `.env`):
```
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

Allowed headers: `Authorization`, `Content-Type`, `X-Request-ID`

---

## Error Response Format

```json
{
  "detail": {
    "code": "INVALID_INIT_DATA",
    "message": "Telegram initData signature verification failed"
  }
}
```

Common error codes for auth:
- `INVALID_INIT_DATA` — bad HMAC signature
- `INIT_DATA_EXPIRED` — initData older than 5 minutes
- `IDENTITY_DEACTIVATED` — account disabled
- `SESSION_EXPIRED` — refresh token TTL exceeded
- `SESSION_REVOKED` — session was revoked
- `REFRESH_TOKEN_REUSE` — old token reused, all sessions revoked
- `INSUFFICIENT_PERMISSIONS` — missing required permission
