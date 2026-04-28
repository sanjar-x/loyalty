import { NextResponse } from 'next/server';
import { backendFetch } from '@/lib/api-client';
import { getAccessToken } from '@/lib/auth';

const STATUS_KEYS = [
  'draft',
  'enriching',
  'ready_for_review',
  'published',
  'archived',
];

/**
 * GET /api/catalog/products/counts
 *
 * Returns product counts per status in a single request.
 * Backend has no dedicated counts endpoint, so we fire parallel
 * limit=0 queries server-side and return { all, draft, enriching, ... }.
 */
export async function GET() {
  const token = await getAccessToken();
  if (!token) {
    return NextResponse.json(
      { error: { code: 'UNAUTHORIZED', message: 'Not authenticated', details: {} } },
      { status: 401 },
    );
  }

  const headers = { Authorization: `Bearer ${token}` };

  try {
    const results = await Promise.all([
      backendFetch('/api/v1/catalog/products?offset=0&limit=1', { headers }),
      ...STATUS_KEYS.map((s) =>
        backendFetch(`/api/v1/catalog/products?offset=0&limit=1&status=${s}`, {
          headers,
        }),
      ),
    ]);

    const counts = { all: results[0].data?.total ?? 0 };
    STATUS_KEYS.forEach((s, i) => {
      counts[s] = results[i + 1].data?.total ?? 0;
    });

    return NextResponse.json(counts, {
      headers: { 'Cache-Control': 'private, max-age=5' },
    });
  } catch {
    return NextResponse.json(
      { error: { code: 'SERVICE_UNAVAILABLE', message: 'Backend unavailable', details: {} } },
      { status: 502 },
    );
  }
}
