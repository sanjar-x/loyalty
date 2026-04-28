import { NextResponse } from 'next/server';
import { backendFetch } from '@/lib/api-client';
import { getAccessToken } from '@/lib/auth';

export async function GET(request, { params }) {
  const { id } = await params;
  const token = await getAccessToken();
  if (!token) {
    return NextResponse.json(
      { error: { code: 'UNAUTHORIZED', message: 'Not authenticated', details: {} } },
      { status: 401 },
    );
  }

  const { searchParams } = new URL(request.url);
  const statusFilter = searchParams.get('status');
  const qs = statusFilter ? `?status=${statusFilter}` : '';

  const { ok, status, data } = await backendFetch(
    `/api/v1/pricing/contexts/${id}/formula/versions${qs}`,
    { headers: { Authorization: `Bearer ${token}` } },
  );

  if (!ok) {
    return NextResponse.json(
      data ?? { error: { code: 'SERVICE_UNAVAILABLE', message: 'Backend unavailable', details: {} } },
      { status: status || 502 },
    );
  }

  return NextResponse.json(data);
}
