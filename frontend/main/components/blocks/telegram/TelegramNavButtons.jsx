"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

export default function TelegramNavButtons() {
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    if (!tg?.BackButton || !tg.isVersionAtLeast?.("6.1")) return;

    const isMainPage =
      pathname === "/" ||
      pathname === "/poizon" ||
      pathname === "/catalog" ||
      pathname === "/favorites" ||
      pathname === "/trash" ||
      pathname === "/profile";

    const sync = () => {
      const homeBack = pathname === "/" ? window.__LM_HOME_BACK__ : null;
      if (isMainPage && !homeBack) {
        tg.BackButton.hide();
      } else {
        tg.BackButton.show();
      }
    };

    sync();

    // On home page, poll to detect search/filter state changes
    const interval = pathname === "/"
      ? setInterval(sync, 150)
      : null;

    const onBack = () => {
      const currentHomeBack = window.__LM_HOME_BACK__;
      if (pathname === "/" && typeof currentHomeBack === "function") {
        currentHomeBack();
        return;
      }
      router.back();
    };

    tg.BackButton.onClick(onBack);

    return () => {
      tg.BackButton.offClick(onBack);
      if (interval) clearInterval(interval);
    };
  }, [pathname, router]);

  return null;
}
