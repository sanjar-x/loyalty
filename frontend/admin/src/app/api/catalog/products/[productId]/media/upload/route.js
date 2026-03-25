import { NextResponse } from 'next/server';
import { backendFetch } from '@/lib/api-client';
import { getAccessToken } from '@/lib/auth';

export async function POST(request, { params }) {
  const token = await getAccessToken();
  if (!token) return NextResponse.json({ error: { code: 'UNAUTHORIZED' } }, { status: 401 });

  const { productId } = await params;
  const body = await request.json();

  const { ok, status, data } = await backendFetch(
    `/api/v1/catalog/products/${productId}/media/upload`,
    { method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: JSON.stringify(body) },
  );

  return NextResponse.json(data ?? { error: { code: 'SERVICE_UNAVAILABLE' } }, { status: ok ? 201 : (status || 502) });
}
