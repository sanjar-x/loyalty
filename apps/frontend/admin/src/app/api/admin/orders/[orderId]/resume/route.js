import { NextResponse } from 'next/server';
import { backendFetch } from '@/shared/api/apiClient';
import { assertSameOrigin, bffError } from '@/shared/api/bff';
import { getAccessToken } from '@/shared/auth/cookies';

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function POST(request, { params }) {
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

  const { ok, status, data } = await backendFetch(
    `/api/v1/admin/orders/${orderId}/resume`,
    {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
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
