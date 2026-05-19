import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL;

// Endpoints that must NOT go through the auth gate:
//   - login: no token yet
//   - logout: must succeed even from a half-dead session
//
// `/api/auth/refresh` is intentionally absent — that route is now a 410
// stub (PR #39 made the Edge proxy the sole refresh path). Letting the
// stub go through the auth gate means any regressive client call gets
// either a 401 (no token) or the route's own 410 with a clear code,
// instead of a free pass that could quietly re-introduce the
// cross-runtime race.
const AUTH_BYPASS_PATHS = new Set(['/api/auth/login', '/api/auth/logout']);

// Path prefixes that bypass the auth gate. `/api/invitations/*` is
// public on purpose — the invitee landing on /invite/{token} has no
// session yet, and the validate/accept handlers self-manage their
// security (Origin check + the accept handler sets cookies). Keep
// prefix-matching narrow: an exact-set entry per nested path would be
// brittle as the route tree grows.
const AUTH_BYPASS_PREFIXES = ['/api/invitations/'];

function isAuthBypassed(pathname) {
  if (AUTH_BYPASS_PATHS.has(pathname)) return true;
  for (const prefix of AUTH_BYPASS_PREFIXES) {
    if (pathname.startsWith(prefix)) return true;
  }
  return false;
}

function decodePayload(token) {
  try {
    const base64 = token.split('.')[1];
    const json = atob(base64.replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(json);
  } catch {
    return null;
  }
}

function isExpired(payload) {
  if (!payload?.exp) return true;
  return Date.now() >= payload.exp * 1000;
}

function isNonEmptyString(v) {
  return typeof v === 'string' && v.length > 0;
}

// Per-instance dedup of in-flight refresh attempts.
//
// Refresh tokens are one-time on the backend, so two simultaneous proxy
// invocations with the same refresh_token would race — one wins, the
// other gets REFRESH_TOKEN_REUSE and the user is logged out. Collapse
// them by awaiting the same promise.
//
// Why the proxy is now the *only* refresh path: the matcher below
// catches both /admin/* navigation AND every BFF route call, so by the
// time downstream code reads cookies via `getAccessToken()`, the access
// token has already been rotated if it was expired. That eliminates
// the cross-runtime race that used to fire when Edge proxy and
// Node-runtime BFF helpers both POSTed /auth/refresh with the same
// refresh_token from cookies and the second one was rejected.
//
// The 5s TTL on the dedup entry covers the tail end of a request batch
// — long enough for parallel tabs / prefetched links that hit the
// proxy after the primary navigation has already settled.
const inflight = new Map();
const REFRESH_DEDUP_TTL_MS = 5000;

// Refresh outcome shape:
//   { ok: true,  accessToken, refreshToken }
//   { ok: false, transient: boolean, status: number, code: string|null }
//
// `transient` is the load-bearing field: a 5xx / network blip from the
// backend does NOT invalidate the user's tokens, so we must not clear the
// cookies in that case — the user retries on next interaction and the
// refresh re-runs. Only auth-meaningful 4xx (SESSION_EXPIRED,
// REFRESH_TOKEN_REUSE, SESSION_REVOKED, …) actually kill the session.
function refreshOnce(refreshToken) {
  const existing = inflight.get(refreshToken);
  if (existing) return existing;
  const promise = (async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refreshToken }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        const code = data?.error?.code ?? null;
        const isPermanent = res.status >= 400 && res.status < 500;
        return {
          ok: false,
          transient: !isPermanent,
          status: res.status,
          code,
        };
      }
      const data = await res.json().catch(() => null);
      if (
        !data ||
        !isNonEmptyString(data.accessToken) ||
        !isNonEmptyString(data.refreshToken)
      ) {
        // Backend said 200 but body is garbage — treat as transient so we
        // don't clobber the user's still-valid refresh_token.
        return {
          ok: false,
          transient: true,
          status: 502,
          code: 'INVALID_REFRESH_RESPONSE',
        };
      }
      return {
        ok: true,
        accessToken: data.accessToken,
        refreshToken: data.refreshToken,
      };
    } catch {
      return {
        ok: false,
        transient: true,
        status: 0,
        code: 'NETWORK_ERROR',
      };
    } finally {
      setTimeout(
        () => inflight.delete(refreshToken),
        REFRESH_DEDUP_TTL_MS,
      ).unref?.();
    }
  })();
  inflight.set(refreshToken, promise);
  return promise;
}

export async function proxy(request) {
  const { pathname } = new URL(request.url);

  // Bypass paths that must work without an access_token (login, logout,
  // public invitation endpoints) — short-circuit before the auth gate
  // so they don't redirect anonymous callers in an endless loop.
  // /api/auth/refresh is intentionally NOT here: that route now returns
  // 410 and refresh is owned by this proxy.
  if (isAuthBypassed(pathname)) {
    return NextResponse.next();
  }

  const isApiRoute = pathname.startsWith('/api/');
  // For /admin/* navigation we send the user to /login; for /api/*
  // calls we return 401 JSON so the browser's apiClient surfaces the
  // error without a hard navigation.
  const failResponse = isApiRoute
    ? () =>
        NextResponse.json(
          {
            error: {
              code: 'UNAUTHORIZED',
              message: 'Not authenticated',
              details: {},
            },
          },
          { status: 401 },
        )
    : () => NextResponse.redirect(new URL('/login', request.url));

  const accessToken = request.cookies.get('access_token')?.value;

  // No access token — redirect / 401
  if (!accessToken) {
    return failResponse();
  }

  const payload = decodePayload(accessToken);

  // Token not expired — pass through
  if (payload && !isExpired(payload)) {
    return NextResponse.next();
  }

  // Token expired — try to refresh directly against backend
  const refreshToken = request.cookies.get('refresh_token')?.value;
  if (!refreshToken) {
    const response = failResponse();
    response.cookies.set('access_token', '', { path: '/', maxAge: 0 });
    return response;
  }

  const result = await refreshOnce(refreshToken);
  if (!result.ok) {
    // Transient (5xx, network, malformed body): user's tokens are still
    // valid, the backend is just unreachable. Surface a 503 to API
    // callers and let SSR navigation render with the expired token —
    // the next interaction triggers another proxy pass which will
    // either succeed or escalate to a permanent failure.
    if (result.transient) {
      if (isApiRoute) {
        return NextResponse.json(
          {
            error: {
              code: result.code ?? 'SERVICE_UNAVAILABLE',
              message: 'Auth refresh temporarily unavailable',
              details: { status: result.status },
            },
          },
          { status: 503 },
        );
      }
      return NextResponse.next();
    }
    // Permanent (auth 4xx — SESSION_EXPIRED, REFRESH_TOKEN_REUSE, …):
    // the session is genuinely dead, clear the cookies and kick to
    // /login. Carry the backend code as `reason` so the login page can
    // explain why the user landed there.
    const response = isApiRoute
      ? failResponse()
      : NextResponse.redirect(
          new URL(
            `/login${result.code ? `?reason=${encodeURIComponent(result.code)}` : ''}`,
            request.url,
          ),
        );
    response.cookies.set('access_token', '', { path: '/', maxAge: 0 });
    response.cookies.set('refresh_token', '', { path: '/', maxAge: 0 });
    return response;
  }

  // Refresh succeeded — propagate the new tokens to BOTH the browser
  // (via Set-Cookie on the response) and the downstream handler (by
  // mutating request.cookies in place, so getAccessToken() reads the
  // fresh token in the same request lifecycle).
  request.cookies.set('access_token', result.accessToken);
  request.cookies.set('refresh_token', result.refreshToken);

  const isProd = process.env.NODE_ENV === 'production';
  const response = NextResponse.next({ request });
  response.cookies.set('access_token', result.accessToken, {
    httpOnly: true,
    secure: isProd,
    sameSite: 'lax',
    path: '/',
    maxAge: 900,
  });
  response.cookies.set('refresh_token', result.refreshToken, {
    httpOnly: true,
    secure: isProd,
    sameSite: 'lax',
    path: '/',
    maxAge: 2_592_000,
  });
  return response;
}

export const config = {
  // /admin/* covers SSR navigation; /api/* covers every BFF route. We
  // exclude /api/auth/(login|logout) at the top of the handler because
  // regex matchers in Next.js 16 can't reliably express the negation
  // across nested segments — the runtime check is simpler.
  matcher: ['/admin/:path*', '/api/:path*'],
};
