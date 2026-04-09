import { NextResponse } from "next/server";

import { ACCESS_COOKIE, REFRESH_COOKIE } from "./cookies";

// Re-export cookie names so BFF routes can import everything from one module
export { ACCESS_COOKIE, REFRESH_COOKIE };

// ---------------------------------------------------------------------------
// Environment helpers
// ---------------------------------------------------------------------------

export function getBackendBaseUrl(): string {
  const raw = process.env.BACKEND_API_BASE_URL;
  if (!raw || typeof raw !== "string" || !raw.trim()) {
    throw new Error("Missing BACKEND_API_BASE_URL");
  }
  return raw.trim().replace(/\/+$/, "");
}

export function isProduction(): boolean {
  return process.env.NODE_ENV === "production";
}

/** Whether cookies should carry the Secure flag (HTTPS-only). */
export function shouldSecureCookie(): boolean {
  if (process.env.NODE_ENV === "production") return true;
  // Vercel preview deployments are always HTTPS
  if (process.env.VERCEL_ENV === "preview") return true;
  return false;
}

export function getCookieDomain(): string | undefined {
  const domain = process.env.COOKIE_DOMAIN;
  if (typeof domain !== "string") return undefined;
  const d = domain.trim();
  if (!d) return undefined;

  if (
    d.includes("://") ||
    d.includes("/") ||
    d.includes(":") ||
    d.includes(" ")
  ) {
    return undefined;
  }

  const normalized = d.startsWith(".") ? d.slice(1) : d;
  if (normalized === "localhost" || normalized === "vercel.app")
    return undefined;

  return d;
}

// ---------------------------------------------------------------------------
// Cookie serialization
// ---------------------------------------------------------------------------

interface CookieOptions {
  maxAge?: number;
  domain?: string;
  path?: string;
  httpOnly?: boolean;
  secure?: boolean;
  sameSite?: string;
}

export function serializeCookie(
  name: string,
  value: string,
  opts: CookieOptions,
): string {
  const parts = [`${encodeURIComponent(name)}=${encodeURIComponent(value)}`];
  if (opts.maxAge !== undefined) parts.push(`Max-Age=${Math.floor(opts.maxAge)}`);
  if (opts.domain) parts.push(`Domain=${opts.domain}`);
  if (opts.path) parts.push(`Path=${opts.path}`);
  if (opts.httpOnly) parts.push("HttpOnly");
  if (opts.secure) parts.push("Secure");
  if (opts.sameSite) parts.push(`SameSite=${opts.sameSite}`);
  return parts.join("; ");
}

export function clearCookieHeader(name: string): string {
  return serializeCookie(name, "", {
    maxAge: 0,
    path: "/",
    httpOnly: true,
    secure: shouldSecureCookie(),
    sameSite: "Lax",
    domain: getCookieDomain(),
  });
}

export function setTokenCookies(
  res: NextResponse,
  accessToken: string,
  refreshToken: string,
): void {
  const domain = getCookieDomain();
  const secure = shouldSecureCookie();

  res.headers.append(
    "Set-Cookie",
    serializeCookie(ACCESS_COOKIE, accessToken, {
      httpOnly: true,
      secure,
      sameSite: "Lax",
      path: "/",
      domain,
      maxAge: 900, // 15 minutes
    }),
  );

  res.headers.append(
    "Set-Cookie",
    serializeCookie(REFRESH_COOKIE, refreshToken, {
      httpOnly: true,
      secure,
      sameSite: "Lax",
      path: "/",
      domain,
      maxAge: 60 * 60 * 24 * 7, // 7 days
    }),
  );
}

export function clearTokenCookies(res: NextResponse): void {
  res.headers.append("Set-Cookie", clearCookieHeader(ACCESS_COOKIE));
  res.headers.append("Set-Cookie", clearCookieHeader(REFRESH_COOKIE));
}
