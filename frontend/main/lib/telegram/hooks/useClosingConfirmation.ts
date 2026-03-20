'use client';

import { useEffect, useRef } from 'react';
import { getWebApp, supportsFeature, safeCall } from '../core';

export function useClosingConfirmation(enabled: boolean) {
  const isAvailable = supportsFeature('enableClosingConfirmation');
  const wasEnabledRef = useRef(false);

  useEffect(() => {
    if (!isAvailable) return;
    const wa = getWebApp();
    if (!wa) return;

    if (enabled) {
      safeCall(() => wa.enableClosingConfirmation(), undefined);
      wasEnabledRef.current = true;
    } else {
      safeCall(() => wa.disableClosingConfirmation(), undefined);
      wasEnabledRef.current = false;
    }

    return () => {
      if (wasEnabledRef.current) {
        safeCall(() => wa.disableClosingConfirmation(), undefined);
        wasEnabledRef.current = false;
      }
    };
  }, [enabled, isAvailable]);

  return { isAvailable };
}
