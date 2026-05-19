import { cookies } from 'next/headers';

const IS_PROD = process.env.NODE_ENV === 'production';

const ACCESS_TOKEN = 'access_token';
const REFRESH_TOKEN = 'refresh_token';

const COOKIE_DEFAULTS = {
  httpOnly: true,
  secure: IS_PROD,
  sameSite: 'lax',
  path: '/',
};

export function decodeJwtPayload(token) {
  try {
    const base64 = token.split('.')[1];
    const json = Buffer.from(base64, 'base64url').toString('utf-8');
    return JSON.parse(json);
  } catch {
    return null;
  }
}

export function isTokenExpired(payload) {
  if (!payload?.exp) return true;
  return Date.now() >= payload.exp * 1000;
}

/**
 * Read the current access token from cookies.
 *
 * No refresh fallback. The proxy at `src/proxy.js` is the single
 * refresh path — its matcher catches every `/admin/*` navigation AND
 * every `/api/*` BFF route, so by the time downstream handlers reach
 * this helper the cookie has already been rotated when needed.
 *
 * Centralising refresh in one runtime eliminates the cross-runtime
 * race that used to fire when Edge proxy and this helper both POSTed
 * `/auth/refresh` with the same refresh_token, and the second one was
 * rejected as `REFRESH_TOKEN_REUSE` → user kicked to login. The
 * `/api/auth/(login|refresh|logout)` bypass paths in the proxy keep
 * those endpoints reachable without an access token.
 */
export async function getAccessToken() {
  const store = await cookies();
  return store.get(ACCESS_TOKEN)?.value ?? null;
}

export async function getRefreshToken() {
  const store = await cookies();
  return store.get(REFRESH_TOKEN)?.value ?? null;
}

export function setAuthCookiesOnResponse(response, accessToken, refreshToken) {
  response.cookies.set(ACCESS_TOKEN, accessToken, {
    ...COOKIE_DEFAULTS,
    maxAge: 900,
  });
  response.cookies.set(REFRESH_TOKEN, refreshToken, {
    ...COOKIE_DEFAULTS,
    maxAge: 2_592_000,
  });
  return response;
}

export function clearAuthCookiesOnResponse(response) {
  response.cookies.set(ACCESS_TOKEN, '', { ...COOKIE_DEFAULTS, maxAge: 0 });
  response.cookies.set(REFRESH_TOKEN, '', { ...COOKIE_DEFAULTS, maxAge: 0 });
  return response;
}
