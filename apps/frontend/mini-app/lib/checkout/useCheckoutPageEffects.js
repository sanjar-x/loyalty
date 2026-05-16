'use client';

import { useEffect, useRef } from 'react';

import { toast } from '@/lib/ui/toast';
import { useCheckoutStore, CheckoutStatus } from './store';

/**
 * `/checkout` sahifasining backend-flow bilan bog'liq uchta yon-effekti
 * (audit #1: `checkout/page.jsx` god-komponentidan ajratildi). Uchchalasi ham
 * "latest callback in ref" pattern'ini ishlatadi — `flow` har render'da yangi
 * closure qaytaradi, lekin effekt minimal dep bilan qayta ishga tushadi:
 *
 *  1. **CONFIRMED → navigatsiya** — status CONFIRMED bo'lsa `flow.onConfirmed()`
 *     (sahifa success ekranga o'tadi). Effekt faqat `status`'ga bog'liq.
 *  2. **Xato → toast** — `flow.error` o'zgarsa toast ko'rsatiladi
 *     (auto-fire'lar: QUOTE_EXPIRED, ATTEMPT_EXPIRED, provider unavailable).
 *     `code|message` bo'yicha dedup — bir xil xato 2 marta chiqmaydi.
 *  3. **Unmount → abandon** — sahifadan chiqishda FROZEN/INITIATING/CONFIRMING
 *     bo'lsa `flow.abandon()` (frozen cart'ni unfreeze, best-effort). Status
 *     snapshot `getState()` orqali olinadi — stale closure yo'q.
 *
 * @param {ReturnType<import('./useCheckoutFlow').useCheckoutFlow>} flow
 */
export function useCheckoutPageEffects(flow) {
  const status = useCheckoutStore((s) => s.status);

  // 1. CONFIRMED → navigatsiya. `onConfirmed` har render'da yangi closure —
  //    ref'da ushlab turamiz, effekt faqat `status` o'zgarganda chaqiriladi.
  const onConfirmedRef = useRef(flow.onConfirmed);
  useEffect(() => {
    onConfirmedRef.current = flow.onConfirmed;
  });
  useEffect(() => {
    if (status === CheckoutStatus.CONFIRMED) {
      onConfirmedRef.current?.();
    }
  }, [status]);

  // 2. Backend xatolarini toast bilan surfacing. Pay button ichidagi alohida
  //    toast.error ham bor — duplikat bo'lmasligi uchun `code|message` dedup.
  const lastErrorIdRef = useRef(null);
  useEffect(() => {
    const err = flow.error;
    if (!err) {
      lastErrorIdRef.current = null;
      return;
    }
    const id = `${err.code || ''}|${err.message || ''}`;
    if (id === lastErrorIdRef.current) return;
    lastErrorIdRef.current = id;
    if (err.message) toast.error(err.message);
  }, [flow.error]);

  // 3. Unmount'da frozen cart'ni unfreeze (best-effort). `abandon` LATEST
  //    callback'i ref'da; cleanup status snapshot'ini `getState()`'dan oladi.
  const abandonRef = useRef(flow.abandon);
  useEffect(() => {
    abandonRef.current = flow.abandon;
  }, [flow.abandon]);
  useEffect(() => {
    return () => {
      const s = useCheckoutStore.getState();
      if (
        s.status === CheckoutStatus.FROZEN ||
        s.status === CheckoutStatus.INITIATING ||
        s.status === CheckoutStatus.CONFIRMING
      ) {
        try {
          abandonRef.current?.();
        } catch {
          // ignore — cancel best-effort, backend TTL kafolat
        }
      }
    };
  }, []);
}
