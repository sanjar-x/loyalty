import { NextRequest, NextResponse } from "next/server";

import { handoffStore } from "../_handoffStore";
import { signHs256Jwt } from "@/lib/auth/telegram";

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

interface CookieOptions {
  maxAge?: number;
  domain?: string;
  path?: string;
  httpOnly?: boolean;
  secure?: boolean;
  sameSite?: string;
}

function serializeCookie(
  name: string,
  value: string,
  opts: CookieOptions,
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

export async function POST(req: NextRequest): Promise<NextResponse> {
  const sessionSecret = process.env.SESSION_JWT_SECRET;
  if (!sessionSecret) {
    return NextResponse.json(
      { error: "Missing SESSION_JWT_SECRET" },
      { status: 500 },
    );
  }

  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  if (typeof body.handoff !== "string" || !body.handoff) {
    return NextResponse.json(
      { error: "handoff must be a string" },
      { status: 400 },
    );
  }

  const payload = handoffStore.consume(body.handoff as string);
  if (!payload) {
    return NextResponse.json(
      { error: "Invalid or expired handoff" },
      { status: 401 },
    );
  }

  const nowSec = Math.floor(Date.now() / 1000);
  const token = signHs256Jwt(
    {
      iss: "telegram-hybrid-auth",
      iat: nowSec,
      exp: nowSec + 60 * 60 * 24 * 30,
      user: payload.user,
    },
    sessionSecret,
  );

  const res = NextResponse.json({ ok: true }, { status: 200 });
  res.headers.append(
    "Set-Cookie",
    serializeCookie("tg_session", token, {
      httpOnly: true,
      secure: true,
      sameSite: "Lax",
      path: "/",
      domain: getCookieDomain(),
      maxAge: 60 * 60 * 24 * 30,
    }),
  );

  return res;
}
