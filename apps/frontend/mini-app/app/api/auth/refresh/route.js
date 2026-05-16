import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

import { REFRESH_COOKIE } from '@/lib/features/auth/lib/cookies';
import { setTokenCookies, clearTokenCookies } from '@/lib/features/auth/lib/cookie-helpers';
import { getBackendBaseUrl } from '@/lib/api/server/backendBaseUrl';

export async function POST() {
  let backendBase;
  try {
    backendBase = getBackendBaseUrl();
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'Server config error' },
      { status: 500 }
    );
  }

  let refreshToken;
  try {
    const cookieJar = await cookies();
    refreshToken = cookieJar.get(REFRESH_COOKIE)?.value || '';
  } catch {
    refreshToken = '';
  }

  if (!refreshToken) {
    return NextResponse.json({ error: 'No refresh token' }, { status: 401 });
  }

  let upstreamRes;
  try {
    upstreamRes = await fetch(`${backendBase}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: {
        accept: 'application/json',
        'content-type': 'application/json',
      },
      body: JSON.stringify({ refreshToken }),
    });
  } catch (e) {
    return NextResponse.json({ error: 'Backend unreachable', hint: e?.message }, { status: 502 });
  }

  const text = await upstreamRes.text();
  let json = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    json = null;
  }

  if (!upstreamRes.ok) {
    // Refresh failed — cookie'lar tozalanadi
    const res = NextResponse.json(
      { error: 'Refresh failed', status: upstreamRes.status, details: json ?? text },
      { status: upstreamRes.status === 401 ? 401 : 502 }
    );
    clearTokenCookies(res);
    return res;
  }

  const newAccessToken = json?.accessToken;
  const newRefreshToken = json?.refreshToken;

  if (typeof newAccessToken !== 'string' || !newAccessToken) {
    return NextResponse.json({ error: 'Backend did not return accessToken' }, { status: 502 });
  }

  const res = NextResponse.json({ ok: true }, { status: 200 });
  setTokenCookies(res, newAccessToken, newRefreshToken);
  return res;
}
