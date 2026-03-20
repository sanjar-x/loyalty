import type { WebApp, WebAppUser } from "@/lib/telegram/types";
import type { BrowserDebugUser } from "@/lib/auth/browserDebugAuth";

declare global {
  interface Window {
    __LM_TG_INIT_DATA__?: string;
    __LM_TG_INIT_DATA_UNSAFE__?: { user?: WebAppUser };
    __LM_BROWSER_DEBUG_AUTH__?: boolean;
    __LM_BROWSER_DEBUG_USER__?: BrowserDebugUser | null;
    Telegram?: { WebApp?: WebApp };
  }
}

export {};
