'use client';

import { useCallback } from 'react';

import { getWebApp, callbackToPromise } from '../core';

import type { PopupParams } from '../types';

export function usePopup() {
  const webApp = getWebApp();
  const isAvailable = webApp !== null;

  const showPopup = useCallback(
    (params: PopupParams): Promise<string | null> => {
      if (!webApp) return Promise.resolve(null);

      return callbackToPromise<string | null>((cb) => {
        webApp.showPopup(params, (buttonId) => {
          cb(buttonId);
        });
      });
    },
    [webApp],
  );

  const showAlert = useCallback(
    (message: string): Promise<void> => {
      if (!webApp) return Promise.resolve();

      return callbackToPromise<void>((cb) => {
        webApp.showAlert(message, () => {
          cb(undefined as unknown as void);
        });
      });
    },
    [webApp],
  );

  const showConfirm = useCallback(
    (message: string): Promise<boolean> => {
      if (!webApp) return Promise.resolve(false);

      return callbackToPromise<boolean>((cb) => {
        webApp.showConfirm(message, (confirmed) => {
          cb(confirmed);
        });
      });
    },
    [webApp],
  );

  return {
    showPopup,
    showAlert,
    showConfirm,
    isAvailable,
  };
}
