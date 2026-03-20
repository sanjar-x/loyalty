import type { TelegramUser, TelegramWebApp, DebugUser } from "./telegram";

declare global {
  interface Window {
    __LM_TG_INIT_DATA__?: string;
    __LM_TG_INIT_DATA_UNSAFE__?: { user?: TelegramUser };
    __LM_BROWSER_DEBUG_AUTH__?: boolean;
    __LM_BROWSER_DEBUG_USER__?: DebugUser | null;
    Telegram?: { WebApp?: TelegramWebApp };
  }
}

export {};
