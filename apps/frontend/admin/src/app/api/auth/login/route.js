import { NextResponse } from 'next/server';
import { backendFetch } from '@/shared/api/apiClient';
import { assertSameOrigin, bffError } from '@/shared/api/bff';
import { setAuthCookiesOnResponse } from '@/shared/auth/cookies';

export async function POST(request) {
  const csrfFail = assertSameOrigin(request);
  if (csrfFail) return csrfFail;

  let body;
  try {
    body = await request.json();
  } catch {
    return bffError('BAD_REQUEST', 'Invalid request body', { status: 400 });
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
