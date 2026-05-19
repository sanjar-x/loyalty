import { NextResponse } from 'next/server';
import { backendFetch } from '@/shared/api/apiClient';
import { getAccessToken } from '@/shared/auth/cookies';

/**
 * BFF passthrough for the live SKU pricing preview (CAT-013 / CAT-014).
 *
 * Backend: POST /api/v1/admin/pricing/preview-sku — same evaluator + resolver
 * as the autonomous recompute, so the preview value matches what `pricing.sku`
 * will land after save.
 */
export async function POST(request) {
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

  let body;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json(
      {
        error: {
          code: 'BAD_REQUEST',
          message: 'Invalid request body',
          details: {},
        },
      },
      { status: 400 },
    );
  }

  const { ok, status, data } = await backendFetch(
    '/api/v1/admin/pricing/preview-sku',
    {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
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

  return NextResponse.json(data);
}
