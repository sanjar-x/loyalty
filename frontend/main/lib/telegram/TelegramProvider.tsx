'use client';

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';

import type {
  WebApp,
  WebAppUser,
  WebAppInitData,
  ThemeParams,
  SafeAreaInset,
  ContentSafeAreaInset,
} from './types';

import { getWebApp } from './core';

import {
  isBrowserDebugAuthEnabled,
  getBrowserDebugUser,
  getBrowserDebugTelegramUser,
} from '@/lib/auth/debug';

// =============================================================================
// Context value
// =============================================================================

export interface TelegramContextValue {
  webApp: WebApp | null;
  user: WebAppUser | null;
  initData: string;
  initDataUnsafe: WebAppInitData | null;
  colorScheme: 'light' | 'dark';
  themeParams: ThemeParams;
  viewportHeight: number;
  viewportStableHeight: number;
  isExpanded: boolean;
  isActive: boolean;
  safeAreaInset: SafeAreaInset;
  contentSafeAreaInset: ContentSafeAreaInset;
  platform: string;
  version: string;
  isReady: boolean;
}

// =============================================================================
// Defaults
// =============================================================================

const DEFAULT_SAFE_AREA: SafeAreaInset = { top: 0, bottom: 0, left: 0, right: 0 };
const DEFAULT_CONTENT_SAFE_AREA: ContentSafeAreaInset = { top: 0, bottom: 0, left: 0, right: 0 };
const DEFAULT_THEME: ThemeParams = {};

const INIT_DATA_EVENT = 'lm:telegram:initdata';

// =============================================================================
// Context
// =============================================================================

const TelegramContext = createContext<TelegramContextValue | null>(null);

export function useTelegramContext(): TelegramContextValue {
  const ctx = useContext(TelegramContext);
  if (!ctx) {
    throw new Error(
      'useTelegramContext must be used within a <TelegramProvider>. ' +
        'Wrap your app (or the relevant subtree) with <TelegramProvider>.',
    );
  }
  return ctx;
}

// =============================================================================
// CSS custom property helpers
// =============================================================================

const THEME_KEY_TO_CSS: Record<string, string> = {
  bg_color: '--tg-theme-bg-color',
  text_color: '--tg-theme-text-color',
  hint_color: '--tg-theme-hint-color',
  link_color: '--tg-theme-link-color',
  button_color: '--tg-theme-button-color',
  button_text_color: '--tg-theme-button-text-color',
  secondary_bg_color: '--tg-theme-secondary-bg-color',
  header_bg_color: '--tg-theme-header-bg-color',
  bottom_bar_bg_color: '--tg-theme-bottom-bar-bg-color',
  accent_text_color: '--tg-theme-accent-text-color',
  section_bg_color: '--tg-theme-section-bg-color',
  section_header_text_color: '--tg-theme-section-header-text-color',
  section_separator_color: '--tg-theme-section-separator-color',
  subtitle_text_color: '--tg-theme-subtitle-text-color',
  destructive_text_color: '--tg-theme-destructive-text-color',
};

function setThemeCSSVars(params: ThemeParams): void {
  const style = document.documentElement.style;
  for (const [key, cssVar] of Object.entries(THEME_KEY_TO_CSS)) {
    const value = (params as Record<string, string | undefined>)[key];
    if (value) {
      style.setProperty(cssVar, value);
    } else {
      style.removeProperty(cssVar);
    }
  }
}

function setViewportCSSVars(height: number, stableHeight: number): void {
  const style = document.documentElement.style;
  style.setProperty('--tg-viewport-height', `${height}px`);
  style.setProperty('--tg-viewport-stable-height', `${stableHeight}px`);
}

function setSafeAreaCSSVars(inset: SafeAreaInset): void {
  const style = document.documentElement.style;
  style.setProperty('--tg-safe-area-top', `${inset.top}px`);
  style.setProperty('--tg-safe-area-bottom', `${inset.bottom}px`);
  style.setProperty('--tg-safe-area-left', `${inset.left}px`);
  style.setProperty('--tg-safe-area-right', `${inset.right}px`);
}

function setContentSafeAreaCSSVars(inset: ContentSafeAreaInset): void {
  const style = document.documentElement.style;
  style.setProperty('--tg-content-safe-area-top', `${inset.top}px`);
  style.setProperty('--tg-content-safe-area-bottom', `${inset.bottom}px`);
  style.setProperty('--tg-content-safe-area-left', `${inset.left}px`);
  style.setProperty('--tg-content-safe-area-right', `${inset.right}px`);
}

function setMetaCSSVars(isExpanded: boolean, isMobile: boolean): void {
  const style = document.documentElement.style;
  style.setProperty('--tg-is-expanded', isExpanded ? '1' : '0');
  style.setProperty('--tg-is-mobile', isMobile ? '1' : '0');
}

function clearAllCSSVars(): void {
  const style = document.documentElement.style;
  for (const cssVar of Object.values(THEME_KEY_TO_CSS)) {
    style.removeProperty(cssVar);
  }
  style.removeProperty('--tg-viewport-height');
  style.removeProperty('--tg-viewport-stable-height');
  style.removeProperty('--tg-safe-area-top');
  style.removeProperty('--tg-safe-area-bottom');
  style.removeProperty('--tg-safe-area-left');
  style.removeProperty('--tg-safe-area-right');
  style.removeProperty('--tg-content-safe-area-top');
  style.removeProperty('--tg-content-safe-area-bottom');
  style.removeProperty('--tg-content-safe-area-left');
  style.removeProperty('--tg-content-safe-area-right');
  style.removeProperty('--tg-is-expanded');
  style.removeProperty('--tg-is-mobile');
}

// =============================================================================
// Init-data publishing (ported from TelegramInit.tsx)
// =============================================================================

function publishInitData(
  rawInitData: string,
  unsafe: WebAppInitData | null,
  browserDebugUser?: ReturnType<typeof getBrowserDebugUser>,
): void {
  (window as any).__LM_TG_INIT_DATA__ = rawInitData;
  (window as any).__LM_TG_INIT_DATA_UNSAFE__ = unsafe ?? undefined;
  (window as any).__LM_BROWSER_DEBUG_AUTH__ = Boolean(browserDebugUser);
  (window as any).__LM_BROWSER_DEBUG_USER__ = browserDebugUser ?? null;

  try {
    window.dispatchEvent(
      new CustomEvent(INIT_DATA_EVENT, {
        detail: {
          initData: rawInitData,
          unsafe,
          user: unsafe?.user ?? null,
          browserDebugUser: browserDebugUser ?? null,
        },
      }),
    );
  } catch {
    // ignore
  }
}

// =============================================================================
// Provider
// =============================================================================

export interface TelegramProviderProps {
  children: ReactNode;
}

export function TelegramProvider({ children }: TelegramProviderProps) {
  const [isReady, setIsReady] = useState(false);
  const [colorScheme, setColorScheme] = useState<'light' | 'dark'>('light');
  const [themeParams, setThemeParams] = useState<ThemeParams>(DEFAULT_THEME);
  const [viewportHeight, setViewportHeight] = useState(
    typeof window !== 'undefined' ? window.innerHeight : 0,
  );
  const [viewportStableHeight, setViewportStableHeight] = useState(
    typeof window !== 'undefined' ? window.innerHeight : 0,
  );
  const [isExpanded, setIsExpanded] = useState(false);
  const [isActive, setIsActive] = useState(true);
  const [safeAreaInset, setSafeAreaInset] = useState<SafeAreaInset>(DEFAULT_SAFE_AREA);
  const [contentSafeAreaInset, setContentSafeAreaInset] =
    useState<ContentSafeAreaInset>(DEFAULT_CONTENT_SAFE_AREA);

  const waRef = useRef<WebApp | null>(null);

  useEffect(() => {
    const wa = getWebApp();
    waRef.current = wa;

    if (wa) {
      // --- Signal ready ---
      try {
        wa.ready();
      } catch {
        // ignore
      }

      // --- Publish init data ---
      publishInitData(
        typeof wa.initData === 'string' ? wa.initData : '',
        wa.initDataUnsafe || null,
      );

      // --- Read initial state ---
      const isMobile = wa.platform === 'ios' || wa.platform === 'android';

      setColorScheme(wa.colorScheme ?? 'light');
      setThemeParams(wa.themeParams ?? DEFAULT_THEME);
      setViewportHeight(wa.viewportHeight ?? window.innerHeight);
      setViewportStableHeight(wa.viewportStableHeight ?? window.innerHeight);
      setIsExpanded(wa.isExpanded ?? false);
      setIsActive(wa.isActive ?? true);
      setSafeAreaInset(wa.safeAreaInset ?? DEFAULT_SAFE_AREA);
      setContentSafeAreaInset(wa.contentSafeAreaInset ?? DEFAULT_CONTENT_SAFE_AREA);

      // --- Set CSS vars ---
      setThemeCSSVars(wa.themeParams ?? DEFAULT_THEME);
      setViewportCSSVars(
        wa.viewportHeight ?? window.innerHeight,
        wa.viewportStableHeight ?? window.innerHeight,
      );
      setSafeAreaCSSVars(wa.safeAreaInset ?? DEFAULT_SAFE_AREA);
      setContentSafeAreaCSSVars(wa.contentSafeAreaInset ?? DEFAULT_CONTENT_SAFE_AREA);
      setMetaCSSVars(wa.isExpanded ?? false, isMobile);

      // --- Mobile-specific initialization ---
      if (isMobile) {
        try {
          wa.expand();
        } catch {
          // ignore
        }
        try {
          (wa as any).requestFullscreen?.();
        } catch {
          // ignore
        }
        try {
          (wa as any).disableVerticalSwipes?.();
        } catch {
          // ignore
        }
      }

      // --- Event handlers ---
      const onThemeChanged = () => {
        setColorScheme(wa.colorScheme ?? 'light');
        setThemeParams(wa.themeParams ?? DEFAULT_THEME);
        setThemeCSSVars(wa.themeParams ?? DEFAULT_THEME);
      };

      const onViewportChanged = () => {
        const h = wa.viewportHeight ?? window.innerHeight;
        const sh = wa.viewportStableHeight ?? window.innerHeight;
        setViewportHeight(h);
        setViewportStableHeight(sh);
        setIsExpanded(wa.isExpanded ?? false);
        setViewportCSSVars(h, sh);
        setMetaCSSVars(
          wa.isExpanded ?? false,
          wa.platform === 'ios' || wa.platform === 'android',
        );
      };

      const onSafeAreaChanged = () => {
        const inset = wa.safeAreaInset ?? DEFAULT_SAFE_AREA;
        setSafeAreaInset(inset);
        setSafeAreaCSSVars(inset);
      };

      const onContentSafeAreaChanged = () => {
        const inset = wa.contentSafeAreaInset ?? DEFAULT_CONTENT_SAFE_AREA;
        setContentSafeAreaInset(inset);
        setContentSafeAreaCSSVars(inset);
      };

      const onActivated = () => setIsActive(true);
      const onDeactivated = () => setIsActive(false);

      wa.onEvent('themeChanged', onThemeChanged);
      wa.onEvent('viewportChanged', onViewportChanged);
      wa.onEvent('safeAreaChanged', onSafeAreaChanged);
      wa.onEvent('contentSafeAreaChanged', onContentSafeAreaChanged);
      wa.onEvent('activated', onActivated);
      wa.onEvent('deactivated', onDeactivated);

      setIsReady(true);

      return () => {
        wa.offEvent('themeChanged', onThemeChanged);
        wa.offEvent('viewportChanged', onViewportChanged);
        wa.offEvent('safeAreaChanged', onSafeAreaChanged);
        wa.offEvent('contentSafeAreaChanged', onContentSafeAreaChanged);
        wa.offEvent('activated', onActivated);
        wa.offEvent('deactivated', onDeactivated);
        clearAllCSSVars();
      };
    }

    // --- Fallback: not in Telegram ---

    // Debug auth support
    if (isBrowserDebugAuthEnabled()) {
      const debugTgUser = getBrowserDebugTelegramUser();
      publishInitData(
        '',
        debugTgUser ? ({ user: debugTgUser } as unknown as WebAppInitData) : null,
        getBrowserDebugUser(),
      );
    }

    // Viewport fallback via window resize
    const onResize = () => {
      setViewportHeight(window.innerHeight);
      setViewportStableHeight(window.innerHeight);
      setViewportCSSVars(window.innerHeight, window.innerHeight);
    };

    window.addEventListener('resize', onResize);
    setViewportCSSVars(window.innerHeight, window.innerHeight);
    setMetaCSSVars(false, false);
    setIsReady(true);

    return () => {
      window.removeEventListener('resize', onResize);
      clearAllCSSVars();
      (window as any).__LM_BROWSER_DEBUG_AUTH__ = false;
      (window as any).__LM_BROWSER_DEBUG_USER__ = null;
    };
  }, []);

  const value = useMemo<TelegramContextValue>(
    () => ({
      webApp: waRef.current,
      user: waRef.current?.initDataUnsafe?.user ?? null,
      initData: waRef.current?.initData ?? '',
      initDataUnsafe: waRef.current?.initDataUnsafe ?? null,
      colorScheme,
      themeParams,
      viewportHeight,
      viewportStableHeight,
      isExpanded,
      isActive,
      safeAreaInset,
      contentSafeAreaInset,
      platform: waRef.current?.platform ?? '',
      version: waRef.current?.version ?? '',
      isReady,
    }),
    [
      colorScheme,
      themeParams,
      viewportHeight,
      viewportStableHeight,
      isExpanded,
      isActive,
      safeAreaInset,
      contentSafeAreaInset,
      isReady,
    ],
  );

  return <TelegramContext.Provider value={value}>{children}</TelegramContext.Provider>;
}

export default TelegramProvider;
