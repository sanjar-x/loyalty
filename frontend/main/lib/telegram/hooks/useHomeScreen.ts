'use client';

import { useCallback } from 'react';
import { getWebApp, supportsFeature, safeCall, callbackToPromise } from '../core';
import type { HomeScreenStatus, EventType } from '../types';

export function useHomeScreen() {
  const isAvailable = supportsFeature('addToHomeScreen');

  const addToHomeScreen = useCallback(() => {
    if (!isAvailable) return;
    const wa = getWebApp();
    if (!wa) return;
    safeCall(() => wa.addToHomeScreen(), undefined);
  }, [isAvailable]);

  const checkStatus = useCallback((): Promise<HomeScreenStatus> => {
    if (!isAvailable) return Promise.resolve('unsupported' as HomeScreenStatus);
    const wa = getWebApp();
    if (!wa) return Promise.resolve('unsupported' as HomeScreenStatus);

    return callbackToPromise<HomeScreenStatus>((cb) => {
      wa.checkHomeScreenStatus((status) => cb(status));
    });
  }, [isAvailable]);

  return { addToHomeScreen, checkStatus, isAvailable };
}
