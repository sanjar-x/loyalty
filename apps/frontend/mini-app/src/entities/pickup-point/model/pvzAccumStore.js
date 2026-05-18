/**
 * Pickup-points accumulator cache (CHK-016 Bug #3).
 *
 * Sprint 3e: moved out of features/checkout-flow/model/store, because
 * features/pickup-selection needed the cache but must not import
 * checkout-flow (cross-feature). Here we keep a dedicated Zustand store
 * for pvzAccumCache with sessionStorage persistence (Map is not
 * serializable → entries).
 *
 * Pickup sheet mount → reads the cache so old markers stay visible while
 * new ones are being fetched. Backend re-fetch → merged by id.
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export const usePvzAccumStore = create(
  persist(
    (set) => ({
      // [[externalId, point], ...] — Map JSON-friendly entries
      entries: null,
      setEntries: (entries) =>
        set({ entries: Array.isArray(entries) ? entries : null }),
      clear: () => set({ entries: null }),
    }),
    {
      name: 'lm-pvz-accum',
      storage: createJSONStorage(() =>
        typeof window !== 'undefined' ? window.sessionStorage : undefined
      ),
    }
  )
);
