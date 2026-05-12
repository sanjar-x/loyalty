import type {
  ContentSafeAreaInset,
  SafeAreaInset,
  ThemeParams,
  WebApp,
  WebAppInitData,
  WebAppUser,
} from './types';

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
