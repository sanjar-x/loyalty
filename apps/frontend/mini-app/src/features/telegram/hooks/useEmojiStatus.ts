'use client';

import { useCallback } from 'react';

import { getWebApp, supportsFeature, callbackToPromise } from '../core';

import type { EmojiStatusParams, EventType } from '../types';

export function useEmojiStatus() {
  const isAvailable = supportsFeature('setEmojiStatus');

  const setEmojiStatus = useCallback(
    (emojiId: string, params?: EmojiStatusParams): Promise<boolean> => {
      if (!isAvailable) return Promise.resolve(false);
      const wa = getWebApp();
      if (!wa) return Promise.resolve(false);

      return callbackToPromise<boolean>((cb) => {
        const onSet = () => {
          cleanup();
          cb(true);
        };
        const onFailed = () => {
          cleanup();
          cb(false);
        };
        const cleanup = () => {
          wa.offEvent('emojiStatusSet' as EventType, onSet);
          wa.offEvent('emojiStatusFailed' as EventType, onFailed);
        };

        wa.onEvent('emojiStatusSet' as EventType, onSet);
        wa.onEvent('emojiStatusFailed' as EventType, onFailed);
        wa.setEmojiStatus(emojiId, params);
      });
    },
    [isAvailable],
  );

  const requestAccess = useCallback((): Promise<boolean> => {
    if (!isAvailable) return Promise.resolve(false);
    const wa = getWebApp();
    if (!wa) return Promise.resolve(false);

    return callbackToPromise<boolean>((cb) => {
      const handler = (...args: unknown[]) => {
        wa.offEvent('emojiStatusAccessRequested' as EventType, handler);
        const granted = (args[0] as { status: string })?.status === 'allowed';
        cb(granted);
      };
      wa.onEvent('emojiStatusAccessRequested' as EventType, handler);
      wa.requestEmojiStatusAccess();
    });
  }, [isAvailable]);

  return { setEmojiStatus, requestAccess, isAvailable };
}
