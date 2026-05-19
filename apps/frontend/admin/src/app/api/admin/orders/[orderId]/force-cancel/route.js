import { NextResponse } from 'next/server';
import { backendFetch } from '@/shared/api/apiClient';
import { assertSameOrigin, bffError } from '@/shared/api/bff';
import { getAccessToken } from '@/shared/auth/cookies';

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

const CANCEL_REASON_MAX = 64;
const IDEMPOTENCY_KEY_MIN = 8;
const IDEMPOTENCY_KEY_MAX = 128;

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
    body && typeof body.reason === 'string' && body.reason.trim()
      ? body.reason.trim()
      : 'customer_changed_mind'; // backend default
  if (reason.length > CANCEL_REASON_MAX) {
    return bffError(
      'INVALID_CANCEL_REASON',
      `reason must be ≤${CANCEL_REASON_MAX} chars`,
      { status: 422 },
    );
  }

  const idempotencyKey =
    body && typeof body.idempotencyKey === 'string'
      ? body.idempotencyKey
      : null;
  if (
    !idempotencyKey ||
    idempotencyKey.length < IDEMPOTENCY_KEY_MIN ||
    idempotencyKey.length > IDEMPOTENCY_KEY_MAX
  ) {
    return bffError(
      'INVALID_IDEMPOTENCY_KEY',
      `idempotencyKey must be ${IDEMPOTENCY_KEY_MIN}..${IDEMPOTENCY_KEY_MAX} chars`,
      { status: 422 },
    );
  }

  const { ok, status, data } = await backendFetch(
    `/api/v1/admin/orders/${orderId}/force-cancel`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ reason, idempotencyKey }),
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
