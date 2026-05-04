Sen Next.js + Telegram Mini App loyihasida ishlayapsan. Quyida Telegram orqali autentifikatsiya tizimining to'liq arxitekturasi va har bir qatlam batafsil tavsiflangan. Shu ma'lumotlar
asosida ishlashni davom ettir.

## ARXITEKTURA: BFF (Backend-For-Frontend) Pattern

Tokenlar brauzerda JS ga ko'rinmaydi — faqat HttpOnly cookie sifatida saqlanadi. Barcha backend so'rovlar Next.js API route proxy orqali o'tadi.

## AUTH FLOW (qadam-baqadam)

### 1. Telegram SDK Initialization

- `TelegramSdkProvider` (src/features/telegram/provider.tsx) — React context orqali `window.Telegram.WebApp` ni o'raydi.
- `useTelegramSdkRuntime` hook 2 soniya ichida `window.Telegram.WebApp` paydo bo'lishini polling qiladi (50ms interval). Topilsa `webApp.ready()` chaqiriladi va `initData`, `user`,
  `platform`, `version` context ga yoziladi. Topilmasa fallback state yaratiladi.
- `TelegramAppShell` (src/app/\_providers/telegram-app-shell.tsx) — provider + auth bootstrap + UI controllerni birlashtiradi.

### 2. Client-side Auth Bootstrap

- `TelegramAuthBootstrap` (src/features/auth/components/telegram-auth-bootstrap.tsx) — renderless component (returns null).
- `useTelegram()` hookdan `initData` va `isReady` oladi, `useAuthStore` dan `authStatus` kuzatadi.
- Qachonki `isReady === true` VA `authStatus === 'idle' | 'expired'` bo'lsa, avtomatik auth boshlaydi.
- Deduplication uchun `inFlightSourceRef` va `failedSourceRef` ref'lar ishlatiladi — bir xil initData bilan takroriy so'rov yuborilmaydi.
- Auth request: `POST /api/auth/telegram` with `{ initData }` (credentials: 'include').
- Muvaffaqiyatda: `useAuthStore.authSuccess({ isNewUser })` + `queryClient.invalidateQueries()`.
- Xatoda: `useAuthStore.authFailure(errorMessage)`.

### 3. BFF Auth Route (Server-side)

- Fayl: `src/app/api/auth/telegram/route.ts` — POST handler.
- Request body dan `initData` string olinadi.
- Backend ga forward qilinadi: `POST ${BACKEND_API_BASE_URL}/api/v1/auth/telegram` header bilan: `authorization: tma ${initData}`.
- Backend javobidan `{ accessToken, refreshToken, isNewUser }` olinadi.
- `setTokenCookies(res, accessToken, refreshToken)` orqali HttpOnly cookie'lar o'rnatiladi.
- Clientga faqat `{ ok: true, isNewUser }` qaytariladi (tokenlar HECH QACHON JSON body da qaytmaydi).

### 4. Cookie Management

- Fayl: `src/features/auth/lib/cookie-helpers.ts`
- Cookie nomlari: `lm_access_token`, `lm_refresh_token` (src/features/auth/lib/cookies.ts da const).
- Access token: HttpOnly, SameSite=Lax, Secure (prod), Path=/, Max-Age=900 (15 daqiqa).
- Refresh token: HttpOnly, SameSite=Lax, Secure (prod), Path=/, Max-Age=604800 (7 kun).
- `getCookieDomain()` — COOKIE_DOMAIN env dan domain olinadi, localhost/vercel.app uchun undefined qaytaradi.
- `shouldSecureCookie()` — production yoki Vercel preview da true.

### 5. API Proxy (BFF)

- Fayl: `src/app/api/backend/[...path]/route.ts`
- Barcha client HTTP so'rovlari `/api/backend/*` orqali o'tadi.
- Cookie'dan access token olinadi: `cookies().get('lm_access_token')`.
- Backend ga `Authorization: Bearer ${token}` header bilan forward qilinadi.
- Faqat xavfsiz headerlar forward qilinadi (accept, content-type, accept-language).
- 25s timeout, abort controller bilan.

### 6. Token Refresh

- Fayl: `src/app/api/auth/refresh/route.ts`
- Cookie'dan `lm_refresh_token` olinadi.
- Backend ga: `POST ${BACKEND_API_BASE_URL}/api/v1/auth/refresh` body: `{ refreshToken }`.
- Muvaffaqiyatda yangi token pair cookie ga yoziladi.
- Xatoda cookie'lar tozalanadi (`clearTokenCookies`).

### 7. Client-side Auto-Refresh (apiClient)

- Fayl: `src/lib/api-client.ts`
- `ky` HTTP client ishlatiladi, prefixUrl: `/api/backend`.
- `afterResponse` hook: agar 401 kelsa VA auth route bo'lmasa → `/api/auth/refresh` POST qiladi.
- Mutex pattern: bir vaqtda faqat bitta refresh so'rov (concurrent 401 lar birlashtiriladi).
- Refresh muvaffaqiyatli bo'lsa — asl so'rov qayta yuboriladi.
- Refresh muvaffaqiyatsiz bo'lsa — `emitAuthExpired()` chaqiriladi.

### 8. Auth Expiry Event System

- Fayl: `src/lib/auth-events.ts`
- `EventTarget` asosidagi sodda pub/sub: `emitAuthExpired()` → `onAuthExpired(listener)`.
- `TelegramAuthBootstrap` `onAuthExpired` ga subscribe bo'ladi va `useAuthStore.sessionExpired()` chaqiradi.
- Bu authStatus ni `expired` ga o'tkazadi → bootstrap qayta initData bilan auth qiladi (auto re-login).

### 9. Auth State Management (Zustand)

- Fayl: `src/features/auth/store.ts`
- State: `{ status: AuthStatus, isNewUser: boolean, error: string | null }`
- AuthStatus: 'idle' → 'loading' → 'authenticated' | 'error' | 'expired' | 'logged_out'
- Actions: authStart(), authSuccess(), authFailure(), sessionExpired(), logout()
- DevTools integratsiya mavjud.

### 10. Logout

- Fayl: `src/app/api/auth/logout/route.ts`
- Best-effort backend logout: `POST ${BACKEND_API_BASE_URL}/api/v1/auth/logout` Bearer token bilan.
- Cookie'lar har doim tozalanadi (backend javobidan qat'i nazar).
- Client-side: `src/features/auth/lib/cookies.ts` dagi `logout()` funksiyasi `/api/auth/logout` ga POST qiladi.

### 11. CSRF Himoyasi

- Fayl: `src/proxy.ts` — edge middleware.
- Barcha state-changing (POST/PUT/PATCH/DELETE) API so'rovlarda Origin header tekshiriladi.
- Origin host ≠ request host bo'lsa → 403 qaytariladi.
- SameSite=Lax cookie + Origin check = ikki qatlamli CSRF himoya.

### 12. Debug Mode (Development only)

- `BROWSER_DEBUG_AUTH=true` va `NEXT_PUBLIC_BROWSER_DEBUG_AUTH=true` env bilan yoqiladi.
- Localhost da Telegram SDK bo'lmasa ham auth ishlaydi.
- Mock user: `{ tg_id: '0000000000', username: 'debug_user' }`.
- BFF route avval backendga debug request yuborishga harakat qiladi, muvaffaqiyatsiz bo'lsa mock token yaratadi: `debug_${tg_id}_${timestamp}`.

### 13. Environment Variables

- `BACKEND_API_BASE_URL` (required) — backend URL (masalan: http://localhost:8080)
- `COOKIE_DOMAIN` (optional) — cookie domain
- `BROWSER_DEBUG_AUTH` / `NEXT_PUBLIC_BROWSER_DEBUG_AUTH` — debug auth rejimi
- Validatsiya: `@t3-oss/env-nextjs` + zod (src/env.ts)

## FAYL XARITASI

src/features/auth/ ├── index.ts — public API (re-exports) ├── types.ts — AuthStatus, TokenPair, TelegramAuthResponse ├── store.ts — Zustand auth state ├── server.ts — server-only
re-exports (cookie-helpers + debug) ├── components/ │ └── telegram-auth-bootstrap.tsx — renderless auto-auth component └── lib/ ├── cookies.ts — cookie name constants + logout() ├──
cookie-helpers.ts — setTokenCookies, clearTokenCookies, serialize └── debug.ts — browser debug auth utilities

src/app/api/auth/ ├── telegram/route.ts — POST: Telegram auth BFF endpoint ├── refresh/route.ts — POST: token refresh └── logout/route.ts — POST: logout

src/app/api/backend/[...path]/route.ts — universal API proxy src/lib/api-client.ts — ky client with auto-refresh src/lib/auth-events.ts — auth expiry event bus src/proxy.ts — edge
middleware (CSRF + security headers) src/features/telegram/ — Telegram SDK provider + hooks

## QOIDALAR

1.  Tokenlar FAQAT HttpOnly cookie da — client JS ularga kirmasin.
2.  Har qanday backendga so'rov `/api/backend/` proxy orqali o'tsin.
3.  Auth flow avtomatik — `TelegramAuthBootstrap` component foydalanuvchi aralashuvisiz ishlaydi.
4.  Token muddati tugasa — refresh → muvaffaqiyatsiz bo'lsa → `expired` state → auto re-auth initData bilan.
5.  Debug mode FAQAT development da ishlaydi, production da `isBrowserDebugAuthEnabled()` har doim false.
