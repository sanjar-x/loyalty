'use client';

import { useCallback } from 'react';

import { useTelegramContext } from '../provider';

export function useViewport() {
  const ctx = useTelegramContext();

  const expand = useCallback(() => {
    ctx.webApp?.expand();
  }, [ctx.webApp]);

  return {
    viewportHeight: ctx.viewportHeight,
    viewportStableHeight: ctx.viewportStableHeight,
    isExpanded: ctx.isExpanded,
    safeAreaInset: ctx.safeAreaInset,
    contentSafeAreaInset: ctx.contentSafeAreaInset,
    expand,
    isAvailable: ctx.webApp !== null,
  };
}
