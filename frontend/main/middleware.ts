import { NextResponse, type NextRequest } from "next/server";

/**
 * Edge middleware for the Telegram Mini App.
 *
 * - Adds security headers to all responses.
 * - Validates Origin header on session-mutation POST routes (CSRF defense-in-depth).
 *
 * NOTE: We do NOT redirect unauthenticated users. In a Telegram Mini App the
 * page must load first so TelegramAuthBootstrap can capture initData from
 * window.Telegram.WebApp and complete the auth flow.
 */

const SESSION_MUTATION_PREFIX = "/api/session/";

export function middleware(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;

  // CSRF defense-in-depth for session-mutation routes.
  // SameSite=Lax blocks most cross-site POSTs, but checking Origin adds a
  // second layer (e.g. against browser bugs or misconfigured proxies).
  if (
    request.method === "POST" &&
    pathname.startsWith(SESSION_MUTATION_PREFIX)
  ) {
    const origin = request.headers.get("origin");
    if (origin) {
      const requestHost = request.nextUrl.host; // host includes port
      try {
        const originHost = new URL(origin).host;
        if (originHost !== requestHost) {
          return NextResponse.json(
            { error: "Cross-origin request blocked" },
            { status: 403 },
          );
        }
      } catch {
        return NextResponse.json(
          { error: "Invalid Origin header" },
          { status: 403 },
        );
      }
    }
  }

  const response = NextResponse.next();

  // Security headers
  response.headers.set("X-Content-Type-Options", "nosniff");
  // Use SAMEORIGIN instead of DENY — Telegram's web client (web.telegram.org)
  // may embed Mini Apps in iframes.
  response.headers.set("X-Frame-Options", "SAMEORIGIN");
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");

  return response;
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico).*)",
  ],
};
