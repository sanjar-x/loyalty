import { NextResponse } from 'next/server';
import { cookies } from 'next/headers';

import { ACCESS_COOKIE } from '@/lib/features/auth/lib/cookies';
import { clearTokenCookies } from '@/lib/features/auth/lib/cookie-helpers';
import { getBackendBaseUrl } from '@/lib/api/server/backendBaseUrl';

export async function POST() {
  // Best-effort backend logout — xato bo'lsa ham cookie tozalanadi.
  // Shared `getBackendBaseUrl` env yo'q bo'lsa `throw` qiladi — bu yerda
  // ushlab `null`'ga aylantiramiz: logout backend chaqiruvisiz ham davom etadi.
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
      // ignore — cookie har doim tozalanadi
    }
  }

  const res = NextResponse.json({ ok: true }, { status: 200 });
  clearTokenCookies(res);
  return res;
}
