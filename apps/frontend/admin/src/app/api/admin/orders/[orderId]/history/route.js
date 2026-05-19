import { NextResponse } from 'next/server';
import { backendFetch } from '@/shared/api/apiClient';
import { getAccessToken } from '@/shared/auth/cookies';

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function GET(_request, { params }) {
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
    return NextResponse.json(
      {
        error: {
          code: 'INVALID_ID',
          message: 'Invalid order ID',
          details: {},
        },
      },
      { status: 400 },
    );
  }

  const { ok, status, data } = await backendFetch(
    `/api/v1/admin/orders/${orderId}/history`,
    { headers: { Authorization: `Bearer ${token}` } },
  );

  return NextResponse.json(
    data ?? {
      error: {
        code: 'SERVICE_UNAVAILABLE',
        message: 'Backend unavailable',
        details: {},
      },
    },
    { status: ok ? 200 : status || 502 },
  );
}
