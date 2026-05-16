'use client';

import { useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';

import { useBackHandlerStore } from '@/lib/features/telegram/back-handler';

export default function TelegramNavButtons() {
  const pathname = usePathname();
  const router = useRouter();
  // Reaktiv: sahifa back-handler'ni ro'yxatdan o'tkazsa/olib tashlasa,
  // effect qayta ishga tushadi. Ilgari bu `window.__LM_*` global + bosh
  // sahifada `setInterval(150)` polling orqali qilingan edi.
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

    // Asosiy sahifalarda BackButton yashirin — bundan mustasno: bosh
    // sahifada qidiruv/filtr ochiq (`homeBack` ro'yxatdan o'tgan).
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
      // search → /checkout. Aks holda history stack hibrid model uchun
      // tepada qotib qoladi.
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
