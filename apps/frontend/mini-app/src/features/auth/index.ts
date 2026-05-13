export type {
  AuthProvider,
  AuthStatus,
  Identity,
  Session,
  TelegramAuthResponse,
  TokenPair,
} from './types';

export { useAuthStore } from './store';

export {
  getBrowserDebugTelegramUser,
  getBrowserDebugUser,
  isBrowserDebugAuthEnabled,
  normalizeBrowserDebugUser,
} from './lib/debug';
export type { BrowserDebugUser } from './lib/debug';

export { ACCESS_COOKIE, REFRESH_COOKIE, logout } from './lib/cookies';

export { TelegramAuthBootstrap } from './components/telegram-auth-bootstrap';
