import { NextResponse } from 'next/server';
import { backendFetch } from '@/lib/api-client';
import { getAccessToken } from '@/lib/auth';

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function POST(request, { params }) {
  const token = await getAccessToken();
  if (!token) return NextResponse.json({ error: { code: 'UNAUTHORIZED' } }, { status: 401 });

  const { productId } = await params;
  if (!UUID_RE.test(productId)) {
    return NextResponse.json(
      { error: { code: 'INVALID_ID', message: 'Invalid product ID', details: {} } },
      { status: 400 },
    );
  }
  const body = await request.json();
  const { storageObjectId, variantId, role, sortOrder, mediaType, isExternal, url } = body;
  const payload = { storageObjectId, variantId, role, sortOrder, mediaType, isExternal, url };

  const { ok, status, data } = await backendFetch(
    `/api/v1/catalog/products/${productId}/media`,
    { method: 'POST', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }, body: JSON.stringify(payload) },
  );

  return NextResponse.json(data ?? { error: { code: 'SERVICE_UNAVAILABLE' } }, { status: ok ? 201 : (status || 502) });
}
