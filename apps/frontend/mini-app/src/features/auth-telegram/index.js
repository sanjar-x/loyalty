// Public API — auth feature
export { AuthStatus } from './model/types';
export { useAuthStore } from './model/store';
export { logout } from './lib/cookies';
export { isBrowserDebugAuthEnabled } from './lib/debug';
export { default as AuthGate } from './ui/AuthGate';
export { default as TelegramAuthBootstrap } from './ui/TelegramAuthBootstrap';
