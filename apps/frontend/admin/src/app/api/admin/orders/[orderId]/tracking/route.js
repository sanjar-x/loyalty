import { NextResponse } from 'next/server';
import { backendFetch } from '@/shared/api/apiClient';
import { getAccessToken } from '@/shared/auth/cookies';

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// Admin tracking surface — currently relays to the customer-facing endpoint
// because the backend does not yet expose a dedicated admin variant. The
// customer endpoint requires a Bearer token (no ownership-based read gate
// for staff Bearer tokens), so admin Bearer is sufficient. If a strict admin
// endpoint lands later (`/api/v1/admin/orders/{id}/tracking`), only the
// `targetPath` below needs to change.
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
    `/api/v1/orders/${orderId}/tracking`,
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
