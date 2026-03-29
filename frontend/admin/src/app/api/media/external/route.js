import { NextResponse } from 'next/server';
import { imageBackendFetch } from '@/lib/image-api-client';
import { getAccessToken } from '@/lib/auth';

export async function POST(request) {
  const token = await getAccessToken();
  if (!token) {
    return NextResponse.json(
      { error: { code: 'UNAUTHORIZED', message: 'Not authenticated', details: {} } },
      { status: 401 },
    );
  }

  const body = await request.json();

  const { ok, status, data } = await imageBackendFetch('/api/v1/media/external', {
    method: 'POST',
    body: JSON.stringify(body),
  });

  return NextResponse.json(
    data ?? { error: { code: 'SERVICE_UNAVAILABLE', message: 'Image service unavailable', details: {} } },
    { status: ok ? 201 : (status || 502) },
  );
}
