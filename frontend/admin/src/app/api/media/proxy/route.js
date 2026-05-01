import { NextResponse } from 'next/server';
import { getAccessToken } from '@/shared/auth/cookies';

export async function GET(request) {
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

  const url = new URL(request.url).searchParams.get('url');
  if (!url || !url.startsWith('https://')) {
    return NextResponse.json(
      {
        error: {
          code: 'BAD_REQUEST',
          message: 'Valid https URL required',
          details: {},
        },
      },
      { status: 400 },
    );
  }

  try {
    const res = await fetch(url, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (compatible; LoyalityAdmin/1.0)',
        Accept: 'image/*,*/*',
      },
    });
    if (!res.ok) {
      return new Response(null, { status: res.status });
    }

    return new Response(res.body, {
      headers: {
        'Content-Type': res.headers.get('Content-Type') || 'image/jpeg',
        'Cache-Control': 'private, max-age=3600',
      },
    });
  } catch {
    return NextResponse.json(
      {
        error: {
          code: 'FETCH_FAILED',
          message: 'Failed to fetch image',
          details: {},
        },
      },
      { status: 502 },
    );
  }
}
