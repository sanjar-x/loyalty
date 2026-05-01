import { NextResponse } from 'next/server';
import { backendFetch } from '@/shared/api/api-client';
import { setAuthCookiesOnResponse } from '@/shared/auth/cookies';

export async function POST(request) {
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

  const { ok, status, data } = await backendFetch('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify(body),
  });

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

  const response = NextResponse.json({ success: true });
  setAuthCookiesOnResponse(response, data.accessToken, data.refreshToken);
  return response;
}
