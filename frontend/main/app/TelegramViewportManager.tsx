"use client";

import { useEffect } from "react";

/**
 * Telegram WebApp runtime manager.
 *
 * Mas'uliyat sohalari (avval `TelegramInit.jsx`'ga taqsimlangan, keyin
 * birlashtirilgan):
 *  • `ready()` — Telegram'ga app yuklanganini bildirish
 *  • `expand()` — kompakt ko'rinishdan tashqariga chiqarish (retry bilan)
 *  • `requestFullscreen()` — mobil platformalarda v7.0+ to'liq ekran rejimi
 *  • `disableVerticalSwipes()` — mobil swipe-to-close'ni o'chirish
 *  • Theme sinxronizatsiyasi (`setBackgroundColor`, `setHeaderColor`)
 *  • CSS o'zgaruvchilarni boshqarish:
 *      --tg-viewport-height / --tg-viewport-stable-height
 *      --tg-is-expanded / --tg-is-mobile
 *      --tg-safe-area-* / --tg-content-safe-area-*
 *  • `viewportChanged`, `safeAreaChanged`, `contentSafeAreaChanged`,
 *    `themeChanged` event'lariga obuna
 *
 * Brauzer fallback (Telegram SDK yo'q) — viewport va safe-area uchun stabil
 * fallback qiymatlar.
 */

function setCssVarPx(name: string, value: number) {
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

function compareSemver(a: string, b: string): number {
  const pa = String(a).split(".").map(Number);
  const pb = String(b).split(".").map(Number);
  const len = Math.max(pa.length, pb.length);
  for (let i = 0; i < len; i++) {
    const ai = pa[i] ?? 0;
    const bi = pb[i] ?? 0;
    if (ai !== bi) return ai - bi;
  }
  return 0;
}

function isVersionAtLeast(tg: any, target: string): boolean {
  if (typeof tg?.version !== "string") return false;
  return compareSemver(tg.version, target) >= 0;
}

function isMobileTelegram(tg: any): boolean {
  return tg?.platform === "ios" || tg?.platform === "android";
}

function applyThemeColors(tg: any) {
  if (typeof document === "undefined" || !isVersionAtLeast(tg, "6.1")) return;

  const appBg =
    getComputedStyle(document.documentElement)
      .getPropertyValue("--app-background")
      .trim() || "#ffffff";

  try {
    tg.setBackgroundColor?.(appBg);
    tg.setHeaderColor?.(appBg);
  } catch {
    // ignore
  }
}

function requestFullscreenBestEffort(tg: any) {
  if (!isVersionAtLeast(tg, "7.0")) return;
  const fn = tg.requestFullscreen ?? tg.requestFullScreen;
  try {
    fn?.call(tg);
  } catch {
    // ignore
  }
}

export default function TelegramViewportManager(): null {
  useEffect(() => {
    let isCancelled = false;
    let fullscreenDone = false;

    const attach = (tg: any) => {
      if (isCancelled) return undefined;

      const isMobile = isMobileTelegram(tg);
      setCssVar("--tg-is-mobile", isMobile ? "1" : "0");

      const syncViewport = () => {
        const vh = tg?.viewportHeight ?? window.innerHeight ?? 0;
        const stable = tg?.viewportStableHeight ?? vh;

        setCssVarPx("--tg-viewport-height", vh);
        setCssVarPx("--tg-viewport-stable-height", stable);
        setCssVar("--tg-is-expanded", tg?.isExpanded ? "1" : "0");
      };

      const syncSafeArea = () => {
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

      const onViewport = () => requestAnimationFrame(syncViewport);
      const onSafeArea = () => requestAnimationFrame(syncSafeArea);
      const onTheme = () => applyThemeColors(tg);

      try {
        tg.ready?.();
      } catch {
        // ignore
      }

      // Initial CSS state
      syncViewport();
      syncSafeArea();
      applyThemeColors(tg);

      // Expand from compact mode (works on all platforms)
      try {
        tg.expand?.();
      } catch {
        // ignore
      }
      // Some Telegram clients need a second tick before expand takes effect
      const expandRetry = window.setTimeout(() => {
        if (isCancelled) return;
        try {
          tg.expand?.();
        } catch {
          // ignore
        }
      }, 50);

      // Mobile-only: full screen + swipe lock
      if (isMobile) {
        if (!fullscreenDone) {
          requestFullscreenBestEffort(tg);
          fullscreenDone = true;
        }
        const fsRetry = window.setTimeout(() => {
          if (isCancelled || fullscreenDone) return;
          requestFullscreenBestEffort(tg);
          fullscreenDone = true;
        }, 50);

        try {
          tg.disableVerticalSwipes?.();
        } catch {
          // ignore
        }

        // Listeners
        try {
          tg.onEvent?.("viewportChanged", onViewport);
        } catch {
          // ignore
        }
        try {
          tg.onEvent?.("safeAreaChanged", onSafeArea);
        } catch {
          // ignore
        }
        try {
          tg.onEvent?.("contentSafeAreaChanged", onSafeArea);
        } catch {
          // ignore
        }
        try {
          tg.onEvent?.("themeChanged", onTheme);
        } catch {
          // ignore
        }
        window.addEventListener("resize", onViewport, { passive: true });

        return () => {
          window.clearTimeout(fsRetry);
          window.clearTimeout(expandRetry);
          try {
            tg.offEvent?.("viewportChanged", onViewport);
          } catch {}
          try {
            tg.offEvent?.("safeAreaChanged", onSafeArea);
          } catch {}
          try {
            tg.offEvent?.("contentSafeAreaChanged", onSafeArea);
          } catch {}
          try {
            tg.offEvent?.("themeChanged", onTheme);
          } catch {}
          window.removeEventListener("resize", onViewport);
        };
      }

      // Desktop / web Telegram — viewport va theme listenerlari
      try {
        tg.onEvent?.("viewportChanged", onViewport);
      } catch {
        // ignore
      }
      try {
        tg.onEvent?.("safeAreaChanged", onSafeArea);
      } catch {
        // ignore
      }
      try {
        tg.onEvent?.("contentSafeAreaChanged", onSafeArea);
      } catch {
        // ignore
      }
      try {
        tg.onEvent?.("themeChanged", onTheme);
      } catch {
        // ignore
      }
      window.addEventListener("resize", onViewport, { passive: true });

      return () => {
        window.clearTimeout(expandRetry);
        try {
          tg.offEvent?.("viewportChanged", onViewport);
        } catch {}
        try {
          tg.offEvent?.("safeAreaChanged", onSafeArea);
        } catch {}
        try {
          tg.offEvent?.("contentSafeAreaChanged", onSafeArea);
        } catch {}
        try {
          tg.offEvent?.("themeChanged", onTheme);
        } catch {}
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
      if (Date.now() - startedAt < 2000) {
        requestAnimationFrame(tryInit);
      }
    };

    tryInit();

    // Brauzer fallback: SDK yo'q bo'lsa ham viewport o'zgaruvchilarni stabil
    // qiymatlarda saqlash. Bu Telegram tashqarisida ochilganda layout buzilmasligi uchun.
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
        if (typeof document !== "undefined") {
          document.documentElement.style.removeProperty("--tg-is-mobile");
        }
      };
    }

    return () => {
      isCancelled = true;
      cleanup?.();
      if (typeof document !== "undefined") {
        document.documentElement.style.removeProperty("--tg-is-mobile");
      }
    };
  }, []);

  return null;
}
