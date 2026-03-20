import { NextResponse, type NextRequest } from "next/server";

function isPublicPath(pathname: string): boolean {
  // API routes handle their own auth logic
  if (pathname.startsWith("/api/")) return true;
  // Static assets
  if (pathname.startsWith("/_next/")) return true;
  if (pathname.startsWith("/favicon")) return true;
  return false;
}

export function middleware(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;

  if (isPublicPath(pathname)) {
    return NextResponse.next();
  }

  // In a Telegram Mini App we do NOT redirect unauthenticated users.
  // The app must load first so TelegramAuthBootstrap can capture initData
  // from window.Telegram.WebApp and complete the auth flow.
  // After auth completes (cookies set), subsequent requests carry the JWT.
  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico).*)",
  ],
};
