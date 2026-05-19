import { NextResponse } from 'next/server';
import { backendFetch } from '@/shared/api/apiClient';
import { invalidate as invalidateCache } from '@/shared/api/serverCache';
import { getAccessToken } from '@/shared/auth/cookies';

export async function POST(request, { params }) {
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

  const { ok, status, data } = await backendFetch(
    `/api/v1/admin/catalog/products/${productId}/media/reorder`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    },
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

  invalidateCache(`catalog:product:${productId}:media`);
  return new NextResponse(null, { status: 204 });
}
