'use client';

import { useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';

import { useBackHandlerStore } from '@/features/telegram-api';

export default function TelegramNavButtons() {
  const pathname = usePathname();
  const router = useRouter();
  // Reactive: when a page registers/removes a back-handler, the effect
  // re-runs. Previously this was done via a `window.__LM_*` global +
  // `setInterval(150)` polling on the home page.
  const homeBack = useBackHandlerStore((s) => s.homeBack);
  const pickupBack = useBackHandlerStore((s) => s.pickupBack);

  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    if (!tg?.BackButton || !tg.isVersionAtLeast?.('6.1')) return;

    const isMainPage =
      pathname === '/' ||
      pathname === '/poizon' ||
      pathname === '/catalog' ||
      pathname === '/favorites' ||
      pathname === '/cart' ||
      pathname === '/profile';

    // On main pages BackButton is hidden — with one exception: on the home
    // page, search/filter is open (`homeBack` is registered).
    const homeHasBack = pathname === '/' && typeof homeBack === 'function';
    if (isMainPage && !homeHasBack) {
      tg.BackButton.hide();
    } else {
      tg.BackButton.show();
    }

    const onBack = () => {
      // Home: custom search/filter dismiss intent
      if (pathname === '/' && typeof homeBack === 'function') {
        homeBack();
        return;
      }
      // CHK-016 Bug #1/#5: pickup step-based back — map/list → search,
      // search → /checkout. Otherwise the history stack gets stuck at the top
      // for the hybrid model.
      if (pathname === '/checkout/pickup' && typeof pickupBack === 'function') {
        pickupBack();
        return;
      }
      router.back();
    };

    tg.BackButton.onClick(onBack);

    return () => {
      tg.BackButton.offClick(onBack);
    };
  }, [pathname, router, homeBack, pickupBack]);

  return null;
}
