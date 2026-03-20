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
  const fromSdk = (window as any).Telegram?.WebApp?.initData;
  if (typeof fromSdk === "string" && fromSdk) return fromSdk;

  const fromGlobal = (window as any).__LM_TG_INIT_DATA__;
  if (typeof fromGlobal === "string" && fromGlobal) return fromGlobal;

  return "";
}

/**
 * Performs Telegram auth on mount and auto-recovers when session expires.
 *
 * In a Telegram Mini App, initData is available on every launch (signed fresh
 * by Telegram). This means we can always re-authenticate transparently — even
 * if cookies were lost (iOS WebView session cleanup, Android OEM quirks, etc.).
 *
 * Recovery flow:
 *   authenticated → cookie lost → 401 → refresh fails → sessionExpired
 *   → this effect re-fires → sends initData → new tokens → authenticated
 */
export default function TelegramAuthBootstrap(): null {
  const dispatch = useAppDispatch();
  const authStatus = useAppSelector(selectAuthStatus);
  const inFlightRef = useRef(false);

  useEffect(() => {
    // A request is already in-flight — don't double-fire
    if (inFlightRef.current) return;

    // Already authenticated — nothing to do
    if (authStatus === "authenticated") return;

    // Statuses that should trigger (re-)auth:
    //   "idle"    — first mount, no auth yet
    //   "expired" — cookies lost mid-session, RTK Query refresh failed
    //   "error"   — previous auth attempt failed, retry
    //   "loading" — StrictMode remount after abort

    const rawInitData = getInitData();
    const isDebug = isBrowserDebugAuthEnabled() && !rawInitData;

    if (!rawInitData && !isDebug) {
      return;
    }

    inFlightRef.current = true;
    dispatch(initStart());

    const body: Record<string, unknown> = {};

    if (rawInitData) {
      body.initData = rawInitData;
    } else if (isDebug) {
      body.debugUser = getBrowserDebugUser();
    }

    const controller = new AbortController();

    fetch("/api/session/auth", {
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
        dispatch(initSuccess({ isNewUser: data?.isNewUser === true }));
      })
      .catch((err) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        dispatch(initFailure(err instanceof Error ? err.message : "Auth error"));
      })
      .finally(() => {
        inFlightRef.current = false;
      });

    return () => {
      controller.abort();
      inFlightRef.current = false;
    };
  }, [dispatch, authStatus]);

  return null;
}
