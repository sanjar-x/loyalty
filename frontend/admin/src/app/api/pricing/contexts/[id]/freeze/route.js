import { NextResponse } from 'next/server';
import { backendFetch } from '@/shared/api/api-client';
import {
  assertSameOrigin,
  bffError,
  serviceUnavailableResponse,
  unauthorizedResponse,
} from '@/shared/api/bff';
import { getAccessToken } from '@/shared/auth/cookies';

export async function POST(request, { params }) {
  const csrfFail = assertSameOrigin(request);
  if (csrfFail) return csrfFail;

  const { id } = await params;
  const token = await getAccessToken();
  if (!token) return unauthorizedResponse();

  let body;
  try {
    body = await request.json();
  } catch {
    return bffError('BAD_REQUEST', 'Invalid request body', { status: 400 });
  }

  const { ok, status, data } = await backendFetch(
    `/api/v1/admin/pricing/contexts/${id}/freeze`,
    {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    },
  );

  if (!ok) {
    return data
      ? NextResponse.json(data, { status: status || 502 })
      : serviceUnavailableResponse();
  }

  return NextResponse.json(data);
}
