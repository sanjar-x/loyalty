import { NextRequest, NextResponse } from "next/server";

import {
  ACCESS_COOKIE,
  getBackendBaseUrl,
  clearTokenCookies,
} from "@/lib/auth/server";

export async function POST(req: NextRequest): Promise<NextResponse> {
  const accessToken = req.cookies.get(ACCESS_COOKIE)?.value;

  let backendBase: string | undefined;
  try {
    backendBase = getBackendBaseUrl();
  } catch {
    // Even if backend is unreachable, clear cookies locally
  }

  // Best-effort backend logout (session revocation)
  if (accessToken && backendBase) {
    try {
      await fetch(`${backendBase}/api/v1/auth/logout`, {
        method: "POST",
        headers: {
          accept: "application/json",
          authorization: `Bearer ${accessToken}`,
        },
      });
    } catch {
      // Ignore — we still clear cookies regardless
    }
  }

  const res = NextResponse.json({ ok: true }, { status: 200 });
  clearTokenCookies(res);
  return res;
}
