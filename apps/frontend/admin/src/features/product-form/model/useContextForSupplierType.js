'use client';

import { useQuery } from '@tanstack/react-query';

import { apiClient, ApiError } from '@/shared/api/clientFetch';
import { REFERENCE_DATA_STALE_TIME_MS } from '@/shared/query';

/**
 * Authoritative resolver for the pricing-context bound to a given
 * `supplier_type` (CAT-015). Mirrors the `pricing_supplier_type_context_mapping`
 * table — the same source of truth the autonomous recompute uses.
 *
 * Throws `ApiError(CONTEXT_NOT_MAPPED)` when the supplier type has no
 * pricing context configured (instead of returning null) so consumers can
 * distinguish "still loading" from "explicitly unmapped" and surface the
 * latter as an actionable error rather than silently rendering nothing.
 */
export function useContextForSupplierType(supplierType) {
  return useQuery({
    queryKey: ['pricing', 'context-for-supplier-type', supplierType],
    queryFn: async () => {
      const res = await apiClient.get(
        `/api/pricing/supplier-type-mapping/${supplierType}`,
      );
      const contextId = res?.contextId ?? null;
      if (!contextId) {
        throw new ApiError({
          code: 'CONTEXT_NOT_MAPPED',
          message:
            'Для этого типа поставщика не настроена ценовая модель. Добавьте mapping в настройках цен.',
          status: 404,
        });
      }
      return contextId;
    },
    enabled: Boolean(supplierType),
    staleTime: REFERENCE_DATA_STALE_TIME_MS,
    retry: false,
  });
}
