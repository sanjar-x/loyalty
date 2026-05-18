'use client';

import { useEffect, useRef } from 'react';

import { toast } from '@/shared/ui/Toaster';
import { useCheckoutStore, CheckoutStatus } from './store';

/**
 * Three backend-flow side-effects for the `/checkout` page (audit #1:
 * extracted from the `checkout/page.jsx` god-component). All three use the
 * "latest callback in ref" pattern — `flow` returns a fresh closure each
 * render, but the effect re-runs with a minimal dep list:
 *
 *  1. **CONFIRMED → navigation** — when status is CONFIRMED call
 *     `flow.onConfirmed()` (the page navigates to the success screen). The
 *     effect depends only on `status`.
 *  2. **Error → toast** — when `flow.error` changes show a toast
 *     (auto-fires: QUOTE_EXPIRED, ATTEMPT_EXPIRED, provider unavailable).
 *     Dedup by `code|message` — the same error doesn't show twice.
 *  3. **Unmount → abandon** — when leaving the page in FROZEN/INITIATING/
 *     CONFIRMING state, call `flow.abandon()` (unfreeze the frozen cart,
 *     best-effort). The status snapshot is read via `getState()` — no stale
 *     closure.
 *
 * @param {ReturnType<import('./useCheckoutFlow').useCheckoutFlow>} flow
 */
export function useCheckoutPageEffects(flow) {
  const status = useCheckoutStore((s) => s.status);

  // 1. CONFIRMED → navigation. `onConfirmed` is a new closure each render —
  //    hold it in a ref, effect only fires when `status` changes.
  const onConfirmedRef = useRef(flow.onConfirmed);
  useEffect(() => {
    onConfirmedRef.current = flow.onConfirmed;
  });
  useEffect(() => {
    if (status === CheckoutStatus.CONFIRMED) {
      onConfirmedRef.current?.();
    }
  }, [status]);

  // 2. Surface backend errors via toast. There's a separate toast.error inside
  //    the pay button — dedup by `code|message` to avoid duplicates.
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

  // 3. On unmount unfreeze the frozen cart (best-effort). The LATEST
  //    `abandon` callback is in a ref; cleanup reads the status snapshot
  //    via `getState()`.
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
          // ignore — cancel is best-effort, backend TTL is the safety net
        }
      }
    };
  }, []);
}
