import { NextRequest, NextResponse } from "next/server";

import {
  isBrowserDebugAuthEnabled,
  normalizeBrowserDebugUser,
} from "@/lib/auth/browserDebugAuth";

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

function isLocalBrowserDebugRequest(req: NextRequest): boolean {
  if (!isBrowserDebugAuthEnabled()) return false;

  const hostHeader =
    req.headers.get("x-forwarded-host") || req.headers.get("host") || "";
  const host =
    req.nextUrl?.hostname ||
    hostHeader
      .split(",")
      .map((part: string) => part.trim())
      .filter(Boolean)[0]
      ?.split(":")[0] ||
    "";

  const h = String(host || "").trim().toLowerCase();

  return (
    h === "localhost" ||
    h === "127.0.0.1" ||
    h === "::1" ||
    h.endsWith(".local") ||
    (() => {
      const raw = process.env.BROWSER_DEBUG_AUTH_ALLOWED_HOSTS;
      if (typeof raw !== "string" || !raw.trim()) return false;
      const rules = raw
        .split(/[,\s]+/g)
        .map((x: string) => x.trim().toLowerCase())
        .filter(Boolean);
      return rules.some((rule: string) => {
        if (rule === h) return true;
        if (rule.startsWith("*.") && h.endsWith(rule.slice(1))) return true;
        if (rule.startsWith(".") && h.endsWith(rule)) return true;
        return false;
      });
    })()
  );
}

function serializeCookie(
  name: string,
  value: string,
  opts: {
    maxAge?: number;
    domain?: string;
    path?: string;
    httpOnly?: boolean;
    secure?: boolean;
    sameSite?: string;
  },
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

function setTokenCookies(
  res: NextResponse,
  accessToken: string,
  refreshToken: string,
): void {
  const domain = getCookieDomain();
  const secure = isProduction();

  res.headers.append(
    "Set-Cookie",
    serializeCookie(ACCESS_COOKIE, accessToken, {
      httpOnly: true,
      secure,
      sameSite: "Lax",
      path: "/",
      domain,
      maxAge: 900,
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
      maxAge: 60 * 60 * 24 * 7,
    }),
  );
}

export async function POST(req: NextRequest): Promise<NextResponse> {
  let backendBase: string;
  try {
    backendBase = getBackendBaseUrl();
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Server config error" },
      { status: 500 },
    );
  }

  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const initData =
    typeof body?.initData === "string" ? (body.initData as string).trim() : "";

  // --- Debug auth path (dev only) ---
  if (!initData && isLocalBrowserDebugRequest(req)) {
    const debugUser = normalizeBrowserDebugUser(
      body?.debugUser as Record<string, unknown> | undefined,
    );
    if (debugUser) {
      const debugRes = await fetch(`${backendBase}/api/v1/users/init/`, {
        method: "POST",
        headers: { accept: "application/json", "content-type": "application/json" },
        body: JSON.stringify({
          init_data: {
            user: { username: debugUser.username, id: String(debugUser.tg_id) },
          },
        }),
      });

      const debugJson = await debugRes.text().then((t) => {
        try { return JSON.parse(t); } catch { return null; }
      });

      if (!debugRes.ok) {
        return NextResponse.json(
          { error: "Debug backend init failed", details: debugJson },
          { status: 502 },
        );
      }

      const accessToken = debugJson?.accessToken;
      if (typeof accessToken !== "string" || !accessToken) {
        return NextResponse.json(
          { error: "Debug backend did not return accessToken" },
          { status: 502 },
        );
      }

      const res = NextResponse.json(
        { ok: true, isNewUser: false, debug: true },
        { status: 200 },
      );

      const refreshToken =
        typeof debugJson?.refreshToken === "string"
          ? debugJson.refreshToken
          : accessToken;

      setTokenCookies(res, accessToken, refreshToken);
      return res;
    }
  }

  // --- Production path: forward raw initData to backend IAM ---
  if (!initData) {
    return NextResponse.json(
      { error: "initData is required" },
      { status: 400 },
    );
  }

  const upstreamUrl = `${backendBase}/api/v1/auth/telegram`;

  let upstreamRes: Response;
  try {
    upstreamRes = await fetch(upstreamUrl, {
      method: "POST",
      headers: {
        accept: "application/json",
        authorization: `tma ${initData}`,
      },
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
    return NextResponse.json(
      {
        error: "Backend auth failed",
        status: upstreamRes.status,
        details: json ?? text,
      },
      { status: upstreamRes.status === 401 ? 401 : 502 },
    );
  }

  const accessToken = json?.accessToken;
  const refreshToken = json?.refreshToken;
  const isNewUser = json?.isNewUser === true;

  if (typeof accessToken !== "string" || !accessToken) {
    return NextResponse.json(
      { error: "Backend did not return accessToken", details: json },
      { status: 502 },
    );
  }

  if (typeof refreshToken !== "string" || !refreshToken) {
    return NextResponse.json(
      { error: "Backend did not return refreshToken", details: json },
      { status: 502 },
    );
  }

  const res = NextResponse.json(
    { ok: true, isNewUser },
    { status: 200 },
  );

  setTokenCookies(res, accessToken, refreshToken);
  return res;
}
