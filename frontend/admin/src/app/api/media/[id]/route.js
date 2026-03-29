import { NextResponse } from 'next/server';
import { imageBackendFetch } from '@/lib/image-api-client';
import { getAccessToken } from '@/lib/auth';

export async function GET(request, { params }) {
  const token = await getAccessToken();
  if (!token) {
    return NextResponse.json(
      { error: { code: 'UNAUTHORIZED', message: 'Not authenticated', details: {} } },
      { status: 401 },
    );
  }

  const { id } = await params;

  const { ok, status, data } = await imageBackendFetch(
    `/api/v1/media/${id}`,
    { method: 'GET' },
  );

  return NextResponse.json(
    data ?? { error: { code: 'SERVICE_UNAVAILABLE', message: 'Image service unavailable', details: {} } },
    { status: ok ? 200 : (status || 502) },
  );
}
