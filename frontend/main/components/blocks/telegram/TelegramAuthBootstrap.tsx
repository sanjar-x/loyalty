"use client";

import { useEffect, useRef } from "react";

import {
  isBrowserDebugAuthEnabled,
  getBrowserDebugUser,
} from "@/lib/auth/browserDebugAuth";
import { useAppDispatch, useAppSelector } from "@/lib/store/hooks";
import {
  initStart,
  initSuccess,
  initFailure,
  selectAuthStatus,
} from "@/lib/store/authSlice";

/**
 * Reads initData from all available sources.
 *
 * Why not use useTelegramContext().initData?
 * The context derives initData from a ref inside useEffect. Due to React's
 * effect ordering (children fire before parents), this component's effect
 * runs BEFORE TelegramProvider's effect sets the ref. Reading directly from
 * window.Telegram.WebApp avoids this timing issue entirely.
 */
function getInitData(): string {
  // 1. Direct SDK access (most reliable — available synchronously after script load)
  const fromSdk = (window as any).Telegram?.WebApp?.initData;
  if (typeof fromSdk === "string" && fromSdk) return fromSdk;

  // 2. Global set by TelegramProvider (fallback)
  const fromGlobal = (window as any).__LM_TG_INIT_DATA__;
  if (typeof fromGlobal === "string" && fromGlobal) return fromGlobal;

  return "";
}

export default function TelegramAuthBootstrap(): null {
  const dispatch = useAppDispatch();
  const authStatus = useAppSelector(selectAuthStatus);
  const calledRef = useRef(false);

  useEffect(() => {
    // Only run once, and only if we haven't already authenticated
    if (calledRef.current) return;
    if (authStatus === "authenticated" || authStatus === "loading") return;

    const rawInitData = getInitData();
    const isDebug = isBrowserDebugAuthEnabled() && !rawInitData;

    if (!rawInitData && !isDebug) {
      // Not in Telegram and not in debug mode — nothing to do
      return;
    }

    calledRef.current = true;
    dispatch(initStart());

    const body: Record<string, unknown> = {};

    if (rawInitData) {
      body.initData = rawInitData;
    } else if (isDebug) {
      body.debugUser = getBrowserDebugUser();
    }

    const controller = new AbortController();

    fetch("/api/session/telegram/init", {
      method: "POST",
      headers: { "content-type": "application/json" },
      credentials: "include",
      body: JSON.stringify(body),
      signal: controller.signal,
    })
      .then(async (res) => {
        if (!res.ok) {
          const errBody = await res.json().catch(() => ({}));
          throw new Error(errBody?.error || `Auth failed: ${res.status}`);
        }
        return res.json();
      })
      .then((data) => {
        dispatch(
          initSuccess({ isNewUser: data?.isNewUser === true }),
        );
      })
      .catch((err) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        dispatch(initFailure(err instanceof Error ? err.message : "Auth error"));
        calledRef.current = false; // Allow retry
      });

    return () => {
      controller.abort();
      calledRef.current = false; // Reset for StrictMode remount
    };
  }, [dispatch, authStatus]);

  return null;
}
