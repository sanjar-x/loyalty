/* eslint-disable react-hooks/set-state-in-effect -- Telegram SDK event handler */
'use client';

import { useState, useCallback, useEffect } from 'react';

import { getWebApp, supportsFeature, safeCall } from '../core';

import type { EventType } from '../types';

export function useFullscreen() {
  const isAvailable = supportsFeature('requestFullscreen');

  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isOrientationLocked, setIsOrientationLocked] = useState(false);

  const syncState = useCallback(() => {
    const wa = getWebApp();
    if (!wa) return;
    setIsFullscreen(wa.isFullscreen);
    setIsOrientationLocked(wa.isOrientationLocked);
  }, []);

  const request = useCallback(() => {
    if (!isAvailable) return;
    const wa = getWebApp();
    if (!wa) return;
    safeCall(() => wa.requestFullscreen(), undefined);
  }, [isAvailable]);

  const exit = useCallback(() => {
    if (!isAvailable) return;
    const wa = getWebApp();
    if (!wa) return;
    safeCall(() => wa.exitFullscreen(), undefined);
  }, [isAvailable]);

  const lockOrientation = useCallback(() => {
    if (!isAvailable) return;
    const wa = getWebApp();
    if (!wa) return;
    safeCall(() => wa.lockOrientation(), undefined);
  }, [isAvailable]);

  const unlockOrientation = useCallback(() => {
    if (!isAvailable) return;
    const wa = getWebApp();
    if (!wa) return;
    safeCall(() => wa.unlockOrientation(), undefined);
  }, [isAvailable]);

  useEffect(() => {
    if (!isAvailable) return;
    const wa = getWebApp();
    if (!wa) return;

    syncState();

    const onChanged = () => syncState();
    const onFailed = () => syncState();

    wa.onEvent('fullscreenChanged' as EventType, onChanged);
    wa.onEvent('fullscreenFailed' as EventType, onFailed);

    return () => {
      wa.offEvent('fullscreenChanged' as EventType, onChanged);
      wa.offEvent('fullscreenFailed' as EventType, onFailed);
    };
  }, [isAvailable, syncState]);

  return {
    request,
    exit,
    isFullscreen,
    lockOrientation,
    unlockOrientation,
    isOrientationLocked,
    isAvailable,
  };
}
