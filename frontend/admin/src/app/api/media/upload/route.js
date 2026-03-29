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

  // Strip product-specific fields that image_backend does not accept.
  // image_backend UploadRequest only accepts: { contentType: string, filename?: string }
  const { contentType, filename } = body;
  const imagePayload = { contentType, filename };

  const { ok, status, data } = await imageBackendFetch('/api/v1/media/upload', {
    method: 'POST',
    body: JSON.stringify(imagePayload),
  });

  if (!ok) {
    return NextResponse.json(
      data ?? { error: { code: 'IMAGE_SERVICE_ERROR', message: 'Image service error', details: {} } },
      { status: status || 502 },
    );
  }

  return NextResponse.json(data, { status: 201 });
}
