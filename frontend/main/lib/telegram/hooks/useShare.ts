'use client';

import { useCallback } from 'react';
import {
  getWebApp,
  supportsFeature,
  safeCall,
  callbackToPromise,
} from '../core';
import type {
  StoryShareParams,
  DownloadFileParams,
  EventType,
} from '../types';

export function useShare() {
  const isAvailable =
    supportsFeature('shareToStory') || supportsFeature('shareMessage');

  const shareToStory = useCallback(
    (mediaUrl: string, params?: StoryShareParams) => {
      if (!supportsFeature('shareToStory')) return;
      const wa = getWebApp();
      if (!wa) return;
      safeCall(() => wa.shareToStory(mediaUrl, params), undefined);
    },
    [],
  );

  const shareMessage = useCallback(
    (msgId: string): Promise<boolean> => {
      if (!supportsFeature('shareMessage')) return Promise.resolve(false);
      const wa = getWebApp();
      if (!wa) return Promise.resolve(false);

      return callbackToPromise<boolean>((cb) => {
        const onSent = () => {
          cleanup();
          cb(true);
        };
        const onFailed = () => {
          cleanup();
          cb(false);
        };
        const cleanup = () => {
          wa.offEvent('shareMessageSent' as EventType, onSent);
          wa.offEvent('shareMessageFailed' as EventType, onFailed);
        };

        wa.onEvent('shareMessageSent' as EventType, onSent);
        wa.onEvent('shareMessageFailed' as EventType, onFailed);
        wa.shareMessage(msgId);
      });
    },
    [],
  );

  const downloadFile = useCallback(
    (params: DownloadFileParams): Promise<boolean> => {
      if (!supportsFeature('downloadFile')) return Promise.resolve(false);
      const wa = getWebApp();
      if (!wa) return Promise.resolve(false);

      return callbackToPromise<boolean>((cb) => {
        wa.downloadFile(params, (success) => cb(success));
      });
    },
    [],
  );

  return { shareToStory, shareMessage, downloadFile, isAvailable };
}
