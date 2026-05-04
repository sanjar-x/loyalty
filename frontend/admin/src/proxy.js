import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL;

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

// Per-instance dedup of in-flight refresh attempts. Refresh tokens are
// one-time on the backend, so two simultaneous proxy invocations with
// the same refresh_token would race — one wins, the other gets
// REFRESH_TOKEN_REUSE and the user is logged out. We collapse them by
// awaiting the same promise. On serverless this only deduplicates within a
// single warm instance; cross-instance races still need a backend grace
// window, but this kills the dominant case (parallel tabs / prefetch).
const inflight = new Map();

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
      if (!res.ok) return { ok: false };
      const data = await res.json().catch(() => null);
      if (
        !data ||
        !isNonEmptyString(data.accessToken) ||
        !isNonEmptyString(data.refreshToken)
      ) {
        return { ok: false };
      }
      return {
        ok: true,
        accessToken: data.accessToken,
        refreshToken: data.refreshToken,
      };
    } catch {
      return { ok: false };
    } finally {
      // Drop the entry shortly after — a successful response invalidates the
      // old refresh anyway, but a small tail keeps near-simultaneous waiters
      // glued to the same result.
      setTimeout(() => inflight.delete(refreshToken), 1000).unref?.();
    }
  })();
  inflight.set(refreshToken, promise);
  return promise;
}

export async function proxy(request) {
  const loginUrl = new URL('/login', request.url);

  const accessToken = request.cookies.get('access_token')?.value;

  // No access token — redirect to login
  if (!accessToken) {
    return NextResponse.redirect(loginUrl);
  }

  const payload = decodePayload(accessToken);

  // Token not expired — pass through
  if (payload && !isExpired(payload)) {
    return NextResponse.next();
  }

  // Token expired — try to refresh directly against backend
  const refreshToken = request.cookies.get('refresh_token')?.value;
  if (!refreshToken) {
    const response = NextResponse.redirect(loginUrl);
    response.cookies.set('access_token', '', { path: '/', maxAge: 0 });
    return response;
  }

  const result = await refreshOnce(refreshToken);
  if (!result.ok) {
    const response = NextResponse.redirect(loginUrl);
    response.cookies.set('access_token', '', { path: '/', maxAge: 0 });
    response.cookies.set('refresh_token', '', { path: '/', maxAge: 0 });
    return response;
  }

  const isProd = process.env.NODE_ENV === 'production';
  const response = NextResponse.next();
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
  matcher: ['/admin/:path*'],
};
