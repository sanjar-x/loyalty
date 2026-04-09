'use client';

import { useTelegramContext } from '../provider';

export function useTheme() {
  const ctx = useTelegramContext();

  return {
    themeParams: ctx.themeParams,
    colorScheme: ctx.colorScheme,
    isDark: ctx.colorScheme === 'dark',
    isAvailable: ctx.webApp !== null,
  };
}
