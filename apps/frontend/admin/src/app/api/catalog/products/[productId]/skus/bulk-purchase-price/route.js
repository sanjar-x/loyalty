import { NextResponse } from 'next/server';
import { backendFetch } from '@/shared/api/apiClient';
import { getAccessToken } from '@/shared/auth/cookies';

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// Bulk apply purchasePrice to multiple SKUs at once (CAT-003 / ADR-005).
// Backend returns a per-row result envelope; we forward the response body
// untouched so the modal can render row-level errors.
export async function POST(request, { params }) {
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

  const { productId } = await params;
  if (!UUID_RE.test(productId)) {
    return NextResponse.json(
      {
        error: {
          code: 'INVALID_ID',
          message: 'Invalid product ID',
          details: {},
        },
      },
      { status: 400 },
    );
  }

  const body = await request.json();

  const { ok, status, data } = await backendFetch(
    `/api/v1/admin/catalog/products/${productId}/skus/bulk-purchase-price`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
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

  return NextResponse.json(data, { status: 200 });
}
