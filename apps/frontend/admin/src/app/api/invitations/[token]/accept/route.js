import { NextResponse } from 'next/server';

import { backendFetch } from '@/shared/api/apiClient';
import { assertSameOrigin, bffError } from '@/shared/api/bff';
import { setAuthCookiesOnResponse } from '@/shared/auth/cookies';

// POST /api/invitations/{token}/accept (public — invitee has no session yet)
//
// The backend returns `{accessToken, refreshToken}` on success. We
// strip those from the response body and write them as httpOnly cookies
// — mirroring the login handler — so the just-signed-up admin can
// router.push('/admin') and the next request carries the tokens via the
// usual cookie path. Returning 204 keeps the secrets out of any
// devtools / extension that might be watching the response payload.
//
// CSRF is asserted via Origin/Referer — the public page lives on the
// same admin host, so a cross-origin form post should still be rejected.
// The Edge proxy bypasses `/api/invitations/*` for auth (no access_token
// expected), but the bypass does not skip this handler — so CSRF and the
// backend call still run normally.
export async function POST(request, ctx) {
  const csrfFail = assertSameOrigin(request);
  if (csrfFail) return csrfFail;

  let body;
  try {
    body = await request.json();
  } catch {
    return bffError('BAD_REQUEST', 'Invalid request body', { status: 400 });
  }

  const { token } = await ctx.params;
  if (!token || typeof token !== 'string') {
    return bffError('BAD_REQUEST', 'Missing invitation token', { status: 400 });
  }

  const { ok, status, data } = await backendFetch(
    `/api/v1/invitations/${encodeURIComponent(token)}/accept`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
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

  if (
    !data ||
    typeof data.accessToken !== 'string' ||
    typeof data.refreshToken !== 'string'
  ) {
    // Backend said 200 but body is garbage — surface as a generic 502
    // rather than leaving the invitee on the page with no cookies and a
    // misleading success state.
    return bffError(
      'INVALID_RESPONSE',
      'Сервер не вернул токены сессии. Свяжитесь с администратором.',
      { status: 502 },
    );
  }

  const response = new NextResponse(null, { status: 204 });
  setAuthCookiesOnResponse(response, data.accessToken, data.refreshToken);
  return response;
}
