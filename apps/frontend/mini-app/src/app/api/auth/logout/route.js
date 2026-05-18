import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

import { ACCESS_COOKIE } from '@/features/auth-telegram/lib/cookies';
import { clearTokenCookies } from '@/features/auth-telegram/lib/cookie-helpers';
import { getBackendBaseUrl } from '@/shared/api/bff';

export async function POST() {
  // Best-effort backend logout — cookies are cleared even on error.
  // The shared `getBackendBaseUrl` throws if the env is missing — we
  // catch it here and turn it into `null`: logout continues without a
  // backend call.
  let backendBase = null;
  try {
    backendBase = getBackendBaseUrl();
  } catch {
    backendBase = null;
  }
  if (backendBase) {
    try {
      const cookieJar = await cookies();
      const accessToken = cookieJar.get(ACCESS_COOKIE)?.value || '';
      if (accessToken) {
        await fetch(`${backendBase}/api/v1/auth/logout`, {
          method: 'POST',
          headers: {
            authorization: `Bearer ${accessToken}`,
            accept: 'application/json',
          },
        });
      }
    } catch {
      // ignore — cookies are always cleared
    }
  }

  const res = NextResponse.json({ ok: true }, { status: 200 });
  clearTokenCookies(res);
  return res;
}
