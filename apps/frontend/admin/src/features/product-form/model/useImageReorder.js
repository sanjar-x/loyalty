'use client';

import { useCallback, useRef, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { productKeys, reorderMedia } from '@/entities/product';

/**
 * Reorder hook that pairs an optimistic local update with the
 * `POST /api/catalog/products/{id}/media/reorder` BFF call.
 *
 * Usage:
 *
 *   const { reorder, isPending, error } = useImageReorder({
 *     productId,                      // null in create mode
 *     onLocalReorder: (next) => onSet(next),
 *   });
 *   reorder(prev, next);              // prev = images before, next = images after
 *
 * Behaviour:
 *   - call `onLocalReorder(next)` synchronously so the UI reflects the
 *     new order immediately (no flicker)
 *   - if `productId` is null (create mode) → no mutation fires; reorder
 *     stays local until the product is saved
 *   - in edit mode → POST {items: [{mediaId, sortOrder}]} for the
 *     subset of images that actually have a `mediaId`. New images that
 *     haven't been associated yet are reordered locally but skipped on
 *     the wire (the create-flow's media association handles their order)
 *   - on backend failure → call `onLocalReorder(prev)` to revert and
 *     surface `error` so the consumer can toast
 */
export function useImageReorder({ productId, onLocalReorder } = {}) {
  const queryClient = useQueryClient();
  const [error, setError] = useState(null);
  const previousOrderRef = useRef(null);

  const mutation = useMutation({
    mutationFn: ({ items }) => reorderMedia(productId, { items }),
    onSuccess: () => {
      if (productId) {
        queryClient.invalidateQueries({
          queryKey: productKeys.media(productId),
        });
      }
    },
    onError: (err) => {
      setError(err);
      const previous = previousOrderRef.current;
      if (previous) {
        onLocalReorder?.(previous);
      }
    },
  });

  // Destructure to avoid passing the unstable mutation object identity
  // through the useCallback dependency list (TanStack Query lint rule).
  const { mutate: persistOrder } = mutation;

  const reorder = useCallback(
    (prev, next) => {
      previousOrderRef.current = prev;
      onLocalReorder?.(next);
      setError(null);

      if (!productId) return; // create-mode: no backend round-trip yet

      const items = next
        .map((image, idx) =>
          image.mediaId ? { mediaId: image.mediaId, sortOrder: idx } : null,
        )
        .filter(Boolean);
      if (items.length === 0) return; // nothing the server knows about

      persistOrder({ items });
    },
    [productId, onLocalReorder, persistOrder],
  );

  const clearError = useCallback(() => setError(null), []);

  return {
    reorder,
    isPending: mutation.isPending,
    error,
    clearError,
  };
}
