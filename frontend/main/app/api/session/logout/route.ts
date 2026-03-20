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

function clearCookie(name: string): string {
  const parts = [`${encodeURIComponent(name)}=`];
  parts.push("Max-Age=0");
  parts.push("Path=/");
  parts.push("HttpOnly");
  if (isProduction()) parts.push("Secure");
  parts.push("SameSite=Lax");
  const domain = getCookieDomain();
  if (domain) parts.push(`Domain=${domain}`);
  return parts.join("; ");
}

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
  res.headers.append("Set-Cookie", clearCookie(ACCESS_COOKIE));
  res.headers.append("Set-Cookie", clearCookie(REFRESH_COOKIE));
  return res;
}
