'use client';

import { useMemo } from 'react';

import { useListMyPassportsQuery } from '../api/passportApi';

/**
 * Reusable selector helpers around the passports roster. Buy-now's
 * `PassportStep` uses it to surface the list + a "current passport"
 * convenience; future cart-flow checkout / profile pages can reuse the
 * same hook without re-implementing the loading/empty-state plumbing.
 *
 * Returns:
 *   • items[]                  — non-archived passports, codegen shape
 *   • byId(passportId)         — Map-style lookup
 *   • isLoading                — first-load flag for skeleton UI
 *   • isError                  — query failed
 *   • refetch()                — wrapper for retry button
 *
 * The hook never picks a default; consumers decide which passport (if
 * any) is "current". See ADR-011 — Passport is M:N with Recipient via
 * Order, so the concept of a single "default" doesn't belong here.
 */
export function usePassportSelection() {
  const { data, isLoading, isError, refetch } = useListMyPassportsQuery();

  const items = useMemo(() => {
    const list = Array.isArray(data?.items) ? data.items : [];
    return list.filter((p) => p && p.isArchived !== true);
  }, [data]);

  const map = useMemo(() => {
    const m = new Map();
    for (const p of items) {
      if (p?.passportId) m.set(p.passportId, p);
    }
    return m;
  }, [items]);

  return {
    items,
    byId: (passportId) => (passportId ? (map.get(passportId) ?? null) : null),
    isLoading,
    isError,
    refetch,
  };
}
