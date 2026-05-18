import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

import { getBackendBaseUrl } from '@/shared/api/bff';

const ACCESS_COOKIE = 'lm_access_token';

function filterUpstreamHeaders(reqHeaders) {
  const headers = new Headers();
  // Spec: SPEC - Frontend Integration Guide §2 — the backend supports
  // X-Anonymous-Token, X-Request-ID and they are allowed by CORS.
  const allowList = [
    'accept',
    'content-type',
    'accept-language',
    'x-anonymous-token',
    'x-request-id',
  ];
  for (const name of allowList) {
    const v = reqHeaders.get(name);
    if (v) headers.set(name, v);
  }
  return headers;
}

function ensureRequestId(headers) {
  if (headers.has('x-request-id')) return;
  // `crypto.randomUUID` is available on the Edge runtime (Node 19+, Web Crypto).
  // Fallback — timestamp+random, only in dev environments without `crypto`.
  let id = '';
  try {
    id =
      typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
        ? crypto.randomUUID()
        : '';
  } catch {
    id = '';
  }
  if (!id) {
    id = `${Date.now().toString(16)}-${Math.random().toString(16).slice(2, 10)}`;
  }
  headers.set('x-request-id', id);
}

function buildUpstreamUrl(req, backendBase, pathParts) {
  const joinedPath = pathParts
    .map((part) => {
      const raw = typeof part === 'string' ? part : '';
      try {
        return encodeURIComponent(decodeURIComponent(raw));
      } catch {
        return encodeURIComponent(raw);
      }
    })
    .join('/');

  const url = new URL(req.url);
  const hadTrailingSlash = url.pathname.endsWith('/');

  const method = req.method || 'GET';
  const forceTrailingSlashForV1Writes =
    joinedPath === 'api/v1' && (method === 'POST' || method === 'PUT' || method === 'PATCH');

  const upstreamPath = `${backendBase}/${joinedPath}${
    hadTrailingSlash || forceTrailingSlashForV1Writes ? '/' : ''
  }`;
  return { upstreamUrl: `${upstreamPath}${url.search}`, url, joinedPath };
}

async function proxy(req, ctx) {
  let backendBase;
  try {
    backendBase = getBackendBaseUrl();
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'Server config error' },
      { status: 500 }
    );
  }

  const params = ctx?.params ? await ctx.params : undefined;
  const pathParts = Array.isArray(params?.path) ? params.path : [];
  const method = req.method || 'GET';

  const { upstreamUrl, url, joinedPath } = buildUpstreamUrl(req, backendBase, pathParts);

  const upstreamHeaders = filterUpstreamHeaders(req.headers);
  ensureRequestId(upstreamHeaders);

  // Take the access token from the cookie and forward it as Bearer.
  // If cookies() throws (edge runtime can on immutable headers) — without
  // logging we get a silent 401 cycle from the backend. We log it so it is
  // visible in Vercel/Railway runtime logs.
  let token = '';
  try {
    const cookieJar = await cookies();
    token = cookieJar.get(ACCESS_COOKIE)?.value || '';
  } catch (e) {
    console.error('[backend-proxy] cookies() threw', { error: e?.message });
  }

  if (token && !upstreamHeaders.has('authorization')) {
    upstreamHeaders.set('authorization', `Bearer ${token}`);
  }

  let bodyBuf = null;
  if (method !== 'GET' && method !== 'HEAD') {
    bodyBuf = await req.arrayBuffer();
  }

  // 25s timeout, via an abort controller
  const controller = new AbortController();
  const timeoutMs = 25_000;
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const init = { method, headers: upstreamHeaders, signal: controller.signal };
    if (method !== 'GET' && method !== 'HEAD' && bodyBuf) {
      init.body = bodyBuf;
    }

    const upstreamRes = await fetch(upstreamUrl, init);
    const contentType = upstreamRes.headers.get('content-type') || '';
    const status = upstreamRes.status;

    // HTTP spec: 204 (No Content) and 304 (Not Modified) responses cannot
    // have a body. If the `Response` constructor is given these statuses
    // with a body, it throws `TypeError: Invalid response status code 204`.
    // We return an empty response without reading the body.
    if (status === 204 || status === 304) {
      return new NextResponse(null, { status });
    }

    const buf = await upstreamRes.arrayBuffer();
    const respHeaders = { 'content-type': contentType };
    // Pass tracing headers back to the frontend (so that request_id can
    // be seen in devtools and forwarded to support).
    const reqId = upstreamRes.headers.get('x-request-id') || upstreamHeaders.get('x-request-id');
    if (reqId) respHeaders['x-request-id'] = reqId;
    const procTime = upstreamRes.headers.get('x-process-time-ms');
    if (procTime) respHeaders['x-process-time-ms'] = procTime;

    return new NextResponse(buf, { status, headers: respHeaders });
  } catch (e) {
    const isAbort = e && typeof e === 'object' && e.name === 'AbortError';

    const debug =
      process.env.NODE_ENV !== 'production'
        ? {
            incomingUrl: req.url,
            incomingPathname: url.pathname,
            joinedPath,
            method,
            upstreamUrl,
            errName: e?.name,
            errMessage: e?.message,
          }
        : undefined;

    console.error('[api/backend] upstream fetch failed', debug);

    return NextResponse.json(
      {
        error: 'Upstream request failed',
        hint: isAbort ? `Timeout after ${timeoutMs}ms` : undefined,
        debug,
      },
      { status: 502 }
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
