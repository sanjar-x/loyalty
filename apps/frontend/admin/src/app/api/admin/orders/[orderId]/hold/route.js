import { NextResponse } from 'next/server';
import { backendFetch } from '@/shared/api/apiClient';
import { assertSameOrigin, bffError } from '@/shared/api/bff';
import { getAccessToken } from '@/shared/auth/cookies';

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// Mirrors the backend `HoldReason` enum (post-D0.1). Kept in lock-step
// with `entities/order/lib/constants.js#HOLD_REASON_VALUES`; if the
// enum grows, both lists need editing — that's the trade-off for
// rejecting bad payloads at the BFF instead of paying a 422 round-trip.
const HOLD_REASON_VALUES = new Set([
  'passport_invalid',
  'customs_rejected',
  'stuck_in_cn',
  'manual_review',
  'booking_failed',
]);

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

  let body;
  try {
    body = await request.json();
  } catch {
    return bffError('BAD_REQUEST', 'Invalid request body', { status: 400 });
  }

  const reason =
    body && typeof body.reason === 'string' ? body.reason.trim() : '';
  if (!HOLD_REASON_VALUES.has(reason)) {
    return bffError(
      'INVALID_HOLD_REASON',
      'reason must be a HoldReason enum value',
      { status: 422, details: { allowed: [...HOLD_REASON_VALUES] } },
    );
  }

  const { ok, status, data } = await backendFetch(
    `/api/v1/admin/orders/${orderId}/hold`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ reason }),
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
