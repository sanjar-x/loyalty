import { NextResponse } from 'next/server';
import { backendFetch } from '@/shared/api/api-client';
import { getAccessToken } from '@/shared/auth/cookies';

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function PATCH(request, { params }) {
  const token = await getAccessToken();
  if (!token)
    return NextResponse.json(
      { error: { code: 'UNAUTHORIZED' } },
      { status: 401 },
    );

  const { productId } = await params;
  if (!UUID_RE.test(productId)) {
    return NextResponse.json(
      {
        error: {
          code: 'INVALID_ID',
          message: 'Invalid product ID',
          details: {},
        },
      },
      { status: 400 },
    );
  }
  const body = await request.json();

  const { ok, status, data } = await backendFetch(
    `/api/v1/catalog/products/${productId}/status`,
    {
      method: 'PATCH',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    },
  );

  return NextResponse.json(data ?? { error: { code: 'SERVICE_UNAVAILABLE' } }, {
    status: ok ? 200 : status || 502,
  });
}
