'use client';

import { useCallback, useEffect, useRef } from 'react';
import { getWebApp } from '../core';

export function useBackButton(onBack?: () => void) {
  const callbackRef = useRef<(() => void) | undefined>(onBack);
  callbackRef.current = onBack;

  const webApp = getWebApp();
  const btn = webApp?.BackButton ?? null;
  const isAvailable = btn !== null;

  useEffect(() => {
    if (!btn || !callbackRef.current) return;

    const handler = () => {
      callbackRef.current?.();
    };

    btn.onClick(handler);
    btn.show();

    return () => {
      btn.offClick(handler);
      btn.hide();
    };
  }, [btn]);

  const show = useCallback(() => { btn?.show(); }, [btn]);
  const hide = useCallback(() => { btn?.hide(); }, [btn]);

  return {
    show,
    hide,
    isVisible: btn?.isVisible ?? false,
    isAvailable,
  };
}
