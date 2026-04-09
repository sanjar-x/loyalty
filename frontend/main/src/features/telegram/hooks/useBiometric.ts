'use client';

import { useState, useCallback, useEffect } from 'react';

import { getWebApp, supportsFeature, safeCall, callbackToPromise } from '../core';

import type {
  BiometricType,
  BiometricRequestAccessParams,
  BiometricAuthenticateParams,
  EventType,
} from '../types';

export function useBiometric() {
  const isAvailable = supportsFeature('BiometricManager');

  const [isInited, setIsInited] = useState(false);
  const [isBiometricAvailable, setIsBiometricAvailable] = useState(false);
  const [biometricType, setBiometricType] = useState<BiometricType>('unknown');
  const [deviceId, setDeviceId] = useState('');
  const [isAccessGranted, setIsAccessGranted] = useState(false);
  const [isTokenSaved, setIsTokenSaved] = useState(false);

  const syncState = useCallback(() => {
    const wa = getWebApp();
    if (!wa) return;
    const bm = wa.BiometricManager;
    setIsInited(bm.isInited);
    setIsBiometricAvailable(bm.isBiometricAvailable);
    setBiometricType(bm.biometricType);
    setDeviceId(bm.deviceId);
    setIsAccessGranted(bm.isAccessGranted);
    setIsTokenSaved(bm.isBiometricTokenSaved);
  }, []);

  const init = useCallback(() => {
    if (!isAvailable) return;
    const wa = getWebApp();
    if (!wa) return;
    safeCall(() => {
      wa.BiometricManager.init(() => syncState());
    }, undefined);
  }, [isAvailable, syncState]);

  const requestAccess = useCallback(
    (params?: BiometricRequestAccessParams): Promise<boolean> => {
      if (!isAvailable) return Promise.resolve(false);
      const wa = getWebApp();
      if (!wa) return Promise.resolve(false);

      return callbackToPromise<boolean>((cb) => {
        wa.BiometricManager.requestAccess(params ?? {}, (granted) => {
          syncState();
          cb(granted);
        });
      });
    },
    [isAvailable, syncState],
  );

  const authenticate = useCallback(
    (params?: BiometricAuthenticateParams): Promise<{ success: boolean; token?: string }> => {
      if (!isAvailable) return Promise.resolve({ success: false });
      const wa = getWebApp();
      if (!wa) return Promise.resolve({ success: false });

      return callbackToPromise<{ success: boolean; token?: string }>((cb) => {
        wa.BiometricManager.authenticate(params ?? {}, (success, token) => {
          syncState();
          cb({ success, token });
        });
      });
    },
    [isAvailable, syncState],
  );

  const updateToken = useCallback(
    (token: string): Promise<boolean> => {
      if (!isAvailable) return Promise.resolve(false);
      const wa = getWebApp();
      if (!wa) return Promise.resolve(false);

      return callbackToPromise<boolean>((cb) => {
        wa.BiometricManager.updateBiometricToken(token, (success) => {
          syncState();
          cb(success);
        });
      });
    },
    [isAvailable, syncState],
  );

  const openSettings = useCallback(() => {
    if (!isAvailable) return;
    const wa = getWebApp();
    if (!wa) return;
    safeCall(() => wa.BiometricManager.openSettings(), undefined);
  }, [isAvailable]);

  useEffect(() => {
    if (!isAvailable) return;
    const wa = getWebApp();
    if (!wa) return;

    const handler = () => syncState();
    wa.onEvent('biometricManagerUpdated' as EventType, handler);

    return () => {
      wa.offEvent('biometricManagerUpdated' as EventType, handler);
    };
  }, [isAvailable, syncState]);

  return {
    init,
    requestAccess,
    authenticate,
    updateToken,
    openSettings,
    isInited,
    isBiometricAvailable,
    biometricType,
    deviceId,
    isAccessGranted,
    isTokenSaved,
    isAvailable,
  };
}
