import { type NextRequest, NextResponse } from "next/server";

import {
  REFRESH_COOKIE,
  getBackendBaseUrl,
  setTokenCookies,
  clearTokenCookies,
} from "@/features/auth/server";

export async function POST(req: NextRequest): Promise<NextResponse> {
  const refreshToken = req.cookies.get(REFRESH_COOKIE)?.value;

  if (!refreshToken) {
    return NextResponse.json({ error: "No refresh token" }, { status: 401 });
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
    const res = NextResponse.json(
      { error: "Refresh failed", status: upstreamRes.status },
      { status: 401 },
    );
    clearTokenCookies(res);
    return res;
  }

  const newAccessToken = json?.accessToken;
  const newRefreshToken = json?.refreshToken;

  if (
    typeof newAccessToken !== "string" ||
    !newAccessToken ||
    typeof newRefreshToken !== "string" ||
    !newRefreshToken
  ) {
    return NextResponse.json({ error: "Backend did not return token pair" }, { status: 502 });
  }

  const res = NextResponse.json({ ok: true }, { status: 200 });
  setTokenCookies(res, newAccessToken, newRefreshToken);
  return res;
}
