"use client";

import { useEffect, useRef } from "react";

import {
  useGetMeQuery,
  useInitTelegramSessionMutation,
  api,
} from "@/lib/store/api";
import {
  getBrowserDebugUser,
  isBrowserDebugAuthEnabled,
} from "@/lib/telegram/browserDebugAuth";
import { useAppDispatch } from "@/lib/store/hooks";

const INIT_DATA_EVENT = "lm:telegram:initdata";

function readInitDataFromWindow() {
  if (typeof window === "undefined") return "";

  const tgInit = window.Telegram?.WebApp?.initData;
  if (typeof tgInit === "string" && tgInit.trim()) return tgInit.trim();

  const fallback = window.__LM_TG_INIT_DATA__;
  if (typeof fallback === "string" && fallback.trim()) return fallback.trim();

  return "";
}

function readBrowserDebugUserFromWindow() {
  if (typeof window === "undefined") return null;

  const user = window.__LM_BROWSER_DEBUG_USER__;
  if (user && typeof user === "object") return user;

  if (isBrowserDebugAuthEnabled()) {
    return getBrowserDebugUser();
  }

  return null;
}

export default function TelegramAuthBootstrap() {
  const didInitRef = useRef(false);
  const isStartingRef = useRef(false);
  const attemptsRef = useRef(0);
  const dispatch = useAppDispatch();

  const { isSuccess, error, data: meData, refetch } = useGetMeQuery();
  const [initSession] = useInitTelegramSessionMutation();

  useEffect(() => {
    if (didInitRef.current) return;

    const debugUser = readBrowserDebugUserFromWindow();
    const shouldUseBrowserDebugAuth = Boolean(debugUser);

    const maybeNotAuthenticated =
      meData &&
      typeof meData === "object" &&
      typeof meData.detail === "string" &&
      meData.detail.toLowerCase().includes("not authenticated");

    // If we already have a valid session, do nothing.
    // Some backends incorrectly return 200 with {detail:"Not authenticated"}.
    if (isSuccess && !maybeNotAuthenticated) {
      didInitRef.current = true;
      return;
    }

    // Attempt init when backend says unauthorized.
    // Some backends return 403 for missing/invalid auth.
    // Some backends return 200 with a "Not authenticated" payload.
    const status = error?.status;
    if (
      !shouldUseBrowserDebugAuth &&
      !maybeNotAuthenticated &&
      status !== 401 &&
      status !== 403
    ) {
      return;
    }

    let isCancelled = false;

    const tryStart = async () => {
      if (isCancelled) return;
      if (didInitRef.current || isStartingRef.current) return;
      if (attemptsRef.current >= 5) return;

      const initData = readInitDataFromWindow();
      const nextDebugUser = readBrowserDebugUserFromWindow();
      if (!initData && !nextDebugUser) return;

      isStartingRef.current = true;
      attemptsRef.current += 1;

      try {
        await initSession(
          initData ? { initData } : { debugUser: nextDebugUser },
        ).unwrap();

        dispatch(api.util.invalidateTags(["User", "Referrals", "Products"]));
        await refetch();
        didInitRef.current = true;
      } catch {
        // ignore
      } finally {
        isStartingRef.current = false;
      }
    };

    // 1) Immediate attempt (initData often is already present)
    tryStart();

    // 2) Listen for TelegramInit event
    const onInitData = () => {
      tryStart();
    };
    window.addEventListener(INIT_DATA_EVENT, onInitData);

    // 3) Short polling fallback (WebView timing)
    const poll = window.setInterval(tryStart, 250);
    const stop = window.setTimeout(() => {
      window.clearInterval(poll);
    }, 2500);

    return () => {
      isCancelled = true;
      window.removeEventListener(INIT_DATA_EVENT, onInitData);
      window.clearInterval(poll);
      window.clearTimeout(stop);
    };
  }, [isSuccess, error, meData, refetch, dispatch, initSession]);

  return null;
}
