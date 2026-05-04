import { NextResponse } from "next/server";

/**
 * Edge proxy — CSRF himoyasi.
 *
 * Next.js 16+ `proxy.js` konvensiyasi (eski `middleware.js` deprecated).
 * Funksiya `proxy` deb eksport qilinadi. Telegram Mini App WebView ichida
 * Origin headeri app hostiga mos kelmasligi mumkin (`web.telegram.org` yoki
 * `null`) — buni hisobga olamiz.
 *
 * CSRF himoya qatlamlari:
 *  1. SameSite=Lax cookie — cross-origin POST da cookie yuborilmaydi (asosiy)
 *  2. Origin check — agar Origin mavjud VA noto'g'ri → block (qo'shimcha)
 *     Telegram WebView 'null' yoki boshqa origin yuborsa — ruxsat beriladi
 *  3. initData — Telegram serveri tomonidan imzolangan, backend tekshiradi
 */
export function proxy(req) {
  const method = req.method;

  if (!["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    return NextResponse.next();
  }

  const pathname = req.nextUrl.pathname;
  if (!pathname.startsWith("/api/")) {
    return NextResponse.next();
  }

  const origin = req.headers.get("origin");

  // Origin header yo'q yoki 'null' (WebView/privacy) — ruxsat
  if (!origin || origin === "null") {
    return NextResponse.next();
  }

  let originHost;
  try {
    originHost = new URL(origin).host;
  } catch {
    // Parse qilib bo'lmasa — WebView 'null' yoki noto'g'ri format
    return NextResponse.next();
  }

  const requestHost =
    req.headers.get("x-forwarded-host") ||
    req.headers.get("host") ||
    req.nextUrl.host;

  // Same-origin — ruxsat
  if (originHost === requestHost) {
    return NextResponse.next();
  }

  // Telegram WebView originlari — ruxsat
  if (
    originHost.endsWith(".telegram.org") ||
    originHost === "telegram.org" ||
    originHost.endsWith(".t.me") ||
    originHost === "t.me"
  ) {
    return NextResponse.next();
  }

  // Noma'lum cross-origin — block
  return NextResponse.json(
    { error: "CSRF check failed: origin mismatch" },
    { status: 403 },
  );
}

export const config = {
  matcher: "/api/:path*",
};
