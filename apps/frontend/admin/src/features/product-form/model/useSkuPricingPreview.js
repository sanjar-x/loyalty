'use client';

import { useEffect, useRef, useState } from 'react';

import { previewSkuPricing } from '@/entities/product';

const DEBOUNCE_MS = 300;

/**
 * Live preview of `sku.sellingPrice` based on the current `purchasePrice`
 * input. Debounces the upstream POST so rapid typing does not stampede the
 * backend, and aborts any prior in-flight request when inputs change so
 * React state never lags behind the latest keystroke.
 *
 * Returns `{ preview, loading, error }`:
 *   - `preview`: backend response `{ finalPrice, contextId, formulaVersionId,
 *     formulaVersionNumber, components }` or null
 *   - `loading`: true while a debounced fetch is in flight
 *   - `error`: error message string from the latest failed fetch, or null
 *
 * Per CAT-023, `productId` is optional — when null/undefined the hook still
 * fires (used by the create-flow form, before the product row exists). The
 * backend (CAT-022) evaluates against category + context + supplier alone
 * in that case.
 */
export function useSkuPricingPreview({
  productId,
  categoryId,
  contextId,
  purchasePrice,
  supplierId,
  enabled = true,
}) {
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const abortRef = useRef(null);

  // Stable serialisation key — `purchasePrice` is an object, plus the few
  // identifiers the upstream needs. Avoids re-firing on object identity churn
  // when the form re-renders with the same logical inputs.
  const amount = purchasePrice?.amount;
  const currency = purchasePrice?.currency;
  const ready =
    enabled &&
    Boolean(categoryId) &&
    Boolean(contextId) &&
    Boolean(currency) &&
    amount != null &&
    amount !== '' &&
    Number(amount) > 0;

  useEffect(() => {
    // Cancel any prior in-flight fetch — the new inputs make its result
    // stale before it can land.
    abortRef.current?.abort();
    abortRef.current = null;

    if (!ready) {
      setPreview(null);
      setLoading(false);
      setError(null);
      return undefined;
    }

    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setError(null);

    const timer = setTimeout(async () => {
      try {
        const result = await previewSkuPricing({
          productId,
          categoryId,
          contextId,
          purchasePrice: { amount: Number(amount), currency },
          supplierId,
          signal: controller.signal,
        });
        if (!controller.signal.aborted) {
          setPreview(result);
          setError(null);
        }
      } catch (err) {
        if (controller.signal.aborted) return;
        if (err?.name === 'AbortError') return;
        setError(err?.message ?? 'Не удалось рассчитать цену');
        setPreview(null);
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }, DEBOUNCE_MS);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [ready, productId, categoryId, contextId, amount, currency, supplierId]);

  return { preview, loading, error };
}
