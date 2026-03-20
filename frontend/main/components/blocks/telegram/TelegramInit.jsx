"use client";

import { useEffect } from "react";

import {
  getBrowserDebugTelegramUser,
  getBrowserDebugUser,
  isBrowserDebugAuthEnabled,
} from "@/lib/auth/browserDebugAuth";

const INIT_DATA_EVENT = "lm:telegram:initdata";

/* ================= Utils ================= */

function compareSemver(a, b) {
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

function getTelegramWebApp() {
  if (typeof window === "undefined") return null;
  return window.Telegram?.WebApp ?? null;
}

function isMobileTelegram(tg) {
  return tg?.platform === "ios" || tg?.platform === "android";
}

/* ================= Theme ================= */

function applyThemeColors(tg) {
  if (typeof document === "undefined") return;

  const appBg =
    getComputedStyle(document.documentElement)
      .getPropertyValue("--app-background")
      .trim() || "#f6f5f3";

  if (
    typeof tg?.version === "string" &&
    compareSemver(tg.version, "6.1") >= 0
  ) {
    try {
      tg.setBackgroundColor(appBg);
      tg.setHeaderColor(appBg);
    } catch {}
  }
}

/* ================= Fullscreen ================= */

function requestFullscreenBestEffort(tg) {
  if (
    typeof tg?.version === "string" &&
    compareSemver(tg.version, "7.0") >= 0
  ) {
    const fn = tg.requestFullscreen ?? tg.requestFullScreen;
    try {
      fn?.call(tg);
    } catch {}
  }
}

/* ================= Component ================= */

export default function TelegramInit() {
  useEffect(() => {
    let cancelled = false;
    let fullscreenDone = false;
    let didPublishInitData = false;

    const publishInitData = ({
      rawInitData,
      unsafe,
      browserDebugUser = null,
    }) => {
      if (cancelled || didPublishInitData) return;

      window.__LM_TG_INIT_DATA__ = rawInitData;
      window.__LM_TG_INIT_DATA_UNSAFE__ = unsafe;
      window.__LM_BROWSER_DEBUG_AUTH__ = Boolean(browserDebugUser);
      window.__LM_BROWSER_DEBUG_USER__ = browserDebugUser;

      try {
        window.dispatchEvent(
          new CustomEvent(INIT_DATA_EVENT, {
            detail: {
              initData: rawInitData,
              unsafe,
              user: unsafe?.user ?? null,
              browserDebugUser,
            },
          }),
        );
      } catch {
        // ignore
      }

      didPublishInitData = true;
    };

    const init = (tg) => {
      if (cancelled || !tg) return;

      const isMobile = isMobileTelegram(tg);

      // CSS uchun global flag
      try {
        document.documentElement.style.setProperty(
          "--tg-is-mobile",
          isMobile ? "1" : "0",
        );
      } catch {}

      try {
        tg.ready();
      } catch {}

      // initData publish ASAP after ready()
      publishInitData({
        rawInitData: typeof tg?.initData === "string" ? tg.initData : "",
        unsafe: tg?.initDataUnsafe || null,
      });

      // Faqat mobile’da
      if (isMobile) {
        try {
          tg.expand();
        } catch {}

        if (!fullscreenDone) {
          requestFullscreenBestEffort(tg);
          fullscreenDone = true;
        }

        try {
          tg.disableVerticalSwipes?.();
        } catch {}
      }

      applyThemeColors(tg);
    };

    const start = Date.now();
    const tick = () => {
      if (cancelled) return;
      const tg = getTelegramWebApp();
      if (tg) init(tg);
      else if (isBrowserDebugAuthEnabled()) {
        publishInitData({
          rawInitData: "",
          unsafe: { user: getBrowserDebugTelegramUser() },
          browserDebugUser: getBrowserDebugUser(),
        });
      } else if (Date.now() - start < 2000) requestAnimationFrame(tick);
    };

    tick();

    return () => {
      cancelled = true;
      try {
        document.documentElement.style.removeProperty("--tg-is-mobile");
      } catch {}
      window.__LM_BROWSER_DEBUG_AUTH__ = false;
      window.__LM_BROWSER_DEBUG_USER__ = null;
    };
  }, []);

  return null;
}
