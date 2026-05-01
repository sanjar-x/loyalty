'use client';

import { useQuery } from '@tanstack/react-query';
import {
  fetchProductCounts,
  getProduct,
  getProductCompleteness,
  listProductMedia,
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
 * Status counts grouped by FSM state — for the product list tabs.
 */
export function useProductCounts() {
  return useQuery({
    queryKey: productKeys.counts(),
    queryFn: fetchProductCounts,
  });
}
