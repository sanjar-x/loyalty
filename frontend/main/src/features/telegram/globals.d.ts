import type { WebApp } from './types';

declare global {
  interface Window {
    __LM_HOME_BACK__?: (() => boolean) | null;
    // Telegram injects the SDK lazily, so both the namespace and WebApp can be absent.
    Telegram?: { WebApp?: WebApp };
  }
}

export {};
