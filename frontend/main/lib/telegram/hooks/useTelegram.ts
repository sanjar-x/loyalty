'use client';

import { useTelegramContext } from '../TelegramProvider';

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
