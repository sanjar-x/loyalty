import { NextRequest, NextResponse } from "next/server";

import {
  isBrowserDebugAuthEnabled,
  normalizeBrowserDebugUser,
} from "@/lib/auth/debug";
import {
  getBackendBaseUrl,
  isProduction,
  setTokenCookies,
} from "@/lib/auth/cookie-helpers";

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
  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const initData =
    typeof body?.initData === "string" ? (body.initData as string).trim() : "";

  // --- Debug auth path (dev only, works without backend) ---
  if (!initData && isLocalBrowserDebugRequest(req)) {
    const debugUser = normalizeBrowserDebugUser(
      body?.debugUser as Record<string, unknown> | undefined,
    );
    if (debugUser) {
      // Try backend first; if unreachable, use mock tokens
      let backendBase: string | undefined;
      try {
        backendBase = getBackendBaseUrl();
      } catch {
        // BACKEND_API_BASE_URL not configured — use mock mode
      }

      if (backendBase) {
        try {
          const debugRes = await fetch(`${backendBase}/api/v1/auth/telegram`, {
            method: "POST",
            headers: {
              accept: "application/json",
              // Debug: construct a minimal auth header (backend will validate)
              "content-type": "application/json",
            },
            body: JSON.stringify({
              init_data: {
                user: { username: debugUser.username, id: String(debugUser.tg_id) },
              },
            }),
          });

          if (debugRes.ok) {
            const debugJson = await debugRes.json().catch(() => null);
            const accessToken = debugJson?.accessToken;
            const refreshToken = debugJson?.refreshToken;
            if (typeof accessToken === "string" && accessToken) {
              const res = NextResponse.json(
                { ok: true, isNewUser: false, debug: true },
                { status: 200 },
              );
              setTokenCookies(res, accessToken, refreshToken || accessToken);
              return res;
            }
          }
          // Backend returned error — fall through to mock mode
        } catch {
          // Backend unreachable — fall through to mock mode
        }
      }

      // Mock mode: generate a synthetic debug token (dev only, never production)
      const mockToken = `debug_${debugUser.tg_id}_${Date.now()}`;
      const res = NextResponse.json(
        { ok: true, isNewUser: false, debug: true, mock: true },
        { status: 200 },
      );
      setTokenCookies(res, mockToken, mockToken);
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
    upstreamRes = await fetch(`${backendBase}/api/v1/auth/telegram`, {
      method: "POST",
      headers: {
        accept: "application/json",
        authorization: `tma ${initData}`,
      },
    });
  } catch {
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
