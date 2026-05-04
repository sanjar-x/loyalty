/** Browser debug auth — Telegram SDK bo'lmagan muhitda ishlash uchun. */

export const MOCK_DEBUG_USER = Object.freeze({
  tg_id: "0000000000",
  username: "debug_user",
});

export function isBrowserDebugAuthEnabled() {
  if (process.env.NODE_ENV !== "production") return true;

  const clientFlag = String(process.env.NEXT_PUBLIC_BROWSER_DEBUG_AUTH || "")
    .trim()
    .toLowerCase();
  if (clientFlag === "1" || clientFlag === "true") return true;

  const serverFlag = String(process.env.BROWSER_DEBUG_AUTH || "")
    .trim()
    .toLowerCase();
  if (serverFlag === "1" || serverFlag === "true") return true;

  return false;
}

export function createMockToken(tgId) {
  return `debug_${tgId}_${Date.now()}`;
}
