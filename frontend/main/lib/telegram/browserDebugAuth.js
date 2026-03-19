const BROWSER_DEBUG_USER = Object.freeze({
  tg_id: "7427756366",
  username: "yokub_janovich",
  id: 2,
  registration_date: "2026-02-07T11:37:15.221455Z",
  points: 0,
  level: "стартовый",
});

export function isBrowserDebugAuthEnabled() {
  // Default: enabled in local dev.
  if (process.env.NODE_ENV !== "production") return true;

  // Production builds (including Vercel preview/prod) must opt-in explicitly.
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

export function normalizeBrowserDebugUser(value) {
  const source =
    value && typeof value === "object"
      ? { ...BROWSER_DEBUG_USER, ...value }
      : null;
  if (!source) return null;

  const tgIdRaw = source.tg_id ?? source.tgId ?? source.telegram_id;
  const tgId =
    typeof tgIdRaw === "number"
      ? String(tgIdRaw)
      : typeof tgIdRaw === "string"
        ? tgIdRaw.trim()
        : "";

  if (!tgId) return null;

  const usernameRaw = source.username;
  const username =
    typeof usernameRaw === "string" && usernameRaw.trim()
      ? usernameRaw.trim()
      : `tg_${tgId}`;

  return {
    ...source,
    tg_id: tgId,
    username,
  };
}

export function getBrowserDebugUser() {
  return normalizeBrowserDebugUser(BROWSER_DEBUG_USER);
}

export function getBrowserDebugTelegramUser() {
  const user = getBrowserDebugUser();
  if (!user) return null;

  const numericTgId = Number(user.tg_id);

  return {
    id: Number.isFinite(numericTgId) ? numericTgId : user.tg_id,
    username: user.username,
  };
}
