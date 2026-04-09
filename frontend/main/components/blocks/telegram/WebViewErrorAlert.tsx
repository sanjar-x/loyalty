"use client";

import { useEffect, useState } from "react";

import { useTelegram } from "@/lib/telegram";

import styles from "./WebViewErrorAlert.module.css";

export default function WebViewErrorAlert() {
  const { isReady, isAvailable } = useTelegram();
  const [shouldShow, setShouldShow] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const timer = window.setTimeout(() => {
      setShouldShow(!isAvailable && !isReady);
    }, 150);

    return () => window.clearTimeout(timer);
  }, [isAvailable, isReady]);

  if (!shouldShow) return null;

  return (
    <div role="alert" className={styles.alert}>
      Telegram WebApp topilmadi. Ilovani Telegram ichida oching.
    </div>
  );
}
