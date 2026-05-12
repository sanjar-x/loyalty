'use client';

import { useMemo } from 'react';

import { getWebApp, supportsFeature, callbackToPromise } from '../core';

interface SecureStorageGetResult {
  value: string;
  canRestore: boolean;
}

export function useSecureStorage() {
  const isAvailable = useMemo(() => supportsFeature('SecureStorage'), []);

  return useMemo(() => {
    const noop = {
      setItem: (_key: string, _value: string): Promise<boolean> => Promise.resolve(false),
      getItem: (_key: string): Promise<SecureStorageGetResult> =>
        Promise.resolve({ value: '', canRestore: false }),
      restoreItem: (_key: string): Promise<boolean> => Promise.resolve(false),
      removeItem: (_key: string): Promise<boolean> => Promise.resolve(false),
      clear: (): Promise<boolean> => Promise.resolve(false),
      isAvailable: false as const,
    };

    if (!isAvailable) return noop;

    const ss = getWebApp()?.SecureStorage;
    if (!ss) return noop;

    return {
      setItem: (key: string, value: string): Promise<boolean> =>
        callbackToPromise<boolean>((cb) => {
          ss.setItem(key, value, (_err, success) => cb(success));
        }),

      getItem: (key: string): Promise<SecureStorageGetResult> =>
        callbackToPromise<SecureStorageGetResult>((cb) => {
          ss.getItem(key, (_err, value, canRestore) => cb({ value, canRestore }));
        }),

      restoreItem: (key: string): Promise<boolean> =>
        callbackToPromise<boolean>((cb) => {
          ss.restoreItem(key, (_err, success) => cb(success));
        }),

      removeItem: (key: string): Promise<boolean> =>
        callbackToPromise<boolean>((cb) => {
          ss.removeItem(key, (_err, success) => cb(success));
        }),

      clear: (): Promise<boolean> =>
        callbackToPromise<boolean>((cb) => {
          ss.clear((_err, success) => cb(success));
        }),

      isAvailable: true as const,
    };
  }, [isAvailable]);
}
