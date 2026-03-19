import { NextResponse } from "next/server";

const ACCESS_COOKIE = "lm_access_token";

function isProduction() {
  return process.env.NODE_ENV === "production";
}

function getCookieDomain() {
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

function serializeCookie(name, value, opts) {
  const parts = [`${encodeURIComponent(name)}=${encodeURIComponent(value)}`];
  if (opts.maxAge != null) parts.push(`Max-Age=${Math.floor(opts.maxAge)}`);
  if (opts.domain) parts.push(`Domain=${opts.domain}`);
  if (opts.path) parts.push(`Path=${opts.path}`);
  if (opts.httpOnly) parts.push("HttpOnly");
  if (opts.secure) parts.push("Secure");
  if (opts.sameSite) parts.push(`SameSite=${opts.sameSite}`);
  return parts.join("; ");
}

export async function POST() {
  const res = NextResponse.json({ ok: true }, { status: 200 });
  res.headers.append(
    "Set-Cookie",
    serializeCookie(ACCESS_COOKIE, "", {
      httpOnly: true,
      secure: isProduction(),
      sameSite: "Lax",
      path: "/",
      domain: getCookieDomain(),
      maxAge: 0,
    }),
  );
  return res;
}
