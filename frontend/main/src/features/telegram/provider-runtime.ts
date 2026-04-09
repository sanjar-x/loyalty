import { useEffect, useState } from 'react';

import {
  getBrowserDebugTelegramUser,
  isBrowserDebugAuthEnabled,
} from '@/features/auth';

import { getWebApp } from './core';
import {
  applyThemeColors,
  clearAllCSSVars,
  setContentSafeAreaCSSVars,
  setMetaCSSVars,
  setSafeAreaCSSVars,
  setThemeCSSVars,
  setViewportCSSVars,
} from './provider-dom';
import {
  createFallbackTelegramState,
  createInitialTelegramState,
  createTelegramStateFromWebApp,
  DEFAULT_CONTENT_SAFE_AREA,
  DEFAULT_SAFE_AREA,
  DEFAULT_THEME,
  getWindowViewportHeight,
  isTelegramMobilePlatform,
} from './provider-state';
import type { TelegramContextValue } from './provider.types';
import type { ContentSafeAreaInset, SafeAreaInset, WebApp, WebAppUser } from './types';

const SDK_WAIT_TIMEOUT_MS = 2_000;
const SDK_POLL_INTERVAL_MS = 50;

export function useTelegramSdkRuntime(): TelegramContextValue {
  const [state, setState] = useState<TelegramContextValue>(() => createInitialTelegramState());

  useEffect(() => {
    let isMounted = true;
    let waitTimer: number | undefined;
    let cleanup: (() => void) | undefined;

    const initializeFallback = () => {
      if (!isMounted) return;

      const debugUser = isBrowserDebugAuthEnabled()
        ? (getBrowserDebugTelegramUser() as WebAppUser | null)
        : null;

      setState(createFallbackTelegramState(debugUser));

      const syncViewport = () => {
        const height = getWindowViewportHeight();
        setState((current) => ({
          ...current,
          viewportHeight: height,
          viewportStableHeight: height,
        }));
        setViewportCSSVars(height, height);
      };

      window.addEventListener('resize', syncViewport);
      syncViewport();
      setMetaCSSVars(false, false);

      cleanup = () => {
        window.removeEventListener('resize', syncViewport);
        clearAllCSSVars();
      };
    };

    const initializeWebApp = (currentWebApp: WebApp) => {
      if (!isMounted) return;

      try {
        currentWebApp.ready();
      } catch {
        // Ignore runtime errors from older Telegram versions.
      }

      const nextState = createTelegramStateFromWebApp(currentWebApp);
      const isMobile = isTelegramMobilePlatform(nextState.platform);

      setState(nextState);

      setThemeCSSVars(nextState.themeParams);
      setViewportCSSVars(nextState.viewportHeight, nextState.viewportStableHeight);
      setSafeAreaCSSVars(nextState.safeAreaInset);
      setContentSafeAreaCSSVars(nextState.contentSafeAreaInset);
      setMetaCSSVars(nextState.isExpanded, isMobile);
      applyThemeColors(currentWebApp);

      if (isMobile) {
        try {
          currentWebApp.expand();
        } catch {
          // Ignore runtime errors from older Telegram versions.
        }

        try {
          currentWebApp.requestFullscreen();
        } catch {
          // Ignore runtime errors from older Telegram versions.
        }

        try {
          currentWebApp.disableVerticalSwipes();
        } catch {
          // Ignore runtime errors from older Telegram versions.
        }
      }

      const onThemeChanged = () => {
        const themeParams = currentWebApp.themeParams ?? DEFAULT_THEME;
        setState((current) => ({
          ...current,
          colorScheme: currentWebApp.colorScheme ?? 'light',
          themeParams,
        }));
        setThemeCSSVars(themeParams);
        applyThemeColors(currentWebApp);
      };

      const onViewportChanged = () => {
        const viewportHeight = currentWebApp.viewportHeight ?? getWindowViewportHeight();
        const viewportStableHeight =
          currentWebApp.viewportStableHeight ?? getWindowViewportHeight();
        const isExpanded = currentWebApp.isExpanded ?? false;
        const isMobile = isTelegramMobilePlatform(currentWebApp.platform ?? '');

        setState((current) => ({
          ...current,
          viewportHeight,
          viewportStableHeight,
          isExpanded,
        }));
        setViewportCSSVars(viewportHeight, viewportStableHeight);
        setMetaCSSVars(isExpanded, isMobile);
      };

      const onSafeAreaChanged = () => {
        const safeAreaInset: SafeAreaInset = currentWebApp.safeAreaInset ?? DEFAULT_SAFE_AREA;
        setState((current) => ({
          ...current,
          safeAreaInset,
        }));
        setSafeAreaCSSVars(safeAreaInset);
      };

      const onContentSafeAreaChanged = () => {
        const contentSafeAreaInset: ContentSafeAreaInset =
          currentWebApp.contentSafeAreaInset ?? DEFAULT_CONTENT_SAFE_AREA;
        setState((current) => ({
          ...current,
          contentSafeAreaInset,
        }));
        setContentSafeAreaCSSVars(contentSafeAreaInset);
      };

      const onActivated = () => {
        setState((current) => ({
          ...current,
          isActive: true,
        }));
      };

      const onDeactivated = () => {
        setState((current) => ({
          ...current,
          isActive: false,
        }));
      };

      currentWebApp.onEvent('themeChanged', onThemeChanged);
      currentWebApp.onEvent('viewportChanged', onViewportChanged);
      currentWebApp.onEvent('safeAreaChanged', onSafeAreaChanged);
      currentWebApp.onEvent('contentSafeAreaChanged', onContentSafeAreaChanged);
      currentWebApp.onEvent('activated', onActivated);
      currentWebApp.onEvent('deactivated', onDeactivated);

      cleanup = () => {
        currentWebApp.offEvent('themeChanged', onThemeChanged);
        currentWebApp.offEvent('viewportChanged', onViewportChanged);
        currentWebApp.offEvent('safeAreaChanged', onSafeAreaChanged);
        currentWebApp.offEvent('contentSafeAreaChanged', onContentSafeAreaChanged);
        currentWebApp.offEvent('activated', onActivated);
        currentWebApp.offEvent('deactivated', onDeactivated);
        clearAllCSSVars();
      };
    };

    const startedAt = Date.now();

    const waitForWebApp = () => {
      if (!isMounted) return;

      const currentWebApp = getWebApp();
      if (currentWebApp) {
        initializeWebApp(currentWebApp);
        return;
      }

      if (Date.now() - startedAt < SDK_WAIT_TIMEOUT_MS) {
        waitTimer = window.setTimeout(waitForWebApp, SDK_POLL_INTERVAL_MS);
        return;
      }

      initializeFallback();
    };

    waitForWebApp();

    return () => {
      isMounted = false;

      if (waitTimer !== undefined) {
        window.clearTimeout(waitTimer);
      }

      cleanup?.();
    };
  }, []);

  return state;
}
