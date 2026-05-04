import { NextResponse } from "next/server";
import { cookies } from "next/headers";

import { ACCESS_COOKIE } from "@/lib/features/auth/lib/cookies";
import { clearTokenCookies } from "@/lib/features/auth/lib/cookie-helpers";

function getBackendBaseUrl() {
  const raw = process.env.BACKEND_API_BASE_URL;
  if (!raw || typeof raw !== "string" || !raw.trim()) return null;
  return raw.trim().replace(/\/+$/, "");
}

export async function POST() {
  // Best-effort backend logout — xato bo'lsa ham cookie tozalanadi
  const backendBase = getBackendBaseUrl();
  if (backendBase) {
    try {
      const cookieJar = await cookies();
      const accessToken = cookieJar.get(ACCESS_COOKIE)?.value || "";
      if (accessToken) {
        await fetch(`${backendBase}/api/v1/auth/logout`, {
          method: "POST",
          headers: {
            authorization: `Bearer ${accessToken}`,
            accept: "application/json",
          },
        });
      }
    } catch {
      // ignore — cookie har doim tozalanadi
    }
  }

  const res = NextResponse.json({ ok: true }, { status: 200 });
  clearTokenCookies(res);
  return res;
}
