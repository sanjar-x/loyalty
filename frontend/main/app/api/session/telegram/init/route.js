import { NextResponse } from "next/server";

import {
  isBrowserDebugAuthEnabled,
  normalizeBrowserDebugUser,
} from "@/lib/auth/browserDebugAuth";
import { validateTelegramInitDataOrThrow } from "@/lib/auth/telegram";

const ACCESS_COOKIE = "lm_access_token";

function getBackendBaseUrl() {
  const raw = process.env.BACKEND_API_BASE_URL;
  if (!raw || typeof raw !== "string" || !raw.trim()) {
    throw new Error("Missing BACKEND_API_BASE_URL");
  }
  return raw.trim().replace(/\/+$/, "");
}

function getBotToken() {
  const raw = process.env.TG_BOT_TOKEN;
  return typeof raw === "string" ? raw.trim() : "";
}

function isProduction() {
  return process.env.NODE_ENV === "production";
}

function getInitDataMaxAgeSeconds() {
  const raw = process.env.TG_INITDATA_MAX_AGE_SECONDS;
  if (typeof raw !== "string" || !raw.trim()) return 300;
  const n = Number(raw.trim());
  if (!Number.isFinite(n) || n <= 0) return 300;
  return Math.floor(n);
}

function getDebugMeta(req, initData, debugUser) {
  if (isProduction()) return undefined;

  const hostHeader =
    req.headers.get("x-forwarded-host") || req.headers.get("host") || "";
  const host =
    req.nextUrl?.hostname ||
    hostHeader
      .split(",")
      .map((part) => part.trim())
      .filter(Boolean)[0]
      ?.split(":")[0] ||
    "";

  return {
    host,
    hasInitData: Boolean(initData),
    initDataLen: typeof initData === "string" ? initData.length : 0,
    hasDebugUser: Boolean(debugUser),
    initDataMaxAgeSeconds: getInitDataMaxAgeSeconds(),
    browserDebugAuthEnabled: isBrowserDebugAuthEnabled(),
    localBrowserDebugAllowed: isLocalBrowserDebugRequest(req),
  };
}

function isLocalBrowserDebugRequest(req) {
  if (!isBrowserDebugAuthEnabled()) return false;

  const hostHeader =
    req.headers.get("x-forwarded-host") || req.headers.get("host") || "";
  const host =
    req.nextUrl?.hostname ||
    hostHeader
      .split(",")
      .map((part) => part.trim())
      .filter(Boolean)[0]
      ?.split(":")[0] ||
    "";

  const h = String(host || "")
    .trim()
    .toLowerCase();

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
        .map((x) => x.trim().toLowerCase())
        .filter(Boolean);

      const hostMatchesRule = (host, rule) => {
        if (!rule) return false;
        if (rule === host) return true;

        if (rule.startsWith("*.")) {
          const suffix = rule.slice(1); // ".example.com"
          return suffix && host.endsWith(suffix);
        }

        if (rule.startsWith(".")) {
          return host.endsWith(rule);
        }

        return false;
      };

      return rules.some((rule) => hostMatchesRule(h, rule));
    })()
  );
}

function serializeCookie(name, value, opts) {
  const parts = [`${encodeURIComponent(name)}=${encodeURIComponent(value)}`];
  if (opts.maxAge) parts.push(`Max-Age=${Math.floor(opts.maxAge)}`);
  if (opts.domain) parts.push(`Domain=${opts.domain}`);
  if (opts.path) parts.push(`Path=${opts.path}`);
  if (opts.httpOnly) parts.push("HttpOnly");
  if (opts.secure) parts.push("Secure");
  if (opts.sameSite) parts.push(`SameSite=${opts.sameSite}`);
  return parts.join("; ");
}

function getCookieDomain() {
  const domain = process.env.COOKIE_DOMAIN;
  if (typeof domain !== "string") return undefined;
  const d = domain.trim();
  if (!d) return undefined;

  // Reject obviously invalid cookie domain values.
  // NOTE: "vercel.app" is a public suffix; setting cookies for it will be rejected.
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

export async function POST(req) {
  let backendBase;
  try {
    backendBase = getBackendBaseUrl();
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Server config error" },
      { status: 500 },
    );
  }

  let body;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const initData =
    typeof body?.initData === "string" ? body.initData.trim() : "";
  const debugUser = isLocalBrowserDebugRequest(req)
    ? normalizeBrowserDebugUser(body?.debugUser)
    : null;

  let tgId = null;
  let username = null;
  let startParam = null;

  if (initData) {
    const botToken = getBotToken();
    if (!botToken) {
      return NextResponse.json(
        {
          error: "Missing TG_BOT_TOKEN",
          debug: getDebugMeta(req, initData, debugUser),
        },
        { status: 500 },
      );
    }

    let parsed;
    try {
      parsed = validateTelegramInitDataOrThrow({
        initData,
        botToken,
        maxAgeSeconds: getInitDataMaxAgeSeconds(),
      });
    } catch (e) {
      return NextResponse.json(
        {
          error: e instanceof Error ? e.message : "Invalid initData",
          debug: getDebugMeta(req, initData, debugUser),
        },
        { status: 401 },
      );
    }

    const tgUser = parsed.user;
    tgId = tgUser?.id;
    if (tgId == null) {
      return NextResponse.json(
        { error: "Telegram user.id is missing" },
        { status: 400 },
      );
    }

    const startParamRaw = parsed?.params?.start_param;
    startParam =
      typeof startParamRaw === "string" && startParamRaw.trim()
        ? startParamRaw.trim()
        : null;

    const usernameRaw = tgUser?.username;
    username =
      typeof usernameRaw === "string" && usernameRaw.trim()
        ? usernameRaw.trim()
        : `tg_${String(tgId)}`;
  } else if (debugUser) {
    tgId = debugUser.tg_id;
    username = debugUser.username;
  } else {
    return NextResponse.json(
      {
        error: "initData or local debugUser is required",
        debug: getDebugMeta(req, initData, debugUser),
      },
      { status: 400 },
    );
  }

  const upstreamUrl = `${backendBase}/api/v1/users/init/`;

  const upstreamRes = await fetch(upstreamUrl, {
    method: "POST",
    headers: {
      accept: "application/json",
      "content-type": "application/json",
    },
    body: JSON.stringify({
      init_data: {
        user: {
          username,
          id: String(tgId),
        },
        ...(startParam ? { start_param: startParam } : {}),
      },
    }),
  });

  const text = await upstreamRes.text();
  let json = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    json = null;
  }

  if (!upstreamRes.ok) {
    return NextResponse.json(
      {
        error: "Backend init failed",
        status: upstreamRes.status,
        details: json ?? text,
      },
      { status: 502 },
    );
  }

  const accessToken = json?.accessToken;
  const user = json?.user;

  if (typeof accessToken !== "string" || !accessToken) {
    return NextResponse.json(
      { error: "Backend did not return accessToken", details: json },
      { status: 502 },
    );
  }

  const res = NextResponse.json({ ok: true, user }, { status: 200 });

  res.headers.append(
    "Set-Cookie",
    serializeCookie(ACCESS_COOKIE, accessToken, {
      httpOnly: true,
      secure: isProduction(),
      sameSite: "Lax",
      path: "/",
      domain: getCookieDomain(),
      maxAge: 60 * 60 * 24 * 30,
    }),
  );

  return res;
}
