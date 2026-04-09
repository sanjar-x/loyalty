'use client';

import { useCallback } from 'react';

import { getWebApp, callbackToPromise } from '../core';

import type { ScanQrPopupParams } from '../types';

export function useQrScanner() {
  const webApp = getWebApp();
  const isAvailable = webApp !== null;

  const show = useCallback(
    (params?: ScanQrPopupParams): Promise<string> => {
      if (!webApp) return Promise.resolve('');

      return callbackToPromise<string>((cb) => {
        webApp.showScanQrPopup(params ?? {}, (text) => {
          cb(text);
          return true; // close the popup after receiving text
        });
      });
    },
    [webApp],
  );

  const close = useCallback(() => {
    webApp?.closeScanQrPopup();
  }, [webApp]);

  return {
    show,
    close,
    isAvailable,
  };
}
