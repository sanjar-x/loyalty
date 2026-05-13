'use client';

import { useCallback } from 'react';

import { getWebApp } from '../core';

import type { ChatType } from '../types';

export function useLinks() {
  const webApp = getWebApp();
  const isAvailable = webApp !== null;

  const openLink = useCallback(
    (url: string, options?: { try_instant_view?: boolean }) => {
      webApp?.openLink(url, options);
    },
    [webApp],
  );

  const openTelegramLink = useCallback(
    (url: string) => {
      webApp?.openTelegramLink(url);
    },
    [webApp],
  );

  const switchInlineQuery = useCallback(
    (query: string, chatTypes?: ChatType[]) => {
      webApp?.switchInlineQuery(query, chatTypes);
    },
    [webApp],
  );

  return {
    openLink,
    openTelegramLink,
    switchInlineQuery,
    isAvailable,
  };
}
