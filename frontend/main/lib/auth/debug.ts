export interface BrowserDebugUser {
  tg_id: string;
  username: string;
  id: number;
  registration_date: string;
  points: number;
  level: string;
  [key: string]: unknown;
}

interface BrowserDebugTelegramUser {
  id: number | string;
  username: string;
}

const BROWSER_DEBUG_USER: Readonly<BrowserDebugUser> = Object.freeze({
  tg_id: "7427756366",
  username: "yokub_janovich",
  id: 2,
  registration_date: "2026-02-07T11:37:15.221455Z",
  points: 0,
  level: "стартовый",
});

export function isBrowserDebugAuthEnabled(): boolean {
  // NEVER allow debug auth in production — regardless of env flags.
  if (process.env.NODE_ENV === "production") return false;

  // Check both server-side and client-side env flags.
  // BROWSER_DEBUG_AUTH is available in server contexts (API routes).
  // NEXT_PUBLIC_BROWSER_DEBUG_AUTH is inlined into the client bundle by Next.js.
  const flag =
    String(process.env.BROWSER_DEBUG_AUTH || process.env.NEXT_PUBLIC_BROWSER_DEBUG_AUTH || "")
      .trim()
      .toLowerCase();
  return flag === "1" || flag === "true";
}

export function normalizeBrowserDebugUser(
  value: Record<string, unknown> | null | undefined,
): BrowserDebugUser | null {
  const source =
    value && typeof value === "object"
      ? { ...BROWSER_DEBUG_USER, ...value }
      : null;
  if (!source) return null;

  const tgIdRaw =
    (source as Record<string, unknown>).tg_id ??
    (source as Record<string, unknown>).tgId ??
    (source as Record<string, unknown>).telegram_id;
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

export function getBrowserDebugUser(): BrowserDebugUser | null {
  return normalizeBrowserDebugUser(
    BROWSER_DEBUG_USER as unknown as Record<string, unknown>,
  );
}

export function getBrowserDebugTelegramUser(): BrowserDebugTelegramUser | null {
  const user = getBrowserDebugUser();
  if (!user) return null;

  const numericTgId = Number(user.tg_id);

  return {
    id: Number.isFinite(numericTgId) ? numericTgId : user.tg_id,
    username: user.username,
  };
}
