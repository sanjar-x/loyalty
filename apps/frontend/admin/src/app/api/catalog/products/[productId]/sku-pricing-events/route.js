import { NextResponse } from 'next/server';
import { getAccessToken } from '@/shared/auth/cookies';

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

const BACKEND_URL = process.env.BACKEND_URL;

// Pricing recompute SSE relay (CAT-005). Native EventSource cannot send
// custom headers, so the browser opens the SSE connection at this BFF route
// (cookie auth). Here we attach the Bearer token extracted from the
// access_token cookie and forward to the main backend's SSE stream — `fetch`
// is used directly (not `backendFetch`) because the response must be streamed
// to the client, not JSON-parsed.
//
// Mirrors the pattern established for the media-status SSE in REC-028.
export async function GET(request, { params }) {
  const token = await getAccessToken();
  if (!token) {
    return NextResponse.json(
      {
        error: {
          code: 'UNAUTHORIZED',
          message: 'Not authenticated',
          details: {},
        },
      },
      { status: 401 },
    );
  }

  const { productId } = await params;
  if (!UUID_RE.test(productId)) {
    return NextResponse.json(
      {
        error: {
          code: 'INVALID_ID',
          message: 'Invalid product ID',
          details: {},
        },
      },
      { status: 400 },
    );
  }

  let upstream;
  try {
    upstream = await fetch(
      `${BACKEND_URL}/api/v1/admin/catalog/products/${productId}/skus/pricing-events`,
      {
        headers: {
          Accept: 'text/event-stream',
          Authorization: `Bearer ${token}`,
        },
        // Forward the abort signal so closing the browser tab tears down the
        // upstream socket immediately (otherwise the long-poll keepalive holds
        // the backend connection open until its server-side timeout fires).
        signal: request.signal,
      },
    );
  } catch (err) {
    // Client disconnect during the upstream connect lands here — let it pass
    // through silently. Any other reason (DNS, connection refused, TLS) is
    // translated to the standard BACKEND_UNAVAILABLE envelope so the caller
    // sees the same shape it gets from `backendFetch` elsewhere.
    if (err?.name === 'AbortError') return new Response(null, { status: 499 });
    return NextResponse.json(
      {
        error: {
          code: 'BACKEND_UNAVAILABLE',
          message: 'Сервер недоступен',
          details: {},
        },
      },
      { status: 502 },
    );
  }

  if (!upstream.ok) {
    // Drain the upstream body before returning — otherwise keep-alive
    // pooling stalls the underlying socket until GC.
    await upstream.body?.cancel().catch(() => {});
    return NextResponse.json(
      {
        error: {
          code: 'SSE_UPSTREAM_ERROR',
          message: 'SSE connection failed',
          details: {},
        },
      },
      { status: upstream.status },
    );
  }

  return new Response(upstream.body, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  });
}
