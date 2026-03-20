import { useCallback } from 'react';
import type { ChatType } from '../types';
import { getWebApp } from '../core';

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
