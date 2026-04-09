import type { TelegramContextValue } from './provider.types';

import type {
  ContentSafeAreaInset,
  SafeAreaInset,
  ThemeParams,
  WebApp,
  WebAppInitData,
  WebAppUser,
} from './types';

export const DEFAULT_SAFE_AREA: SafeAreaInset = { top: 0, bottom: 0, left: 0, right: 0 };
export const DEFAULT_CONTENT_SAFE_AREA: ContentSafeAreaInset = {
  top: 0,
  bottom: 0,
  left: 0,
  right: 0,
};
export const DEFAULT_THEME: ThemeParams = {};

export function getWindowViewportHeight(): number {
  return typeof window !== 'undefined' ? window.innerHeight : 0;
}

export function isTelegramMobilePlatform(platform: string): boolean {
  return platform === 'ios' || platform === 'android';
}

export function createInitialTelegramState(): TelegramContextValue {
  const viewportHeight = getWindowViewportHeight();

  return {
    webApp: null,
    user: null,
    initData: '',
    initDataUnsafe: null,
    colorScheme: 'light',
    themeParams: DEFAULT_THEME,
    viewportHeight,
    viewportStableHeight: viewportHeight,
    isExpanded: false,
    isActive: true,
    safeAreaInset: DEFAULT_SAFE_AREA,
    contentSafeAreaInset: DEFAULT_CONTENT_SAFE_AREA,
    platform: '',
    version: '',
    isReady: false,
  };
}

export function createFallbackTelegramState(debugUser: WebAppUser | null): TelegramContextValue {
  const viewportHeight = getWindowViewportHeight();
  const initDataUnsafe = debugUser ? ({ user: debugUser } as WebAppInitData) : null;

  return {
    webApp: null,
    user: debugUser,
    initData: '',
    initDataUnsafe,
    colorScheme: 'light',
    themeParams: DEFAULT_THEME,
    viewportHeight,
    viewportStableHeight: viewportHeight,
    isExpanded: false,
    isActive: true,
    safeAreaInset: DEFAULT_SAFE_AREA,
    contentSafeAreaInset: DEFAULT_CONTENT_SAFE_AREA,
    platform: '',
    version: '',
    isReady: true,
  };
}

export function createTelegramStateFromWebApp(webApp: WebApp): TelegramContextValue {
  const viewportHeight = getWindowViewportHeight();

  return {
    webApp,
    user: webApp.initDataUnsafe?.user ?? null,
    initData: typeof webApp.initData === 'string' ? webApp.initData : '',
    initDataUnsafe: webApp.initDataUnsafe ?? null,
    colorScheme: webApp.colorScheme ?? 'light',
    themeParams: webApp.themeParams ?? DEFAULT_THEME,
    viewportHeight: webApp.viewportHeight ?? viewportHeight,
    viewportStableHeight: webApp.viewportStableHeight ?? viewportHeight,
    isExpanded: webApp.isExpanded ?? false,
    isActive: webApp.isActive ?? true,
    safeAreaInset: webApp.safeAreaInset ?? DEFAULT_SAFE_AREA,
    contentSafeAreaInset: webApp.contentSafeAreaInset ?? DEFAULT_CONTENT_SAFE_AREA,
    platform: webApp.platform ?? '',
    version: webApp.version ?? '',
    isReady: true,
  };
}
