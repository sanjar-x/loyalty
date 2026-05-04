import { NextResponse } from "next/server";

import { setTokenCookies } from "@/lib/features/auth/lib/cookie-helpers";
import {
  isBrowserDebugAuthEnabled,
  MOCK_DEBUG_USER,
  createMockToken,
} from "@/lib/features/auth/lib/debug";

function getBackendBaseUrl() {
  const raw = process.env.BACKEND_API_BASE_URL;
  if (!raw || typeof raw !== "string" || !raw.trim()) {
    throw new Error("Missing BACKEND_API_BASE_URL");
  }
  return raw.trim().replace(/\/+$/, "");
}

export async function POST(req) {
  let backendBase;
  try {
    backendBase = getBackendBaseUrl();
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : "Server config error" },
      { status: 500 },
    );
  }

  let body;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const initData =
    typeof body?.initData === "string" ? body.initData.trim() : "";

  // Debug mode — Telegram SDK bo'lmagan muhitda ishlash
  const isDebug = !initData && isBrowserDebugAuthEnabled();

  if (!initData && !isDebug) {
    return NextResponse.json(
      { error: "initData is required" },
      { status: 400 },
    );
  }

  // Backend ga forward: Authorization: tma <initData>
  const authHeader = initData
    ? `tma ${initData}`
    : `tma debug_user_${MOCK_DEBUG_USER.tg_id}`;

  let upstreamRes;
  try {
    upstreamRes = await fetch(`${backendBase}/api/v1/auth/telegram`, {
      method: "POST",
      headers: { accept: "application/json", authorization: authHeader },
    });
  } catch (e) {
    // Debug mode fallback — backend unreachable, mock token yaratish
    if (isDebug) {
      const mockAccess = createMockToken(MOCK_DEBUG_USER.tg_id);
      const mockRefresh = createMockToken(`refresh_${MOCK_DEBUG_USER.tg_id}`);
      const res = NextResponse.json(
        { ok: true, isNewUser: false },
        { status: 200 },
      );
      setTokenCookies(res, mockAccess, mockRefresh);
      return res;
    }
    return NextResponse.json(
      { error: "Backend unreachable", hint: e?.message },
      { status: 502 },
    );
  }

  // Debug mode — backend xato qaytarsa mock token fallback
  if (!upstreamRes.ok && isDebug) {
    const mockAccess = createMockToken(MOCK_DEBUG_USER.tg_id);
    const mockRefresh = createMockToken(`refresh_${MOCK_DEBUG_USER.tg_id}`);
    const res = NextResponse.json(
      { ok: true, isNewUser: false },
      { status: 200 },
    );
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
      { error: "Backend auth failed", status: upstreamRes.status, details: json ?? text },
      { status: 502 },
    );
  }

  const accessToken = json?.accessToken;
  const refreshToken = json?.refreshToken;
  const isNewUser = json?.isNewUser ?? false;

  if (typeof accessToken !== "string" || !accessToken) {
    return NextResponse.json(
      { error: "Backend did not return accessToken", details: json },
      { status: 502 },
    );
  }

  // initData dan user ma'lumotlarini ajratib olish (profil yaratish uchun)
  let tgUser = null;
  try {
    const params = new URLSearchParams(initData);
    const userJson = params.get("user");
    if (userJson) tgUser = JSON.parse(userJson);
  } catch {
    // ignore parse errors
  }

  // Yangi foydalanuvchi uchun profilni avtomatik yaratish
  if (isNewUser && tgUser) {
    try {
      const profileBody = {};
      if (tgUser.first_name) profileBody.firstName = tgUser.first_name;
      if (tgUser.last_name) profileBody.lastName = tgUser.last_name;

      await fetch(`${backendBase}/api/v1/profile/me`, {
        method: "PATCH",
        headers: {
          "content-type": "application/json",
          accept: "application/json",
          authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify(profileBody),
      });
    } catch {
      // Profil yaratish xatoligi auth ni to'xtatmasligi kerak
    }
  }

  // Tokenlar faqat HttpOnly cookie da — HECH QACHON JSON body da qaytmaydi
  const res = NextResponse.json({ ok: true, isNewUser }, { status: 200 });
  setTokenCookies(res, accessToken, refreshToken);
  return res;
}
