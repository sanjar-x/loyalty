import { NextResponse } from 'next/server';
import { backendFetch } from '@/lib/api-client';
import { getAccessToken } from '@/lib/auth';

export async function GET(request, { params }) {
  const { categoryId } = await params;
  const token = await getAccessToken();
  if (!token) {
    return NextResponse.json(
      { error: { code: 'UNAUTHORIZED', message: 'Not authenticated', details: {} } },
      { status: 401 },
    );
  }

  const { searchParams } = new URL(request.url);
  const contextId = searchParams.get('context_id');
  if (!contextId) {
    return NextResponse.json(
      { error: { code: 'BAD_REQUEST', message: 'context_id query param is required', details: {} } },
      { status: 400 },
    );
  }

  const { ok, status, data } = await backendFetch(
    `/api/v1/pricing/categories/${categoryId}/pricing?context_id=${contextId}`,
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
