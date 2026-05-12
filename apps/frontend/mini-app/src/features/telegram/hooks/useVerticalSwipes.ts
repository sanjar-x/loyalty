'use client';

import { useEffect, useRef } from 'react';

import { getWebApp, supportsFeature, safeCall } from '../core';

export function useVerticalSwipes(enabled: boolean) {
  const isAvailable = supportsFeature('enableVerticalSwipes');
  const wasEnabledRef = useRef(false);

  useEffect(() => {
    if (!isAvailable) return;
    const wa = getWebApp();
    if (!wa) return;

    if (enabled) {
      safeCall(() => wa.enableVerticalSwipes(), undefined);
      wasEnabledRef.current = true;
    } else {
      safeCall(() => wa.disableVerticalSwipes(), undefined);
      wasEnabledRef.current = false;
    }

    return () => {
      if (wasEnabledRef.current) {
        safeCall(() => wa.disableVerticalSwipes(), undefined);
        wasEnabledRef.current = false;
      }
    };
  }, [enabled, isAvailable]);

  return { isAvailable };
}
