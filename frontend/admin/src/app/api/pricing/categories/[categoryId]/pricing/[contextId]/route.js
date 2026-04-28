import { NextResponse } from 'next/server';
import { backendFetch } from '@/lib/api-client';
import { getAccessToken } from '@/lib/auth';

export async function PUT(request, { params }) {
  const { categoryId, contextId } = await params;
  const token = await getAccessToken();
  if (!token) {
    return NextResponse.json(
      { error: { code: 'UNAUTHORIZED', message: 'Not authenticated', details: {} } },
      { status: 401 },
    );
  }

  let body;
  try { body = await request.json(); } catch {
    return NextResponse.json(
      { error: { code: 'BAD_REQUEST', message: 'Invalid request body', details: {} } },
      { status: 400 },
    );
  }

  const { ok, status, data } = await backendFetch(
    `/api/v1/pricing/categories/${categoryId}/pricing/${contextId}`,
    {
      method: 'PUT',
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    },
  );

  if (!ok) {
    return NextResponse.json(
      data ?? { error: { code: 'SERVICE_UNAVAILABLE', message: 'Backend unavailable', details: {} } },
      { status: status || 502 },
    );
  }

  return NextResponse.json(data);
}

export async function DELETE(_request, { params }) {
  const { categoryId, contextId } = await params;
  const token = await getAccessToken();
  if (!token) {
    return NextResponse.json(
      { error: { code: 'UNAUTHORIZED', message: 'Not authenticated', details: {} } },
      { status: 401 },
    );
  }

  const { ok, status, data } = await backendFetch(
    `/api/v1/pricing/categories/${categoryId}/pricing/${contextId}`,
    { method: 'DELETE', headers: { Authorization: `Bearer ${token}` } },
  );

  if (status === 204 || ok) {
    return NextResponse.json(data ?? { success: true });
  }

  return NextResponse.json(
    data ?? { error: { code: 'SERVICE_UNAVAILABLE', message: 'Backend unavailable', details: {} } },
    { status: status || 502 },
  );
}
