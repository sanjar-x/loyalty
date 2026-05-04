import { ACCESS_COOKIE, REFRESH_COOKIE } from "./cookies";

const ACCESS_MAX_AGE = 900; // 15 daqiqa
const REFRESH_MAX_AGE = 604_800; // 7 kun

/* ─── Helpers ─── */

export function getCookieDomain() {
  const domain = process.env.COOKIE_DOMAIN;
  if (typeof domain !== "string") return undefined;
  const d = domain.trim();
  if (!d) return undefined;
  if (d.includes("://") || d.includes("/") || d.includes(":") || d.includes(" "))
    return undefined;
  const normalized = d.startsWith(".") ? d.slice(1) : d;
  if (normalized === "localhost" || normalized === "vercel.app") return undefined;
  return d;
}

export function shouldSecureCookie() {
  if (process.env.NODE_ENV === "production") return true;
  if (process.env.VERCEL) return true;
  return false;
}

export function serializeCookie(name, value, opts) {
  const parts = [`${encodeURIComponent(name)}=${encodeURIComponent(value)}`];
  if (opts.maxAge != null) parts.push(`Max-Age=${Math.floor(opts.maxAge)}`);
  if (opts.domain) parts.push(`Domain=${opts.domain}`);
  if (opts.path) parts.push(`Path=${opts.path}`);
  if (opts.httpOnly) parts.push("HttpOnly");
  if (opts.secure) parts.push("Secure");
  if (opts.sameSite) parts.push(`SameSite=${opts.sameSite}`);
  return parts.join("; ");
}

/* ─── Public API ─── */

function baseCookieOpts() {
  return {
    httpOnly: true,
    secure: shouldSecureCookie(),
    sameSite: "Lax",
    path: "/",
    domain: getCookieDomain(),
  };
}

export function setTokenCookies(res, accessToken, refreshToken) {
  const opts = baseCookieOpts();

  res.headers.append(
    "Set-Cookie",
    serializeCookie(ACCESS_COOKIE, accessToken, {
      ...opts,
      maxAge: ACCESS_MAX_AGE,
    }),
  );

  if (typeof refreshToken === "string" && refreshToken) {
    res.headers.append(
      "Set-Cookie",
      serializeCookie(REFRESH_COOKIE, refreshToken, {
        ...opts,
        maxAge: REFRESH_MAX_AGE,
      }),
    );
  }
}

export function clearTokenCookies(res) {
  const opts = { ...baseCookieOpts(), maxAge: 0 };

  res.headers.append("Set-Cookie", serializeCookie(ACCESS_COOKIE, "", opts));
  res.headers.append("Set-Cookie", serializeCookie(REFRESH_COOKIE, "", opts));
}
