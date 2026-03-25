import { NextResponse } from 'next/server';
import { backendFetch } from '@/lib/api-client';
import { getAccessToken } from '@/lib/auth';

export async function POST(request, { params }) {
  const token = await getAccessToken();
  if (!token) return NextResponse.json({ error: { code: 'UNAUTHORIZED' } }, { status: 401 });

  const { productId, mediaId } = await params;

  const { ok, status, data } = await backendFetch(
    `/api/v1/catalog/products/${productId}/media/${mediaId}/confirm`,
    { method: 'POST', headers: { Authorization: `Bearer ${token}` } },
  );

  return NextResponse.json(data ?? { error: { code: 'SERVICE_UNAVAILABLE' } }, { status: ok ? 202 : (status || 502) });
}
