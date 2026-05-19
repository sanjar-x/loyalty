'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { changeProductStatus, productKeys } from '@/entities/product';

import { pathToPublished } from '../lib/pathToPublished';

/**
 * Mutation hook: walks the product through every transition needed to land
 * in `published`. On any backend error (PRODUCT_NOT_READY, conflict, etc.)
 * the chain stops and the error propagates to the caller's onError — the
 * FSM is left at whichever intermediate status succeeded last.
 *
 * Returns the standard TanStack mutation result; consumer typically wires
 * `mutate()` to a single "Опубликовать" button.
 */
export function usePublishProduct(productId) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const product = queryClient.getQueryData(productKeys.detail(productId));
      const currentStatus = product?.status ?? 'draft';

      const path = pathToPublished(currentStatus);
      if (path.length === 0) {
        return { ok: true, alreadyPublished: true };
      }

      // Sequential — each transition needs the prior one to have committed
      // server-side, otherwise the next PATCH fails with "invalid transition".
      for (const target of path) {
        await changeProductStatus(productId, target);
      }
      return { ok: true };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: productKeys.detail(productId),
      });
      queryClient.invalidateQueries({ queryKey: productKeys.lists() });
    },
  });
}
