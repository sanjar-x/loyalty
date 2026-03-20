import { NextRequest, NextResponse } from "next/server";

import {
  isBrowserDebugAuthEnabled,
  normalizeBrowserDebugUser,
} from "@/lib/auth/browserDebugAuth";
import {
  getBackendBaseUrl,
  isProduction,
  setTokenCookies,
} from "@/lib/auth/server";

function isLocalBrowserDebugRequest(req: NextRequest): boolean {
  if (!isBrowserDebugAuthEnabled()) return false;

  // Prefer req.nextUrl.hostname (set by Next.js from the actual URL).
  // Do NOT trust x-forwarded-host — it is trivially spoofable unless
  // the reverse proxy guarantees it.
  const host = req.nextUrl?.hostname || "";
  const h = String(host).trim().toLowerCase();

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
          { error: "Debug backend init failed" },
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

      const refreshToken =
        typeof debugJson?.refreshToken === "string"
          ? debugJson.refreshToken
          : accessToken; // fallback for legacy debug endpoint

      const res = NextResponse.json(
        { ok: true, isNewUser: false, debug: true },
        { status: 200 },
      );
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

  let upstreamRes: Response;
  try {
    upstreamRes = await fetch(`${backendBase}/api/v1/auth/telegram`, {
      method: "POST",
      headers: {
        accept: "application/json",
        authorization: `tma ${initData}`,
      },
    });
  } catch (e) {
    return NextResponse.json(
      { error: "Backend unreachable" },
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
        ...(isProduction() ? {} : { details: json ?? text }),
      },
      { status: upstreamRes.status === 401 ? 401 : 502 },
    );
  }

  const accessToken = json?.accessToken;
  const refreshToken = json?.refreshToken;
  const isNewUser = json?.isNewUser === true;

  if (typeof accessToken !== "string" || !accessToken) {
    return NextResponse.json(
      { error: "Backend did not return accessToken" },
      { status: 502 },
    );
  }

  if (typeof refreshToken !== "string" || !refreshToken) {
    return NextResponse.json(
      { error: "Backend did not return refreshToken" },
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
