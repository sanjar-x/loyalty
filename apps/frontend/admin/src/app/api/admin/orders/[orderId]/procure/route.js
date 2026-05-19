import { NextResponse } from 'next/server';
import { backendFetch } from '@/shared/api/apiClient';
import { assertSameOrigin, bffError } from '@/shared/api/bff';
import { getAccessToken } from '@/shared/auth/cookies';

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// Mirrors the backend domain regex for the Chinese incoming declaration. The
// OpenAPI schema only carries minLength/maxLength so we re-enforce the
// character-class constraint here as a defense-in-depth check — the same
// rule is duplicated client-side (`validateIncomingDeclaration`) for inline
// form feedback, and the BFF guard catches anything that bypasses it.
const INCOMING_DECLARATION_RE = /^[A-Za-z0-9-]{1,15}$/;

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

  const incomingDeclaration =
    body && typeof body.incomingDeclaration === 'string'
      ? body.incomingDeclaration
      : null;

  if (
    !incomingDeclaration ||
    !INCOMING_DECLARATION_RE.test(incomingDeclaration)
  ) {
    return bffError(
      'INVALID_INCOMING_DECLARATION',
      'incomingDeclaration must match [A-Za-z0-9-]{1,15}',
      { status: 422 },
    );
  }

  const { ok, status, data } = await backendFetch(
    `/api/v1/admin/orders/${orderId}/procure`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ incomingDeclaration }),
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

  // Backend returns 204 — relay as-is.
  return new NextResponse(null, { status: 204 });
}
