import { useMemo } from 'react';
import { getWebApp, supportsFeature, callbackToPromise } from '../core';

export function useDeviceStorage() {
  const isAvailable = useMemo(() => supportsFeature('DeviceStorage'), []);

  return useMemo(() => {
    const noop = {
      setItem: (_key: string, _value: string): Promise<boolean> =>
        Promise.resolve(false),
      getItem: (_key: string): Promise<string> => Promise.resolve(''),
      removeItem: (_key: string): Promise<boolean> => Promise.resolve(false),
      clear: (): Promise<boolean> => Promise.resolve(false),
      isAvailable: false as const,
    };

    if (!isAvailable) return noop;

    const ds = getWebApp()?.DeviceStorage;
    if (!ds) return noop;

    return {
      setItem: (key: string, value: string): Promise<boolean> =>
        callbackToPromise<boolean>((cb) => {
          ds.setItem(key, value, (_err, success) => cb(success));
        }),

      getItem: (key: string): Promise<string> =>
        callbackToPromise<string>((cb) => {
          ds.getItem(key, (_err, value) => cb(value));
        }),

      removeItem: (key: string): Promise<boolean> =>
        callbackToPromise<boolean>((cb) => {
          ds.removeItem(key, (_err, success) => cb(success));
        }),

      clear: (): Promise<boolean> =>
        callbackToPromise<boolean>((cb) => {
          ds.clear((_err, success) => cb(success));
        }),

      isAvailable: true as const,
    };
  }, [isAvailable]);
}
