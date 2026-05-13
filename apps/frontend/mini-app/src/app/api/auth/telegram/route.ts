import { type NextRequest, NextResponse } from "next/server";

import {
  getBackendBaseUrl,
  isProduction,
  setTokenCookies,
  isBrowserDebugAuthEnabled,
  normalizeBrowserDebugUser,
} from "@/features/auth/server";

function isLocalBrowserDebugRequest(req: NextRequest): boolean {
  if (!isBrowserDebugAuthEnabled()) return false;
  const host = req.nextUrl?.hostname || "";
  const h = String(host).trim().toLowerCase();
  return (
    h === "localhost" ||
    h === "127.0.0.1" ||
    h === "::1" ||
    h.endsWith(".local")
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

  // Debug auth path (dev only)
  if (!initData && isLocalBrowserDebugRequest(req)) {
    const debugUser = normalizeBrowserDebugUser(
      body?.debugUser as Record<string, unknown> | undefined,
    );
    if (debugUser) {
      let backendBase: string | undefined;
      try {
        backendBase = getBackendBaseUrl();
      } catch {
        // Backend not configured — use mock mode
      }

      if (backendBase) {
        try {
          const debugRes = await fetch(`${backendBase}/api/v1/auth/telegram`, {
            method: "POST",
            headers: {
              accept: "application/json",
              "content-type": "application/json",
            },
            body: JSON.stringify({
              init_data: {
                user: { username: debugUser.username, id: String(debugUser.tg_id) },
              },
            }),
          });

          if (debugRes.ok) {
            const debugJson = (await debugRes.json().catch(() => null)) as Record<string, unknown> | null;
            const accessToken = debugJson?.accessToken;
            const refreshToken = debugJson?.refreshToken;
            if (typeof accessToken === "string" && accessToken) {
              const res = NextResponse.json(
                { ok: true, isNewUser: false, debug: true },
                { status: 200 },
              );
              setTokenCookies(res, accessToken, (refreshToken as string) || accessToken);
              return res;
            }
          }
        } catch {
          // Backend unreachable — fall through to mock mode
        }
      }

      const mockToken = `debug_${debugUser.tg_id}_${Date.now()}`;
      const res = NextResponse.json(
        { ok: true, isNewUser: false, debug: true, mock: true },
        { status: 200 },
      );
      setTokenCookies(res, mockToken, mockToken);
      return res;
    }
  }

  // Production path: forward initData to backend
  if (!initData) {
    return NextResponse.json({ error: "initData is required" }, { status: 400 });
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
    return NextResponse.json({ error: "Backend unreachable" }, { status: 502 });
  }

  const text = await upstreamRes.text();
  let json: Record<string, unknown> | null = null;
  try {
    json = text ? (JSON.parse(text) as Record<string, unknown>) : null;
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
    return NextResponse.json({ error: "Backend did not return accessToken" }, { status: 502 });
  }

  if (typeof refreshToken !== "string" || !refreshToken) {
    return NextResponse.json({ error: "Backend did not return refreshToken" }, { status: 502 });
  }

  const res = NextResponse.json({ ok: true, isNewUser }, { status: 200 });
  setTokenCookies(res, accessToken, refreshToken);
  return res;
}
