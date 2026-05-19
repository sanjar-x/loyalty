/**
 * Promise-based wrapper over the SKU pricing-events SSE stream.
 *
 * Resolves with `true` once every SKU we've seen on the stream is in the
 * `priced` state. Resolves with `false` on timeout. Rejects only on
 * connection-level errors (terminal CLOSED with no successful events).
 *
 * Used by the product-form auto-publish flow: after createProduct, we wait
 * for the recompute pipeline to land all sellingPrices, then chain through
 * the publish FSM. The default timeout (30s) is the same SLA the
 * `subscribeMediaStatus` helper uses for media processing.
 *
 * NOTE: caller passes `productId` only; we open a fresh EventSource
 * internally. The detail-page hook `useSkuPricingEvents` keeps its own
 * connection — this is a one-shot helper, not a long-lived consumer.
 */
export function waitForAllSkusPriced(productId, { timeout = 30_000 } = {}) {
  return new Promise((resolve, reject) => {
    if (typeof window === 'undefined' || typeof EventSource === 'undefined') {
      resolve(false);
      return;
    }

    const url = `/api/catalog/products/${productId}/sku-pricing-events`;
    const eventSource = new EventSource(url, { withCredentials: true });
    const skuStates = new Map();
    let settled = false;

    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      cleanup();
      resolve(false);
    }, timeout);

    function cleanup() {
      clearTimeout(timer);
      eventSource.removeEventListener('status', onMessage);
      eventSource.removeEventListener('message', onMessage);
      eventSource.onerror = null;
      eventSource.close();
    }

    function onMessage(event) {
      if (settled) return;
      let payload;
      try {
        payload = JSON.parse(event.data);
      } catch {
        return;
      }
      if (!payload?.skuId) return;
      skuStates.set(payload.skuId, payload.pricingStatus);

      // Don't resolve until at least one event has landed — without this
      // an empty stream would resolve immediately with `true`.
      if (skuStates.size === 0) return;
      const allPriced = [...skuStates.values()].every((s) => s === 'priced');
      if (allPriced) {
        settled = true;
        cleanup();
        resolve(true);
      }
    }

    eventSource.addEventListener('status', onMessage);
    eventSource.addEventListener('message', onMessage);

    eventSource.onerror = () => {
      if (settled) return;
      // Mirror the readyState gate from useSkuPricingEvents — only give up
      // on terminal CLOSED, not on transient reconnect attempts.
      if (eventSource.readyState !== EventSource.CLOSED) return;
      settled = true;
      cleanup();
      // Treat connection failure as "could not confirm" rather than a hard
      // error — caller falls back to manual publish.
      resolve(false);
    };
  });
}
