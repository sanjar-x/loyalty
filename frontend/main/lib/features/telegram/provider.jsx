"use client";

import { createContext, useContext, useEffect, useMemo, useState, useRef } from "react";

const TelegramContext = createContext(null);

/**
 * Hook — window.Telegram.WebApp paydo bo'lishini 2s ichida poll qiladi (50ms).
 */
function useTelegramSdkRuntime() {
  const [state, setState] = useState({
    webApp: null,
    initData: "",
    user: null,
    platform: "unknown",
    version: "",
    isReady: false,
  });

  const ranRef = useRef(false);

  useEffect(() => {
    if (ranRef.current) return;
    ranRef.current = true;

    const start = Date.now();
    const maxWait = 2000;
    const interval = 50;

    const poll = setInterval(() => {
      const tg =
        typeof window !== "undefined" ? window.Telegram?.WebApp : null;

      if (tg) {
        clearInterval(poll);
        try {
          tg.ready();
        } catch {
          // ignore
        }

        setState({
          webApp: tg,
          initData: typeof tg.initData === "string" ? tg.initData : "",
          user: tg.initDataUnsafe?.user ?? null,
          platform: tg.platform || "unknown",
          version: tg.version || "",
          isReady: true,
        });
        return;
      }

      if (Date.now() - start >= maxWait) {
        clearInterval(poll);
        // Telegram SDK topilmadi — fallback state
        setState((s) => ({ ...s, isReady: true }));
      }
    }, interval);

    return () => clearInterval(poll);
  }, []);

  return state;
}

/**
 * TelegramSdkProvider — React context orqali Telegram WebApp ni o'raydi.
 */
export function TelegramSdkProvider({ children }) {
  const sdk = useTelegramSdkRuntime();

  const value = useMemo(
    () => ({
      webApp: sdk.webApp,
      initData: sdk.initData,
      user: sdk.user,
      platform: sdk.platform,
      version: sdk.version,
      isReady: sdk.isReady,
    }),
    [sdk.webApp, sdk.initData, sdk.user, sdk.platform, sdk.version, sdk.isReady],
  );

  return (
    <TelegramContext.Provider value={value}>{children}</TelegramContext.Provider>
  );
}

/**
 * useTelegram — context dan Telegram SDK ma'lumotlarini olish.
 */
export function useTelegram() {
  const ctx = useContext(TelegramContext);
  if (!ctx) {
    throw new Error("useTelegram must be used within <TelegramSdkProvider>");
  }
  return ctx;
}
