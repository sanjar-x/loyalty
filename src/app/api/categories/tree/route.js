import { NextResponse } from 'next/server';
import { backendFetch } from '@/lib/api-client';
import { getAccessToken } from '@/lib/auth';

export async function GET() {
  const token = await getAccessToken();
  const headers = token ? { Authorization: `Bearer ${token}` } : {};

  const { ok, status, data } = await backendFetch(
    '/api/v1/catalog/categories/tree',
    { headers },
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

  // Backend already returns camelCase via Pydantic CamelModel
  return NextResponse.json(data);
}
