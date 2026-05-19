import { NextResponse } from 'next/server';
import { backendFetch } from '@/shared/api/apiClient';
import { assertSameOrigin, bffError } from '@/shared/api/bff';
import { getAccessToken } from '@/shared/auth/cookies';

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

const CARRIER_MAX = 16;
const POINT_ID_MAX = 128;

export async function PATCH(request, { params }) {
  const csrfFail = assertSameOrigin(request);
  if (csrfFail) return csrfFail;

  const token = await getAccessToken();
  if (!token) {
    return NextResponse.json(
      {
        error: {
          code: 'UNAUTHORIZED',
          message: 'Not authenticated',
          details: {},
        },
      },
      { status: 401 },
    );
  }

  const { orderId } = await params;
  if (!UUID_RE.test(orderId)) {
    return bffError('INVALID_ID', 'Invalid order ID', { status: 400 });
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return bffError('BAD_REQUEST', 'Invalid request body', { status: 400 });
  }

  const carrier =
    body && typeof body.carrier === 'string' ? body.carrier.trim() : '';
  const pointId =
    body && typeof body.pointId === 'string' ? body.pointId.trim() : '';

  if (!carrier || carrier.length > CARRIER_MAX) {
    return bffError(
      'INVALID_CARRIER',
      `carrier must be 1..${CARRIER_MAX} chars`,
      { status: 422 },
    );
  }
  if (!pointId || pointId.length > POINT_ID_MAX) {
    return bffError(
      'INVALID_POINT_ID',
      `pointId must be 1..${POINT_ID_MAX} chars`,
      { status: 422 },
    );
  }

  const { ok, status, data } = await backendFetch(
    `/api/v1/admin/orders/${orderId}/pickup-point`,
    {
      method: 'PATCH',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ carrier, pointId }),
    },
  );

  if (!ok) {
    return NextResponse.json(
      data ?? {
        error: {
          code: 'SERVICE_UNAVAILABLE',
          message: 'Backend unavailable',
          details: {},
        },
      },
      { status: status || 502 },
    );
  }
  return new NextResponse(null, { status: 204 });
}
