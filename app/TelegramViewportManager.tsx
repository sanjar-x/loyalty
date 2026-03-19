"use client";

import { useEffect } from "react";

function setCssVarPx(name: string, value: number) {
  // `window.Telegram` is undefined in normal browsers, and `document` is not
  // available during SSR. This guard keeps the app safe everywhere.
  if (typeof document === "undefined") return;

  const safe = Number.isFinite(value) ? Math.max(0, value) : 0;
  document.documentElement.style.setProperty(name, `${safe}px`);
}

function setCssVar(name: string, value: string) {
  if (typeof document === "undefined") return;
  document.documentElement.style.setProperty(name, value);
}

function getTelegramWebApp(): any | null {
  if (typeof window === "undefined") return null;
  return (window as any).Telegram?.WebApp ?? null;
}

export default function TelegramViewportManager(): null {
  useEffect(() => {
    let isCancelled = false;

    const attach = (tg: any) => {
      if (isCancelled) return;

      const sync = () => {
        const vh = tg?.viewportHeight ?? window.innerHeight ?? 0;
        const stable = tg?.viewportStableHeight ?? vh;

        setCssVarPx("--tg-viewport-height", vh);
        setCssVarPx("--tg-viewport-stable-height", stable);
        setCssVar("--tg-is-expanded", tg?.isExpanded ? "1" : "0");

        const safe = tg?.safeAreaInset;
        if (safe) {
          setCssVarPx("--tg-safe-area-top", safe.top);
          setCssVarPx("--tg-safe-area-bottom", safe.bottom);
          setCssVarPx("--tg-safe-area-left", safe.left);
          setCssVarPx("--tg-safe-area-right", safe.right);
        }

        const contentSafe = tg?.contentSafeAreaInset;
        if (contentSafe) {
          setCssVarPx("--tg-content-safe-area-top", contentSafe.top);
          setCssVarPx("--tg-content-safe-area-bottom", contentSafe.bottom);
          setCssVarPx("--tg-content-safe-area-left", contentSafe.left);
          setCssVarPx("--tg-content-safe-area-right", contentSafe.right);
        }
      };

      const onViewport = () => {
        requestAnimationFrame(sync);
      };

      sync();

      tg?.onEvent?.("viewportChanged", onViewport);
      window.addEventListener("resize", onViewport, { passive: true });

      return () => {
        tg?.offEvent?.("viewportChanged", onViewport);
        window.removeEventListener("resize", onViewport);
      };
    };

    let cleanup: undefined | (() => void);
    const startedAt = Date.now();

    const tryInit = () => {
      if (isCancelled) return;

      const tg = getTelegramWebApp();
      if (tg) {
        cleanup = attach(tg);
        return;
      }

      // Wait a bit for Telegram WebApp SDK to initialize.
      if (Date.now() - startedAt < 2000) {
        requestAnimationFrame(tryInit);
      }
    };

    tryInit();

    // Browser fallback: still set variables to a stable px height.
    if (!getTelegramWebApp()) {
      const syncBrowser = () => {
        const vh = window.innerHeight ?? 0;
        setCssVarPx("--tg-viewport-height", vh);
        setCssVarPx("--tg-viewport-stable-height", vh);
      };

      syncBrowser();
      window.addEventListener("resize", syncBrowser, { passive: true });

      return () => {
        isCancelled = true;
        window.removeEventListener("resize", syncBrowser);
        cleanup?.();
      };
    }

    return () => {
      isCancelled = true;
      cleanup?.();
    };
  }, []);

  return null;
}
