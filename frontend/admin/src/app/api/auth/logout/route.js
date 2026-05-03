import { NextResponse } from 'next/server';
import { backendFetch } from '@/shared/api/api-client';
import { assertSameOrigin } from '@/shared/api/bff';
import {
  getAccessToken,
  clearAuthCookiesOnResponse,
} from '@/shared/auth/cookies';

export async function POST(request) {
  const csrfFail = assertSameOrigin(request);
  if (csrfFail) return csrfFail;

  const accessToken = await getAccessToken();

  if (accessToken) {
    await backendFetch('/api/v1/auth/logout', {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    // Best-effort — ignore backend errors (token may be expired)
  }

  const response = NextResponse.json({ success: true });
  clearAuthCookiesOnResponse(response);
  return response;
}
