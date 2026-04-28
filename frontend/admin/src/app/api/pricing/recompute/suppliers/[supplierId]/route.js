import { NextResponse } from 'next/server';
import { backendFetch } from '@/lib/api-client';
import { getAccessToken } from '@/lib/auth';

export async function POST(_request, { params }) {
  const { supplierId } = await params;
  const token = await getAccessToken();
  if (!token) {
    return NextResponse.json(
      { error: { code: 'UNAUTHORIZED', message: 'Not authenticated', details: {} } },
      { status: 401 },
    );
  }

  const { ok, status, data } = await backendFetch(
    `/api/v1/pricing/recompute/suppliers/${supplierId}`,
    { method: 'POST', headers: { Authorization: `Bearer ${token}` } },
  );

  if (!ok) {
    return NextResponse.json(
      data ?? { error: { code: 'SERVICE_UNAVAILABLE', message: 'Backend unavailable', details: {} } },
      { status: status || 502 },
    );
  }

  return NextResponse.json(data, { status: 202 });
}
