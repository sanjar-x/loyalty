import { NextResponse } from 'next/server';
import { imageBackendFetch } from '@/shared/api/image-api-client';
import { getAccessToken } from '@/shared/auth/cookies';

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

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

  const { id } = await params;
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

  const { ok, status, data } = await imageBackendFetch(`/api/v1/media/${id}`, {
    method: 'GET',
  });

  return NextResponse.json(
    data ?? {
      error: {
        code: 'SERVICE_UNAVAILABLE',
        message: 'Image service unavailable',
        details: {},
      },
    },
    { status: ok ? 200 : status || 502 },
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

  const { id } = await params;
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

  const { ok, status, data } = await imageBackendFetch(`/api/v1/media/${id}`, {
    method: 'DELETE',
  });

  return NextResponse.json(data ?? { deleted: true }, {
    status: ok ? 200 : status || 502,
  });
}
