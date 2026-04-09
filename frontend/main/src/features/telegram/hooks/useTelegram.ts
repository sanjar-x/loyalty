'use client';

import { useTelegramContext } from '../provider';

/**
 * Public facade over the Telegram context for most feature code.
 * Returns the stable, app-facing subset plus `isAvailable`.
 */
export function useTelegram() {
  const ctx = useTelegramContext();

  return {
    webApp: ctx.webApp,
    user: ctx.user,
    initData: ctx.initData,
    initDataUnsafe: ctx.initDataUnsafe,
    platform: ctx.platform,
    version: ctx.version,
    isReady: ctx.isReady,
    isActive: ctx.isActive,
    isAvailable: ctx.webApp !== null,
  };
}
