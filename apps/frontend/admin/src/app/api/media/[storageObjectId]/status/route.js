import { NextResponse } from 'next/server';
import { getAccessToken } from '@/shared/auth/cookies';

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

const BACKEND_URL = process.env.BACKEND_URL;

// Native EventSource cannot send custom headers, so the browser opens the SSE
// connection at this BFF route (cookie auth). Here we attach the Bearer token
// extracted from the access_token cookie and forward to the main backend's SSE
// stream — `fetch` is used directly (not `backendFetch`) because the response
// must be streamed to the client, not JSON-parsed.
//
// Mirrors the pattern in /api/catalog/products/[productId]/sku-pricing-events:
// forward request.signal so closing the tab tears down the upstream socket
// immediately, drain non-OK upstream bodies before responding, and translate
// transport errors into the standard envelope.
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

  const { storageObjectId } = await params;
  if (!UUID_RE.test(id)) {
    return NextResponse.json(
      {
        error: {
          code: 'INVALID_ID',
          message: 'Invalid storage object ID',
          details: {},
        },
      },
      { status: 400 },
    );
  }

  let upstream;
  try {
    upstream = await fetch(
      `${BACKEND_URL}/api/v1/admin/media/${storageObjectId}/status`,
      {
        headers: {
          Accept: 'text/event-stream',
          Authorization: `Bearer ${token}`,
        },
        signal: request.signal,
      },
    );
  } catch (err) {
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
