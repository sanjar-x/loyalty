import { NextResponse } from 'next/server';
import { backendFetch } from '@/shared/api/apiClient';
import { getAccessToken } from '@/shared/auth/cookies';

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

  const { ok, status, data, headers } = await backendFetch(
    `/api/v1/admin/catalog/products/${productId}`,
    { method: 'GET', headers: { Authorization: `Bearer ${token}` } },
  );

  if (!ok) {
    return NextResponse.json(
      data ?? {
        error: {
          code: 'SERVICE_UNAVAILABLE',
          message: 'Backend unavailable',
          details: {},
        },
      },
      { status: status || 502 },
    );
  }

  // Relay backend ETag so the browser apiClient interceptor stores it
  // for the next If-Match round-trip on PATCH (F-5).
  const responseHeaders = { 'Cache-Control': 'no-store' };
  if (headers?.etag) responseHeaders.ETag = headers.etag;

  return NextResponse.json(data, { status: 200, headers: responseHeaders });
}

export async function PATCH(request, { params }) {
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
  const body = await request.json();

  // Forward If-Match to the backend so it can run the optimistic-lock
  // check; on mismatch the backend returns 412 which we relay verbatim.
  const ifMatch = request.headers.get('If-Match');
  const upstreamHeaders = {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
  if (ifMatch) upstreamHeaders['If-Match'] = ifMatch;

  const { ok, status, data, headers } = await backendFetch(
    `/api/v1/admin/catalog/products/${productId}`,
    {
      method: 'PATCH',
      headers: upstreamHeaders,
      body: JSON.stringify(body),
    },
  );

  const responseHeaders = headers?.etag ? { ETag: headers.etag } : undefined;

  return NextResponse.json(
    data ?? {
      error: {
        code: 'SERVICE_UNAVAILABLE',
        message: 'Backend unavailable',
        details: {},
      },
    },
    {
      status: ok ? 200 : status || 502,
      ...(responseHeaders ? { headers: responseHeaders } : {}),
    },
  );
}

export async function DELETE(request, { params }) {
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

  const { ok, status, data } = await backendFetch(
    `/api/v1/admin/catalog/products/${productId}`,
    { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } },
  );

  if (!ok) {
    return NextResponse.json(
      data ?? {
        error: {
          code: 'SERVICE_UNAVAILABLE',
          message: 'Backend unavailable',
          details: {},
        },
      },
      { status: status || 502 },
    );
  }

  return new NextResponse(null, { status: 204 });
}
