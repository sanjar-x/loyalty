// Helpers shared across BFF route handlers in src/app/api/**.
//
// 1) Standard JSON error responses matching the backend envelope shape
//    `{ error: { code, message, details, request_id } }`.
// 2) `assertSameOrigin(request)` — minimal CSRF defense for mutating
//    routes. SameSite=lax cookies block top-level cross-site form posts but
//    not script-driven requests from compromised subdomains; checking that
//    `Origin` (or, lacking it, `Referer`) matches `Host` is the cheapest
//    cross-cutting protection.
// 3) `proxyToBackend(...)` — factory that collapses the ~30-line auth +
//    fetch + envelope copy/paste shared by 25+ thin BFF handlers. Use only
//    for transparent proxies; routes that enrich/transform data stay
//    explicit.

import { NextResponse } from 'next/server';
import { backendFetch } from './api-client';
import { getAccessToken } from '@/shared/auth/cookies';

export function bffError(code, message, { status = 500, details = {} } = {}) {
  return NextResponse.json({ error: { code, message, details } }, { status });
}

export const unauthorizedResponse = () =>
  bffError('UNAUTHORIZED', 'Not authenticated', { status: 401 });

export const serviceUnavailableResponse = (message = 'Backend unavailable') =>
  bffError('SERVICE_UNAVAILABLE', message, { status: 502 });

export const forbiddenResponse = (message = 'Forbidden') =>
  bffError('FORBIDDEN', message, { status: 403 });

// Mutating BFF routes must originate from the same site as the host. Returns
// a NextResponse on failure (caller returns it directly), or `null` when the
// request is allowed.
export function assertSameOrigin(request) {
  const host = request.headers.get('host');
  if (!host) {
    return forbiddenResponse('Missing host header');
  }

  const origin = request.headers.get('origin');
  if (origin) {
    let originHost;
    try {
      originHost = new URL(origin).host;
    } catch {
      return forbiddenResponse('Invalid origin');
    }
    return originHost === host ? null : forbiddenResponse('Origin mismatch');
  }

  // Fallback to Referer for clients that strip Origin (rare in modern
  // browsers but still happens through some privacy extensions).
  const referer = request.headers.get('referer');
  if (referer) {
    let refererHost;
    try {
      refererHost = new URL(referer).host;
    } catch {
      return forbiddenResponse('Invalid referer');
    }
    return refererHost === host ? null : forbiddenResponse('Referer mismatch');
  }

  // Neither header — likely a non-browser client. Reject; legitimate browser
  // requests will always carry one of these on a state-changing call.
  return forbiddenResponse('Missing origin/referer');
}

const SAFE_METHODS = new Set(['GET', 'HEAD']);

// Build a Next.js route-handler that forwards the request to the backend.
//
//   pathFn        — `(params, searchParams) => '/api/v1/...'`
//   method        — HTTP method (default: 'GET')
//   forwardSearch — pass query string through verbatim (default: true for GET/HEAD)
//   allowedParams — when set, only these query keys are forwarded
//   forwardBody   — pass JSON body through (default: true for non-safe methods)
//   transformBody — `(body) => body'` to reshape outgoing JSON
//   successStatus — override response status on backend 2xx (e.g. 201)
//   csrf            — apply assertSameOrigin (default: true for non-safe methods)
//   requireAuth     — require + attach Bearer access_token (default: true).
//                     When false, the Bearer header is still attached if a
//                     token happens to be present (best-effort), but a missing
//                     token does not 401 — useful for routes the backend lets
//                     through anonymously.
//   responseHeaders — extra headers to attach to a successful response.
//
// Returned handler signature matches Next.js App Router: (request, ctx).
export function proxyToBackend({
  pathFn,
  method = 'GET',
  forwardSearch,
  allowedParams,
  forwardBody,
  transformBody,
  successStatus,
  csrf,
  requireAuth = true,
  responseHeaders,
} = {}) {
  if (typeof pathFn !== 'function') {
    throw new Error('proxyToBackend: pathFn is required');
  }
  const isSafe = SAFE_METHODS.has(method);
  const wantSearch = forwardSearch ?? isSafe;
  const wantBody = forwardBody ?? !isSafe;
  const wantCsrf = csrf ?? !isSafe;

  return async function handler(request, ctx = {}) {
    if (wantCsrf) {
      const fail = assertSameOrigin(request);
      if (fail) return fail;
    }

    const params = ctx.params ? await ctx.params : {};
    const url = new URL(request.url);
    let basePath;
    try {
      basePath = pathFn(params, url.searchParams);
    } catch {
      return bffError('BAD_REQUEST', 'Invalid request path', { status: 400 });
    }
    if (!basePath || typeof basePath !== 'string') {
      return bffError('BAD_REQUEST', 'Invalid request path', { status: 400 });
    }

    const qs = wantSearch
      ? buildQueryString(url.searchParams, allowedParams)
      : '';
    const targetPath = qs ? `${basePath}?${qs}` : basePath;

    let token = null;
    if (requireAuth) {
      token = await getAccessToken();
      if (!token) return unauthorizedResponse();
    } else {
      token = await getAccessToken();
    }

    let body;
    if (wantBody) {
      const ct = request.headers.get('content-type') || '';
      if (ct.includes('application/json')) {
        try {
          const parsed = await request.json();
          const out = transformBody ? transformBody(parsed) : parsed;
          body = JSON.stringify(out);
        } catch {
          return bffError('BAD_REQUEST', 'Invalid request body', {
            status: 400,
          });
        }
      }
    }

    const headers = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    if (body !== undefined) headers['Content-Type'] = 'application/json';

    const { ok, status, data } = await backendFetch(targetPath, {
      method,
      headers,
      ...(body !== undefined ? { body } : {}),
    });

    if (!ok) {
      return data
        ? NextResponse.json(data, { status: status || 502 })
        : serviceUnavailableResponse();
    }

    const responseInit = {
      status:
        successStatus ??
        (data === null || data === undefined ? 204 : (status ?? 200)),
      ...(responseHeaders ? { headers: responseHeaders } : {}),
    };
    if (data === null || data === undefined) {
      return new NextResponse(null, responseInit);
    }
    return NextResponse.json(data, responseInit);
  };
}

function buildQueryString(searchParams, allowedParams) {
  if (!allowedParams) {
    const s = searchParams.toString();
    return s;
  }
  const out = new URLSearchParams();
  for (const key of allowedParams) {
    const values = searchParams.getAll(key);
    for (const v of values) out.append(key, v);
  }
  return out.toString();
}
