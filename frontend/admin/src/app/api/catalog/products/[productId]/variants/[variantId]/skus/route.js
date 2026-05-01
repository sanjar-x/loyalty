import { NextResponse } from 'next/server';
import { backendFetch } from '@/shared/api/api-client';
import { getAccessToken } from '@/shared/auth/cookies';

export async function GET(request, { params }) {
  const token = await getAccessToken();
  if (!token)
    return NextResponse.json(
      { error: { code: 'UNAUTHORIZED' } },
      { status: 401 },
    );

  const { productId, variantId } = await params;

  const { ok, status, data } = await backendFetch(
    `/api/v1/catalog/products/${productId}/variants/${variantId}/skus?limit=200`,
    { headers: { Authorization: `Bearer ${token}` } },
  );

  return NextResponse.json(data ?? { error: { code: 'SERVICE_UNAVAILABLE' } }, {
    status: ok ? 200 : status || 502,
  });
}
