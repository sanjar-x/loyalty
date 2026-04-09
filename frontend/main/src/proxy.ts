import { type NextRequest, NextResponse } from 'next/server';

/**
 * Edge middleware for the Telegram Mini App.
 *
 * - Adds security headers to all responses.
 * - Validates Origin header on auth-mutation POST routes (CSRF defense-in-depth).
 *
 * NOTE: We do NOT redirect unauthenticated users. In a Telegram Mini App the
 * page must load first so TelegramAuthBootstrap can capture initData from
 * window.Telegram.WebApp and complete the auth flow.
 */

const STATE_CHANGING_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);
const API_PREFIX = '/api/';

export function proxy(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;

  // CSRF defense-in-depth for all state-changing API requests.
  // SameSite=Lax blocks most cross-site POSTs, but checking Origin adds a
  // second layer (e.g. against browser bugs or misconfigured proxies).
  if (STATE_CHANGING_METHODS.has(request.method) && pathname.startsWith(API_PREFIX)) {
    const origin = request.headers.get('origin');

    if (!origin) {
      return NextResponse.json({ error: 'Missing Origin header' }, { status: 403 });
    }

    const requestHost = request.nextUrl.host;
    try {
      const originHost = new URL(origin).host;
      if (originHost !== requestHost) {
        return NextResponse.json({ error: 'Cross-origin request blocked' }, { status: 403 });
      }
    } catch {
      return NextResponse.json({ error: 'Invalid Origin header' }, { status: 403 });
    }
  }

  const response = NextResponse.next();

  // Security headers
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('X-Frame-Options', 'SAMEORIGIN');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');

  return response;
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)'],
};
