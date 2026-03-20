import { NextRequest, NextResponse } from "next/server";

const ACCESS_COOKIE = "lm_access_token";
const REFRESH_COOKIE = "lm_refresh_token";

function getBackendBaseUrl(): string {
  const raw = process.env.BACKEND_API_BASE_URL;
  if (!raw || typeof raw !== "string" || !raw.trim()) {
    throw new Error("Missing BACKEND_API_BASE_URL");
  }
  return raw.trim().replace(/\/+$/, "");
}

function isProduction(): boolean {
  return process.env.NODE_ENV === "production";
}

function getCookieDomain(): string | undefined {
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

function serializeCookie(
  name: string,
  value: string,
  opts: { maxAge?: number; domain?: string; path?: string; httpOnly?: boolean; secure?: boolean; sameSite?: string },
): string {
  const parts = [`${encodeURIComponent(name)}=${encodeURIComponent(value)}`];
  if (opts.maxAge) parts.push(`Max-Age=${Math.floor(opts.maxAge)}`);
  if (opts.domain) parts.push(`Domain=${opts.domain}`);
  if (opts.path) parts.push(`Path=${opts.path}`);
  if (opts.httpOnly) parts.push("HttpOnly");
  if (opts.secure) parts.push("Secure");
  if (opts.sameSite) parts.push(`SameSite=${opts.sameSite}`);
  return parts.join("; ");
}

function clearCookie(name: string): string {
  return serializeCookie(name, "", {
    maxAge: 0,
    path: "/",
    httpOnly: true,
    secure: isProduction(),
    sameSite: "Lax",
    domain: getCookieDomain(),
  });
}

export async function POST(req: NextRequest): Promise<NextResponse> {
  const refreshToken = req.cookies.get(REFRESH_COOKIE)?.value;

  if (!refreshToken) {
    return NextResponse.json(
      { error: "No refresh token" },
      { status: 401 },
    );
  }

  let backendBase: string;
  try {
    backendBase = getBackendBaseUrl();
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Server config error" },
      { status: 500 },
    );
  }

  let upstreamRes: Response;
  try {
    upstreamRes = await fetch(`${backendBase}/api/v1/auth/refresh`, {
      method: "POST",
      headers: {
        accept: "application/json",
        "content-type": "application/json",
      },
      body: JSON.stringify({ refreshToken }),
    });
  } catch (e) {
    return NextResponse.json(
      { error: "Backend unreachable", detail: e instanceof Error ? e.message : "unknown" },
      { status: 502 },
    );
  }

  const text = await upstreamRes.text();
  let json: Record<string, unknown> | null = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    json = null;
  }

  if (!upstreamRes.ok) {
    const res = NextResponse.json(
      { error: "Refresh failed", status: upstreamRes.status },
      { status: 401 },
    );
    res.headers.append("Set-Cookie", clearCookie(ACCESS_COOKIE));
    res.headers.append("Set-Cookie", clearCookie(REFRESH_COOKIE));
    return res;
  }

  const newAccessToken = json?.accessToken;
  const newRefreshToken = json?.refreshToken;

  if (
    typeof newAccessToken !== "string" || !newAccessToken ||
    typeof newRefreshToken !== "string" || !newRefreshToken
  ) {
    return NextResponse.json(
      { error: "Backend did not return token pair" },
      { status: 502 },
    );
  }

  const res = NextResponse.json({ ok: true }, { status: 200 });
  const domain = getCookieDomain();
  const secure = isProduction();

  res.headers.append(
    "Set-Cookie",
    serializeCookie(ACCESS_COOKIE, newAccessToken, {
      httpOnly: true, secure, sameSite: "Lax", path: "/", domain,
      maxAge: 900,
    }),
  );
  res.headers.append(
    "Set-Cookie",
    serializeCookie(REFRESH_COOKIE, newRefreshToken, {
      httpOnly: true, secure, sameSite: "Lax", path: "/", domain,
      maxAge: 60 * 60 * 24 * 7,
    }),
  );

  return res;
}
