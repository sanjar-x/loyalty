'use client';

import { useCallback } from 'react';

import { getWebApp, callbackToPromise } from '../core';

export function useClipboard() {
  const webApp = getWebApp();
  const isAvailable = webApp !== null;

  const readText = useCallback((): Promise<string | null> => {
    if (!webApp) return Promise.resolve(null);

    return callbackToPromise<string | null>((cb) => {
      webApp.readTextFromClipboard((text) => {
        cb(text);
      });
    });
  }, [webApp]);

  return {
    readText,
    isAvailable,
  };
}
