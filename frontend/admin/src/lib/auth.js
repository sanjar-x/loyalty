import { cookies } from 'next/headers';

const IS_PROD = process.env.NODE_ENV === 'production';
const BACKEND_URL = process.env.BACKEND_URL;

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
  // Refresh 30 seconds before actual expiry to avoid race conditions
  return Date.now() >= (payload.exp - 30) * 1000;
}

export async function getAccessToken() {
  const store = await cookies();
  const accessToken = store.get(ACCESS_TOKEN)?.value;

  if (!accessToken) return null;

  const payload = decodeJwtPayload(accessToken);
  if (payload && !isTokenExpired(payload)) {
    return accessToken;
  }

  // Token expired or about to expire — try refresh
  const refreshToken = store.get(REFRESH_TOKEN)?.value;
  if (!refreshToken) return null;

  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refreshToken }),
    });

    if (!res.ok) return null;

    const data = await res.json();

    store.set(ACCESS_TOKEN, data.accessToken, {
      ...COOKIE_DEFAULTS,
      maxAge: 900,
    });
    store.set(REFRESH_TOKEN, data.refreshToken, {
      ...COOKIE_DEFAULTS,
      maxAge: 2_592_000,
    });

    return data.accessToken;
  } catch {
    return null;
  }
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
