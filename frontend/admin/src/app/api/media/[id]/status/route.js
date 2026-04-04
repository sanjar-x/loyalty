import { NextResponse } from 'next/server';
import { getImageBackendSSEUrl } from '@/lib/image-api-client';
import { getAccessToken } from '@/lib/auth';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function GET(request, { params }) {
  const token = await getAccessToken();
  if (!token) {
    return NextResponse.json(
      { error: { code: 'UNAUTHORIZED', message: 'Not authenticated', details: {} } },
      { status: 401 },
    );
  }

  const { id } = await params;
  if (!UUID_RE.test(id)) {
    return NextResponse.json(
      { error: { code: 'INVALID_ID', message: 'Invalid storage object ID', details: {} } },
      { status: 400 },
    );
  }

  const upstreamUrl = getImageBackendSSEUrl(id);

  const upstream = await fetch(upstreamUrl, {
    headers: {
      'Accept': 'text/event-stream',
      'X-API-Key': process.env.IMAGE_BACKEND_API_KEY,
    },
  });

  if (!upstream.ok) {
    return NextResponse.json(
      { error: { code: 'SSE_UPSTREAM_ERROR', message: 'SSE connection failed', details: {} } },
      { status: upstream.status },
    );
  }

  return new Response(upstream.body, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  });
}
