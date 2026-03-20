import { useCallback } from 'react';
import type { InvoiceStatus } from '../types';
import { getWebApp, callbackToPromise } from '../core';

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
