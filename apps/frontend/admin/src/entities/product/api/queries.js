'use client';

import { useQuery } from '@tanstack/react-query';
import {
  getProduct,
  getProductCompleteness,
  listProductMedia,
  validatePublish,
} from './products';
import { productKeys } from './keys';

/**
 * Single product detail (everything needed for the detail/edit pages).
 * Disabled until productId is provided.
 */
export function useProduct(productId) {
  return useQuery({
    queryKey: productKeys.detail(productId),
    queryFn: () => getProduct(productId),
    enabled: Boolean(productId),
  });
}

/**
 * Completeness summary for a product (filled-required / missing-required …).
 * Backed by `/products/:id/completeness`. Disabled until productId is provided.
 */
export function useProductCompleteness(productId) {
  return useQuery({
    queryKey: productKeys.completeness(productId),
    queryFn: () => getProductCompleteness(productId),
    enabled: Boolean(productId),
  });
}

/**
 * Media assets attached to a product.
 * Disabled until productId is provided.
 */
export function useProductMedia(productId) {
  return useQuery({
    queryKey: productKeys.media(productId),
    queryFn: () => listProductMedia(productId),
    enabled: Boolean(productId),
  });
}

/**
 * Live publish-gate verdict (CAT-C1.1 / F-3).
 *
 * Returns the same shape backend uses to power the publish-gate panel —
 * `{ ok, currentStatus, nextStatus, skuDiagnostics, gateFailures }`. The
 * SSE-driven invalidation on `productKeys.detail(productId)` cascades
 * here automatically because the key is nested under it; the page-level
 * SKU pricing events handler can keep firing `invalidateQueries(productKeys
 * .detail(productId))` without needing to know about the validate key.
 *
 * staleTime stays 0 — pricing state changes in real-time and admins
 * should never see a stale verdict.
 */
export function useValidatePublish(productId, { enabled = true } = {}) {
  return useQuery({
    queryKey: productKeys.validatePublish(productId),
    queryFn: () => validatePublish(productId),
    enabled: enabled && Boolean(productId),
    staleTime: 0,
  });
}
