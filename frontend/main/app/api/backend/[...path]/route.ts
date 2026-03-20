import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

const ACCESS_COOKIE = "lm_access_token";

function getBackendBaseUrl(): string {
  const raw = process.env.BACKEND_API_BASE_URL;
  if (!raw || typeof raw !== "string" || !raw.trim()) {
    throw new Error("Missing BACKEND_API_BASE_URL");
  }
  return raw.trim().replace(/\/+$/, "");
}

async function getAccessTokenFromCookies(): Promise<string> {
  try {
    const cookieJar = await cookies();
    return cookieJar.get(ACCESS_COOKIE)?.value || "";
  } catch {
    return "";
  }
}

function filterUpstreamHeaders(reqHeaders: Headers): Headers {
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

async function proxy(
  req: NextRequest,
  ctx?: { params: Promise<{ path?: string[] }> },
): Promise<NextResponse> {
  let backendBase: string;
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
    .map((part: string) => {
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
    const init: RequestInit = {
      method,
      headers: upstreamHeaders,
      signal: controller.signal,
    };

    if (method !== "GET" && method !== "HEAD") {
      const body = await req.arrayBuffer();
      init.body = body;
    }

    const upstreamRes = await fetch(upstreamUrl, init);

    const buf = await upstreamRes.arrayBuffer();

    // Forward a safe subset of upstream response headers
    const safeResponseHeaders = [
      "content-type",
      "content-length",
      "content-disposition",
      "cache-control",
      "x-total-count",
    ];
    const resHeaders = new Headers();
    for (const name of safeResponseHeaders) {
      const v = upstreamRes.headers.get(name);
      if (v) resHeaders.set(name, v);
    }

    return new NextResponse(buf, {
      status: upstreamRes.status,
      headers: resHeaders,
    });
  } catch (e: unknown) {
    const isAbort =
      e && typeof e === "object" && (e as { name?: string }).name === "AbortError";

    const errObj = e && typeof e === "object" ? (e as Record<string, unknown>) : null;
    const errName =
      errObj && typeof errObj.name === "string" ? errObj.name : null;
    const errMessage =
      errObj && typeof errObj.message === "string" ? errObj.message : null;

    const cause =
      errObj && "cause" in errObj && errObj.cause ? errObj.cause : null;
    const causeObj =
      cause && typeof cause === "object"
        ? (cause as Record<string, unknown>)
        : null;
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

    // Always log full details server-side for debugging.
    console.error("[api/backend] upstream fetch failed", debug);

    return NextResponse.json(
      {
        error: "Upstream request failed",
        hint: isAbort ? `Timeout after ${timeoutMs}ms` : undefined,
        // Never send internal URLs, IPs, or ports to the client
      },
      { status: 502 },
    );
  } finally {
    clearTimeout(timeout);
  }
}

export async function GET(
  req: NextRequest,
  ctx: { params: Promise<{ path?: string[] }> },
): Promise<NextResponse> {
  return proxy(req, ctx);
}
export async function POST(
  req: NextRequest,
  ctx: { params: Promise<{ path?: string[] }> },
): Promise<NextResponse> {
  return proxy(req, ctx);
}
export async function PUT(
  req: NextRequest,
  ctx: { params: Promise<{ path?: string[] }> },
): Promise<NextResponse> {
  return proxy(req, ctx);
}
export async function PATCH(
  req: NextRequest,
  ctx: { params: Promise<{ path?: string[] }> },
): Promise<NextResponse> {
  return proxy(req, ctx);
}
export async function DELETE(
  req: NextRequest,
  ctx: { params: Promise<{ path?: string[] }> },
): Promise<NextResponse> {
  return proxy(req, ctx);
}
