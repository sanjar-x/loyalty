import { NextResponse } from 'next/server';
import { backendFetch } from '@/shared/api/apiClient';
import {
  assertSameOrigin,
  serviceUnavailableResponse,
  unauthorizedResponse,
} from '@/shared/api/bff';
import { getAccessToken } from '@/shared/auth/cookies';

export async function POST(request, { params }) {
  const csrfFail = assertSameOrigin(request);
  if (csrfFail) return csrfFail;

  const { contextId, versionId } = await params;
  const token = await getAccessToken();
  if (!token) return unauthorizedResponse();

  const { ok, status, data } = await backendFetch(
    `/api/v1/admin/pricing/contexts/${contextId}/formula/versions/${versionId}/rollback`,
    { method: 'POST', headers: { Authorization: `Bearer ${token}` } },
  );

  if (!ok) {
    return data
      ? NextResponse.json(data, { status: status || 502 })
      : serviceUnavailableResponse();
  }

  return NextResponse.json(data);
}
