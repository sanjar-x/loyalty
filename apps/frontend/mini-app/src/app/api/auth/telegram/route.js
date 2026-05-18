import { NextResponse } from 'next/server';

import { setTokenCookies } from '@/features/auth-telegram/lib/cookie-helpers';
import {
  isBrowserDebugAuthEnabled,
  MOCK_DEBUG_USER,
  createMockToken,
} from '@/features/auth-telegram/lib/debug';
import { getBackendBaseUrl } from '@/shared/api/bff';

export async function POST(req) {
  let backendBase;
  try {
    backendBase = getBackendBaseUrl();
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : 'Server config error' },
      { status: 500 }
    );
  }

  let body;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  const initData = typeof body?.initData === 'string' ? body.initData.trim() : '';

  // Debug mode — works in environments without the Telegram SDK
  const isDebug = !initData && isBrowserDebugAuthEnabled();

  if (!initData && !isDebug) {
    return NextResponse.json({ error: 'initData is required' }, { status: 400 });
  }

  // Forward to backend: Authorization: tma <initData>
  const authHeader = initData ? `tma ${initData}` : `tma debug_user_${MOCK_DEBUG_USER.tg_id}`;

  let upstreamRes;
  try {
    upstreamRes = await fetch(`${backendBase}/api/v1/auth/telegram`, {
      method: 'POST',
      headers: { accept: 'application/json', authorization: authHeader },
    });
  } catch (e) {
    // Debug mode fallback — backend unreachable, create a mock token
    if (isDebug) {
      const mockAccess = createMockToken(MOCK_DEBUG_USER.tg_id);
      const mockRefresh = createMockToken(`refresh_${MOCK_DEBUG_USER.tg_id}`);
      const res = NextResponse.json({ ok: true, isNewUser: false }, { status: 200 });
      setTokenCookies(res, mockAccess, mockRefresh);
      return res;
    }
    return NextResponse.json({ error: 'Backend unreachable', hint: e?.message }, { status: 502 });
  }

  // Debug mode — mock token fallback if the backend returns an error
  if (!upstreamRes.ok && isDebug) {
    const mockAccess = createMockToken(MOCK_DEBUG_USER.tg_id);
    const mockRefresh = createMockToken(`refresh_${MOCK_DEBUG_USER.tg_id}`);
    const res = NextResponse.json({ ok: true, isNewUser: false }, { status: 200 });
    setTokenCookies(res, mockAccess, mockRefresh);
    return res;
  }

  const text = await upstreamRes.text();
  let json = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    json = null;
  }

  if (!upstreamRes.ok) {
    return NextResponse.json(
      { error: 'Backend auth failed', status: upstreamRes.status, details: json ?? text },
      { status: 502 }
    );
  }

  const accessToken = json?.accessToken;
  const refreshToken = json?.refreshToken;
  const isNewUser = json?.isNewUser ?? false;

  if (typeof accessToken !== 'string' || !accessToken) {
    return NextResponse.json(
      { error: 'Backend did not return accessToken', details: json },
      { status: 502 }
    );
  }

  // Extract user info from initData (for creating the profile)
  let tgUser = null;
  try {
    const params = new URLSearchParams(initData);
    const userJson = params.get('user');
    if (userJson) tgUser = JSON.parse(userJson);
  } catch {
    // ignore parse errors
  }

  // Auto-create a profile for a new user
  if (isNewUser && tgUser) {
    const profileBody = {};
    if (tgUser.first_name) profileBody.firstName = tgUser.first_name;
    if (tgUser.last_name) profileBody.lastName = tgUser.last_name;

    try {
      const patchRes = await fetch(`${backendBase}/api/v1/profile/me`, {
        method: 'PATCH',
        headers: {
          'content-type': 'application/json',
          accept: 'application/json',
          authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify(profileBody),
      });
      // Don't block auth (best-effort), but log it — otherwise it is
      // impossible to count how many new users lose profile data.
      if (!patchRes.ok) {
        console.error('[auth/telegram] new-user profile patch failed', {
          tgId: tgUser?.id,
          status: patchRes.status,
        });
      }
    } catch (e) {
      console.error('[auth/telegram] new-user profile patch threw', {
        tgId: tgUser?.id,
        error: e?.message,
      });
    }
  }

  // Tokens go only in HttpOnly cookies — NEVER returned in the JSON body
  const res = NextResponse.json({ ok: true, isNewUser }, { status: 200 });
  setTokenCookies(res, accessToken, refreshToken);
  return res;
}
