import { NextResponse } from 'next/server';
import { backendFetch } from '@/shared/api/api-client';
import { imageBackendFetch } from '@/shared/api/image-api-client';
import { getAccessToken } from '@/shared/auth/cookies';

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * Resolve a media asset URL from main-backend fields or image-backend fallback.
 */
async function resolveMediaUrl(asset) {
  if (asset.url) return asset.url;
  if (asset.imageVariants?.length) {
    const v = asset.imageVariants.find((iv) => iv.url);
    if (v) return v.url;
  }
  if (asset.storageObjectId) {
    try {
      const { ok, data } = await imageBackendFetch(
        `/api/v1/media/${asset.storageObjectId}`,
      );
      if (ok && data) {
        if (data.url) return data.url;
        if (data.variants?.length) {
          const sorted = [...data.variants].sort((a, b) => a.width - b.width);
          return sorted[0]?.url ?? null;
        }
      }
    } catch {
      /* graceful degradation */
    }
  }
  return null;
}

export async function GET(request, { params }) {
  const token = await getAccessToken();
  if (!token)
    return NextResponse.json(
      { error: { code: 'UNAUTHORIZED' } },
      { status: 401 },
    );

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

  const { ok, status, data } = await backendFetch(
    `/api/v1/catalog/products/${productId}/media?limit=200`,
    { method: 'GET', headers: { Authorization: `Bearer ${token}` } },
  );

  if (!ok) {
    return NextResponse.json(
      data ?? { error: { code: 'SERVICE_UNAVAILABLE' } },
      { status: status || 502 },
    );
  }

  // Resolve URLs for each media asset in parallel
  const items = data?.items ?? [];
  const resolved = await Promise.all(
    items.map(async (asset) => ({
      ...asset,
      _resolvedUrl: await resolveMediaUrl(asset),
    })),
  );

  return NextResponse.json(
    { ...data, items: resolved },
    { status: 200, headers: { 'Cache-Control': 'no-store' } },
  );
}

export async function POST(request, { params }) {
  const token = await getAccessToken();
  if (!token)
    return NextResponse.json(
      { error: { code: 'UNAUTHORIZED' } },
      { status: 401 },
    );

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
  const {
    storageObjectId,
    variantId,
    role,
    sortOrder,
    mediaType,
    isExternal,
    url,
  } = body;
  const payload = {
    storageObjectId,
    variantId,
    role,
    sortOrder,
    mediaType,
    isExternal,
    url,
  };

  const { ok, status, data } = await backendFetch(
    `/api/v1/catalog/products/${productId}/media`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    },
  );

  return NextResponse.json(data ?? { error: { code: 'SERVICE_UNAVAILABLE' } }, {
    status: ok ? 201 : status || 502,
  });
}
