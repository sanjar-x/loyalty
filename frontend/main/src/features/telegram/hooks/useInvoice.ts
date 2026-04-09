'use client';

import { useCallback } from 'react';

import { getWebApp, callbackToPromise } from '../core';

import type { InvoiceStatus } from '../types';

export function useInvoice() {
  const webApp = getWebApp();
  const isAvailable = webApp !== null;

  const openInvoice = useCallback(
    (url: string): Promise<InvoiceStatus> => {
      if (!webApp) return Promise.resolve('failed' as InvoiceStatus);

      return callbackToPromise<InvoiceStatus>((cb) => {
        webApp.openInvoice(url, (status) => {
          cb(status);
        });
      });
    },
    [webApp],
  );

  return {
    openInvoice,
    isAvailable,
  };
}
