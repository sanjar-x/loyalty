import { NextResponse } from 'next/server';
import { backendFetch } from '@/shared/api/api-client';
import {
  getRefreshToken,
  setAuthCookiesOnResponse,
  clearAuthCookiesOnResponse,
} from '@/shared/auth/cookies';

export async function POST() {
  const refreshToken = await getRefreshToken();

  if (!refreshToken) {
    return NextResponse.json(
      {
        error: {
          code: 'NO_REFRESH_TOKEN',
          message: 'No refresh token',
          details: {},
        },
      },
      { status: 401 },
    );
  }

  const { ok, status, data } = await backendFetch('/api/v1/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refreshToken }),
  });

  if (!ok) {
    const response = NextResponse.json(
      data ?? {
        error: {
          code: 'REFRESH_FAILED',
          message: 'Token refresh failed',
          details: {},
        },
      },
      { status: status || 401 },
    );
    clearAuthCookiesOnResponse(response);
    return response;
  }

  const response = NextResponse.json({ success: true });
  setAuthCookiesOnResponse(response, data.accessToken, data.refreshToken);
  return response;
}
