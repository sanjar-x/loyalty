'use client';

import { useEffect, useRef } from 'react';

import { useQueryClient } from '@tanstack/react-query';

import { useTelegram } from '@/features/telegram/hooks/useTelegram';
import { onAuthExpired } from '@/lib/auth-events';

import { getBrowserDebugUser, isBrowserDebugAuthEnabled } from '../lib/debug';
import { useAuthStore } from '../store';

import type { TelegramAuthResponse } from '../types';

interface TelegramAuthRequest {
  key: string;
  body: Record<string, unknown>;
}

function buildTelegramAuthRequest(initData: string): TelegramAuthRequest | null {
  const normalizedInitData = initData.trim();
  if (normalizedInitData) {
    return {
      key: `telegram:${normalizedInitData}`,
      body: { initData: normalizedInitData },
    };
  }

  if (!isBrowserDebugAuthEnabled()) return null;

  const debugUser = getBrowserDebugUser();
  if (!debugUser) return null;

  return {
    key: `debug:${debugUser.tg_id}`,
    body: { debugUser },
  };
}

export function TelegramAuthBootstrap(): null {
  const queryClient = useQueryClient();
  const { initData, isReady } = useTelegram();
  const authStatus = useAuthStore((state) => state.status);
  const inFlightSourceRef = useRef<string | null>(null);
  const failedSourceRef = useRef<string | null>(null);

  useEffect(() => {
    return onAuthExpired(() => {
      failedSourceRef.current = null;
      useAuthStore.getState().sessionExpired();
    });
  }, []);

  useEffect(() => {
    if (!isReady) return;

    const authRequest = buildTelegramAuthRequest(initData);
    if (!authRequest) return;

    if (authStatus === 'authenticated' || authStatus === 'loading' || authStatus === 'logged_out') {
      return;
    }

    if (inFlightSourceRef.current === authRequest.key) return;
    if (authStatus === 'error' && failedSourceRef.current === authRequest.key) return;

    const shouldAuthenticate =
      authStatus === 'idle' ||
      authStatus === 'expired' ||
      (authStatus === 'error' && failedSourceRef.current !== authRequest.key);

    if (!shouldAuthenticate) return;

    inFlightSourceRef.current = authRequest.key;
    useAuthStore.getState().authStart();

    fetch('/api/auth/telegram', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(authRequest.body),
    })
      .then(async (response) => {
        if (!response.ok) {
          const errorBody = await response.json().catch(() => ({}));
          const message =
            typeof errorBody?.error === 'string'
              ? errorBody.error
              : `Auth failed: ${response.status}`;
          throw new Error(message);
        }

        return response.json() as Promise<TelegramAuthResponse>;
      })
      .then((data) => {
        failedSourceRef.current = null;
        useAuthStore.getState().authSuccess({ isNewUser: data?.isNewUser === true });
        void queryClient.invalidateQueries();
      })
      .catch((error: unknown) => {
        failedSourceRef.current = authRequest.key;
        useAuthStore.getState().authFailure(error instanceof Error ? error.message : 'Auth error');
      })
      .finally(() => {
        if (inFlightSourceRef.current === authRequest.key) {
          inFlightSourceRef.current = null;
        }
      });
  }, [authStatus, initData, isReady, queryClient]);

  return null;
}
