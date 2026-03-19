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

  try {
    const res = await fetch(`${BACKEND_URL}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refreshToken }),
    });

    if (!res.ok) {
      const response = NextResponse.redirect(loginUrl);
      response.cookies.set('access_token', '', { path: '/', maxAge: 0 });
      response.cookies.set('refresh_token', '', { path: '/', maxAge: 0 });
      return response;
    }

    const data = await res.json();
    const isProd = process.env.NODE_ENV === 'production';

    const response = NextResponse.next();
    response.cookies.set('access_token', data.accessToken, {
      httpOnly: true,
      secure: isProd,
      sameSite: 'lax',
      path: '/',
      maxAge: 900,
    });
    response.cookies.set('refresh_token', data.refreshToken, {
      httpOnly: true,
      secure: isProd,
      sameSite: 'lax',
      path: '/',
      maxAge: 2_592_000,
    });
    return response;
  } catch {
    const response = NextResponse.redirect(loginUrl);
    response.cookies.set('access_token', '', { path: '/', maxAge: 0 });
    response.cookies.set('refresh_token', '', { path: '/', maxAge: 0 });
    return response;
  }
}

export const config = {
  matcher: ['/admin/:path*'],
};
