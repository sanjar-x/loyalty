'use client';

import { useEffect, useRef, useState } from 'react';

/**
 * Subscribe to the pricing recompute SSE stream for a product (CAT-005).
 *
 * Each push event has the shape:
 *   {
 *     skuId: string,
 *     pricingStatus: 'priced' | 'pending' | 'stale_fx' |
 *                    'missing_purchase_price' | 'formula_error',
 *     sellingPrice: { amount, currency } | null,
 *     pricedAt: string | null,
 *     pricedFailureReason: string | null,
 *   }
 *
 * Native `EventSource` reconnects on transient network errors out of the
 * box, but stops cold on terminal HTTP errors (401 / 4xx) — once the BFF
 * returns one of those, the stream silently goes to `CLOSED` and the page
 * keeps running on a stale snapshot. The hook surfaces that transition via
 * a returned `connectionError` flag so consumers can show a "live updates
 * disconnected" banner and prompt a refresh.
 *
 * `onEvent` is captured in a ref so callers don't have to memoise it — the
 * stream is bound to productId, not to the function identity.
 */
export function useSkuPricingEvents(productId, onEvent) {
  const onEventRef = useRef(onEvent);
  const [connectionError, setConnectionError] = useState(false);

  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    if (!productId) return undefined;
    if (typeof window === 'undefined' || typeof EventSource === 'undefined') {
      return undefined;
    }

    const url = `/api/catalog/products/${productId}/sku-pricing-events`;
    const source = new EventSource(url, { withCredentials: true });
    setConnectionError(false);

    function handleStatus(event) {
      let payload;
      try {
        payload = JSON.parse(event.data);
      } catch {
        // Malformed body — swallow this single event and let the next valid
        // one through. (Real keepalive comment frames never reach here, the
        // protocol filters them, so this catch only fires on protocol drift.)
        return;
      }
      onEventRef.current?.(payload);
    }

    function handleError() {
      // EventSource reconnects autonomously while readyState === CONNECTING.
      // Only flag the consumer when the stream lands in CLOSED (= 2) — that
      // means the browser gave up (auth failure, server-side abort).
      if (source.readyState === EventSource.CLOSED) {
        setConnectionError(true);
        source.close();
      }
    }

    source.addEventListener('status', handleStatus);
    source.addEventListener('message', handleStatus);
    source.addEventListener('error', handleError);

    return () => {
      source.removeEventListener('status', handleStatus);
      source.removeEventListener('message', handleStatus);
      source.removeEventListener('error', handleError);
      source.close();
    };
  }, [productId]);

  return { connectionError };
}
