import { NextResponse } from 'next/server';
import { backendFetch } from '@/shared/api/apiClient';
import { assertSameOrigin, bffError } from '@/shared/api/bff';
import { getAccessToken } from '@/shared/auth/cookies';

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// POST /api/catalog/products/{productId}/validate-publish
//   → /api/v1/admin/catalog/products/{product_id}/_validate-publish
//
// Frontend folder is `validate-publish` (no leading underscore) because
// Next.js App Router treats `_foo/` as a private folder and excludes it
// from routing — a `_validate-publish/` folder here would silently 404
// for every caller. Backend keeps `_validate-publish` in its own URL,
// the BFF just bridges the rename.
//
// Read-only validator. Returns the publish-gate verdict + per-SKU
// diagnostics + structured failure codes the UI renders in
// PublishGateBlocker. Never returns a 4xx for "cannot publish yet" —
// that's a valid preview surfaced in the body (`ok=false`).
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

  const { productId } = await params;
  if (!UUID_RE.test(productId)) {
    return bffError('INVALID_ID', 'Invalid product ID', { status: 400 });
  }

  const { ok, status, data } = await backendFetch(
    `/api/v1/admin/catalog/products/${productId}/_validate-publish`,
    { method: 'POST', headers: { Authorization: `Bearer ${token}` } },
  );

  return NextResponse.json(data ?? { error: { code: 'SERVICE_UNAVAILABLE' } }, {
    status: ok ? 200 : status || 502,
  });
}
