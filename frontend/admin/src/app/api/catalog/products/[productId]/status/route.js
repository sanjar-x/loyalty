import { NextResponse } from 'next/server';
import { backendFetch } from '@/lib/api-client';
import { getAccessToken } from '@/lib/auth';

export async function PATCH(request, { params }) {
  const token = await getAccessToken();
  if (!token) return NextResponse.json({ error: { code: 'UNAUTHORIZED' } }, { status: 401 });

  const { productId } = await params;
  const body = await request.json();

  const { ok, status, data } = await backendFetch(
    `/api/v1/catalog/products/${productId}/status`,
    { method: 'PATCH', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: JSON.stringify(body) },
  );

  return NextResponse.json(data ?? { error: { code: 'SERVICE_UNAVAILABLE' } }, { status: ok ? 200 : (status || 502) });
}
