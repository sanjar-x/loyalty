import { useMemo } from 'react';
import { getWebApp, supportsFeature, callbackToPromise } from '../core';

export function useCloudStorage() {
  const isAvailable = useMemo(() => supportsFeature('CloudStorage'), []);

  return useMemo(() => {
    const noop = {
      setItem: (_key: string, _value: string): Promise<boolean> =>
        Promise.resolve(false),
      getItem: (_key: string): Promise<string> => Promise.resolve(''),
      getItems: (_keys: string[]): Promise<Record<string, string>> =>
        Promise.resolve({}),
      removeItem: (_key: string): Promise<boolean> => Promise.resolve(false),
      removeItems: (_keys: string[]): Promise<boolean> =>
        Promise.resolve(false),
      getKeys: (): Promise<string[]> => Promise.resolve([]),
      isAvailable: false as const,
    };

    if (!isAvailable) return noop;

    const cs = getWebApp()?.CloudStorage;
    if (!cs) return noop;

    return {
      setItem: (key: string, value: string): Promise<boolean> =>
        callbackToPromise<boolean>((cb) => {
          cs.setItem(key, value, (_err, success) => cb(success));
        }),

      getItem: (key: string): Promise<string> =>
        callbackToPromise<string>((cb) => {
          cs.getItem(key, (_err, value) => cb(value));
        }),

      getItems: (keys: string[]): Promise<Record<string, string>> =>
        callbackToPromise<Record<string, string>>((cb) => {
          cs.getItems(keys, (_err, values) => cb(values));
        }),

      removeItem: (key: string): Promise<boolean> =>
        callbackToPromise<boolean>((cb) => {
          cs.removeItem(key, (_err, success) => cb(success));
        }),

      removeItems: (keys: string[]): Promise<boolean> =>
        callbackToPromise<boolean>((cb) => {
          cs.removeItems(keys, (_err, success) => cb(success));
        }),

      getKeys: (): Promise<string[]> =>
        callbackToPromise<string[]>((cb) => {
          cs.getKeys((_err, keys) => cb(keys));
        }),

      isAvailable: true as const,
    };
  }, [isAvailable]);
}
