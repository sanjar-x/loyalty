import { NextResponse } from 'next/server';
import { backendFetch } from '@/shared/api/apiClient';
import { getAccessToken } from '@/shared/auth/cookies';

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

  const body = await request.json();

  // Strip extras: backend /api/v1/admin/media/upload only accepts
  // { contentType: string, filename?: string }.
  const { contentType, filename } = body;
  const payload = { contentType, filename };

  const { ok, status, data } = await backendFetch(
    '/api/v1/admin/media/upload',
    {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(payload),
    },
  );

  if (!ok) {
    return NextResponse.json(
      data ?? {
        error: {
          code: 'MEDIA_SERVICE_ERROR',
          message: 'Media service error',
          details: {},
        },
      },
      { status: status || 502 },
    );
  }

  return NextResponse.json(data, { status: 201 });
}
