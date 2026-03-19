import { NextResponse } from "next/server";
import { cookies } from "next/headers";

const ACCESS_COOKIE = "lm_access_token";

function getBackendBaseUrl() {
  const raw = process.env.BACKEND_API_BASE_URL;
  if (!raw || typeof raw !== "string" || !raw.trim()) {
    throw new Error("Missing BACKEND_API_BASE_URL");
  }
  return raw.trim().replace(/\/+$/, "");
}

async function getAccessTokenFromCookies() {
  try {
    const cookieJar = await cookies();
    return cookieJar.get(ACCESS_COOKIE)?.value || "";
  } catch {
    return "";
  }
}

function filterUpstreamHeaders(reqHeaders) {
  const headers = new Headers();

  // Keep only headers that are safe and useful for server-to-server proxying.
  // Forwarding browser-specific headers like Origin/Referer may trigger
  // upstream CORS/WAF rules and cause unexpected 403/404 responses.
  const allowList = ["accept", "content-type", "accept-language"];

  for (const name of allowList) {
    const v = reqHeaders.get(name);
    if (v) headers.set(name, v);
  }

  return headers;
}

async function proxy(req, ctx) {
  let backendBase;
  try {
    backendBase = getBackendBaseUrl();
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Server config error" },
      { status: 500 },
    );
  }

  const params = ctx?.params ? await ctx.params : undefined;
  const pathParts = Array.isArray(params?.path) ? params.path : [];
  // Avoid double-encoding when a client path segment already contains
  // percent-escapes (e.g. get_photo/1%2Ffile.png). We normalize by
  // decode -> encode exactly once per segment.
  const joinedPath = pathParts
    .map((part) => {
      const raw = typeof part === "string" ? part : "";
      try {
        return encodeURIComponent(decodeURIComponent(raw));
      } catch {
        return encodeURIComponent(raw);
      }
    })
    .join("/");

  const url = new URL(req.url);
  const hadTrailingSlash = url.pathname.endsWith("/");

  const method = req.method || "GET";
  // DRF-style APIs often require trailing slashes. For the root /api/v1 endpoint
  // we normalize POST/PUT/PATCH to always include the slash to avoid redirects.
  const forceTrailingSlashForV1Writes =
    joinedPath === "api/v1" &&
    (method === "POST" || method === "PUT" || method === "PATCH");

  const upstreamPath = `${backendBase}/${joinedPath}${
    hadTrailingSlash || forceTrailingSlashForV1Writes ? "/" : ""
  }`;
  const upstreamUrl = `${upstreamPath}${url.search}`;

  const upstreamHeaders = filterUpstreamHeaders(req.headers);

  const token = await getAccessTokenFromCookies();
  if (token && !upstreamHeaders.has("authorization")) {
    upstreamHeaders.set("authorization", `Bearer ${token}`);
  }

  const controller = new AbortController();
  const timeoutMs = 25_000;
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const init = {
      method,
      headers: upstreamHeaders,
      signal: controller.signal,
    };

    if (method !== "GET" && method !== "HEAD") {
      const body = await req.arrayBuffer();
      init.body = body;
    }

    const upstreamRes = await fetch(upstreamUrl, init);

    // Pass-through body + content-type
    const contentType = upstreamRes.headers.get("content-type") || "";
    const buf = await upstreamRes.arrayBuffer();

    const res = new NextResponse(buf, {
      status: upstreamRes.status,
      headers: {
        "content-type": contentType,
      },
    });

    return res;
  } catch (e) {
    const isAbort = e && typeof e === "object" && e.name === "AbortError";

    const errName =
      e && typeof e === "object" && typeof e.name === "string" ? e.name : null;
    const errMessage =
      e && typeof e === "object" && typeof e.message === "string"
        ? e.message
        : null;

    const cause =
      e && typeof e === "object" && "cause" in e && e.cause ? e.cause : null;
    const causeObj = cause && typeof cause === "object" ? cause : null;
    const causeName =
      causeObj && typeof causeObj.name === "string" ? causeObj.name : null;
    const causeMessage =
      causeObj && typeof causeObj.message === "string"
        ? causeObj.message
        : null;
    const causeCode =
      causeObj && typeof causeObj.code === "string" ? causeObj.code : null;
    const causeErrno =
      causeObj &&
      (typeof causeObj.errno === "number" || typeof causeObj.errno === "string")
        ? causeObj.errno
        : null;
    const causeSyscall =
      causeObj && typeof causeObj.syscall === "string"
        ? causeObj.syscall
        : null;
    const causeAddress =
      causeObj && typeof causeObj.address === "string"
        ? causeObj.address
        : null;
    const causePort =
      causeObj &&
      (typeof causeObj.port === "number" || typeof causeObj.port === "string")
        ? causeObj.port
        : null;

    const debug =
      process.env.NODE_ENV !== "production"
        ? {
            incomingUrl: req.url,
            incomingPathname: url.pathname,
            incomingHadTrailingSlash: hadTrailingSlash,
            joinedPath,
            method,
            forceTrailingSlashForV1Writes,
            upstreamUrl,
            errName,
            errMessage,
            causeName,
            causeMessage,
            causeCode,
            causeErrno,
            causeSyscall,
            causeAddress,
            causePort,
          }
        : undefined;

    // Keep a server-side log for local debugging.
    console.error("[api/backend] upstream fetch failed", debug);

    return NextResponse.json(
      {
        error: "Upstream request failed",
        hint: isAbort ? `Timeout after ${timeoutMs}ms` : undefined,
        debug,
      },
      { status: 502 },
    );
  } finally {
    clearTimeout(timeout);
  }
}

export async function GET(req, ctx) {
  return proxy(req, ctx);
}
export async function POST(req, ctx) {
  return proxy(req, ctx);
}
export async function PUT(req, ctx) {
  return proxy(req, ctx);
}
export async function PATCH(req, ctx) {
  return proxy(req, ctx);
}
export async function DELETE(req, ctx) {
  return proxy(req, ctx);
}
