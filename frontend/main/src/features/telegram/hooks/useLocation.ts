'use client';

import { useState, useCallback, useEffect } from 'react';

import { getWebApp, supportsFeature, safeCall, callbackToPromise } from '../core';

import type { LocationData, EventType } from '../types';

export function useLocation() {
  const isAvailable = supportsFeature('LocationManager');

  const [isInited, setIsInited] = useState(false);
  const [isLocationAvailable, setIsLocationAvailable] = useState(false);
  const [isGranted, setIsGranted] = useState(false);

  const syncState = useCallback(() => {
    const wa = getWebApp();
    if (!wa) return;
    const lm = wa.LocationManager;
    setIsInited(lm.isInited);
    setIsLocationAvailable(lm.isLocationAvailable);
    setIsGranted(lm.isAccessGranted);
  }, []);

  const init = useCallback(() => {
    if (!isAvailable) return;
    const wa = getWebApp();
    if (!wa) return;

    safeCall(() => {
      wa.LocationManager.init(() => {
        syncState();
      });
    }, undefined);
  }, [isAvailable, syncState]);

  const getLocation = useCallback((): Promise<LocationData | null> => {
    if (!isAvailable) return Promise.resolve(null);
    const wa = getWebApp();
    if (!wa) return Promise.resolve(null);

    return callbackToPromise<LocationData | null>((cb) => {
      wa.LocationManager.getLocation((data) => cb(data));
    });
  }, [isAvailable]);

  const openSettings = useCallback(() => {
    if (!isAvailable) return;
    const wa = getWebApp();
    if (!wa) return;
    safeCall(() => wa.LocationManager.openSettings(), undefined);
  }, [isAvailable]);

  useEffect(() => {
    if (!isAvailable) return;
    const wa = getWebApp();
    if (!wa) return;

    const handler = () => syncState();

    wa.onEvent('locationManagerUpdated' as EventType, handler);
    return () => {
      wa.offEvent('locationManagerUpdated' as EventType, handler);
    };
  }, [isAvailable, syncState]);

  return {
    init,
    getLocation,
    openSettings,
    isInited,
    isLocationAvailable,
    isGranted,
    isAvailable,
  };
}
