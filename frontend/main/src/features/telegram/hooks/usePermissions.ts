'use client';

import { useCallback } from 'react';

import { getWebApp, callbackToPromise } from '../core';

import type { WriteAccessStatus, ContactRequestStatus } from '../types';

export function usePermissions() {
  const webApp = getWebApp();
  const isAvailable = webApp !== null;

  const requestWriteAccess = useCallback((): Promise<WriteAccessStatus> => {
    if (!webApp) return Promise.resolve('cancelled' as WriteAccessStatus);

    return callbackToPromise<WriteAccessStatus>((cb) => {
      webApp.requestWriteAccess((status) => {
        cb(status);
      });
    });
  }, [webApp]);

  const requestContact = useCallback((): Promise<ContactRequestStatus> => {
    if (!webApp) return Promise.resolve('cancelled' as ContactRequestStatus);

    return callbackToPromise<ContactRequestStatus>((cb) => {
      webApp.requestContact((status) => {
        cb(status);
      });
    });
  }, [webApp]);

  return {
    requestWriteAccess,
    requestContact,
    isAvailable,
  };
}
