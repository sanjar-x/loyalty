'use client';

import { useEffect } from 'react';

import { usePathname, useRouter } from 'next/navigation';

import { useTelegramContext } from '../provider';

const ROOT_TAB_ROUTES = new Set(['/', '/poizon', '/catalog', '/favorites', '/cart', '/profile']);

/**
 * Keeps the native Telegram BackButton in sync with the current app route.
 */
export function TelegramBackButtonController() {
  const pathname = usePathname();
  const router = useRouter();
  const { isReady, webApp } = useTelegramContext();

  useEffect(() => {
    if (!isReady || !webApp?.BackButton) return;

    const isRootTabRoute = ROOT_TAB_ROUTES.has(pathname);
    const backButton = webApp.BackButton;

    const syncVisibility = () => {
      const homeBackHandler = pathname === '/' ? window.__LM_HOME_BACK__ : null;

      if (isRootTabRoute && !homeBackHandler) {
        backButton.hide();
        return;
      }

      backButton.show();
    };

    syncVisibility();

    const handleBackClick = () => {
      const homeBackHandler = window.__LM_HOME_BACK__;
      if (pathname === '/' && typeof homeBackHandler === 'function') {
        homeBackHandler();
        return;
      }

      router.back();
    };

    backButton.onClick(handleBackClick);

    return () => {
      backButton.offClick(handleBackClick);
      backButton.hide();
    };
  }, [isReady, pathname, router, webApp]);

  return null;
}
