import { NextResponse } from 'next/server';

/**
 * Edge proxy — CSRF protection.
 *
 * Next.js 16+ uses the `proxy.js` convention (old `middleware.js` is
 * deprecated). The function is exported as `proxy`. Inside the Telegram
 * Mini App WebView the Origin header may not match the app host
 * (`web.telegram.org` or `null`) — we account for that.
 *
 * CSRF protection layers:
 *  1. SameSite=Lax cookie — on cross-origin POSTs the cookie is not sent (primary)
 *  2. Origin check — if Origin is present AND wrong → block (additional).
 *     If the Telegram WebView sends 'null' or another origin — allowed.
 *  3. initData — signed by Telegram's server and verified by the backend.
 */
export function proxy(req) {
  const method = req.method;

  if (!['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    return NextResponse.next();
  }

  const pathname = req.nextUrl.pathname;
  if (!pathname.startsWith('/api/')) {
    return NextResponse.next();
  }

  const origin = req.headers.get('origin');

  // No Origin header or 'null' (WebView/privacy) — allowed
  if (!origin || origin === 'null') {
    return NextResponse.next();
  }

  let originHost;
  try {
    originHost = new URL(origin).host;
  } catch {
    // If it can't be parsed — WebView 'null' or invalid format
    return NextResponse.next();
  }

  const requestHost =
    req.headers.get('x-forwarded-host') || req.headers.get('host') || req.nextUrl.host;

  // Same-origin — allowed
  if (originHost === requestHost) {
    return NextResponse.next();
  }

  // Telegram WebView origins — allowed
  if (
    originHost.endsWith('.telegram.org') ||
    originHost === 'telegram.org' ||
    originHost.endsWith('.t.me') ||
    originHost === 't.me'
  ) {
    return NextResponse.next();
  }

  // Unknown cross-origin — block
  return NextResponse.json({ error: 'CSRF check failed: origin mismatch' }, { status: 403 });
}

export const config = {
  matcher: '/api/:path*',
};
