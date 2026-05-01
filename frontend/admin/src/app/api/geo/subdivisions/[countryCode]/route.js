import { NextResponse } from 'next/server';
import { backendFetch } from '@/shared/api/api-client';
import { getAccessToken } from '@/shared/auth/cookies';

export async function GET(request, { params }) {
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

  const { countryCode } = await params;
  const { searchParams } = new URL(request.url);
  const lang = searchParams.get('lang') ?? 'ru';
  const search = searchParams.get('search') ?? '';
  const limit = searchParams.get('limit') ?? '50';

  const qs = new URLSearchParams({ lang, limit });
  if (search) qs.set('search', search);

  const { ok, status, data } = await backendFetch(
    `/api/v1/geo/countries/${encodeURIComponent(countryCode)}/subdivisions?${qs}`,
    { headers: { Authorization: `Bearer ${token}` } },
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
