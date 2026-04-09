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

const DEFAULT_DEBUG_USER: Readonly<BrowserDebugUser> = Object.freeze({
  tg_id: '0000000000',
  username: 'debug_user',
  id: 0,
  registration_date: new Date().toISOString(),
  points: 0,
  level: 'debug',
});

export function isBrowserDebugAuthEnabled(): boolean {
  if (process.env.NODE_ENV === 'production') return false;
  const flag = String(
    process.env.BROWSER_DEBUG_AUTH || process.env.NEXT_PUBLIC_BROWSER_DEBUG_AUTH || '',
  )
    .trim()
    .toLowerCase();
  return flag === '1' || flag === 'true';
}

export function normalizeBrowserDebugUser(
  value: Record<string, unknown> | null | undefined,
): BrowserDebugUser | null {
  const source = value && typeof value === 'object' ? { ...DEFAULT_DEBUG_USER, ...value } : null;
  if (!source) return null;

  const tgIdRaw =
    (source as Record<string, unknown>).tg_id ??
    (source as Record<string, unknown>).tgId ??
    (source as Record<string, unknown>).telegram_id;
  const tgId =
    typeof tgIdRaw === 'number'
      ? String(tgIdRaw)
      : typeof tgIdRaw === 'string'
        ? tgIdRaw.trim()
        : '';

  if (!tgId) return null;

  const usernameRaw = source.username;
  const username =
    typeof usernameRaw === 'string' && usernameRaw.trim()
      ? usernameRaw.trim()
      : `tg_${tgId}`;

  return { ...source, tg_id: tgId, username };
}

export function getBrowserDebugUser(): BrowserDebugUser | null {
  return normalizeBrowserDebugUser(DEFAULT_DEBUG_USER as unknown as Record<string, unknown>);
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
