"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

export default function TelegramNavButtons() {
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    if (!tg) return;

    const isMainPage =
      pathname === "/" ||
      pathname === "/poizon" ||
      pathname === "/catalog" ||
      pathname === "/favorites" ||
      pathname === "/trash" ||
      pathname === "/profile";

    if (isMainPage) {
      tg.BackButton?.hide();
    } else {
      tg.BackButton?.show();
    }

    const onBack = () => {
      // ichki page -> back
      router.back();
    };

    tg.BackButton?.onClick(onBack);

    return () => {
      tg.BackButton?.offClick(onBack);
    };
  }, [pathname, router]);

  return null;
}
