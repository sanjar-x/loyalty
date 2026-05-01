import { NextResponse } from 'next/server';
import { backendFetch } from '@/shared/api/api-client';
import { getAccessToken } from '@/shared/auth/cookies';

export async function GET(request) {
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

  const { searchParams } = new URL(request.url);
  const params = new URLSearchParams();
  if (searchParams.has('is_active'))
    params.set('is_active', searchParams.get('is_active'));
  if (searchParams.has('is_frozen'))
    params.set('is_frozen', searchParams.get('is_frozen'));
  const qs = params.toString();

  const { ok, status, data } = await backendFetch(
    `/api/v1/pricing/contexts${qs ? `?${qs}` : ''}`,
    { headers: { Authorization: `Bearer ${token}` } },
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

  return NextResponse.json(data);
}

export async function POST(request) {
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

  let body;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      {
        error: {
          code: 'BAD_REQUEST',
          message: 'Invalid request body',
          details: {},
        },
      },
      { status: 400 },
    );
  }

  const { ok, status, data } = await backendFetch('/api/v1/pricing/contexts', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
  });

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

  return NextResponse.json(data, { status: 201 });
}
