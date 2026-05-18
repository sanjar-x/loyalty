'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

/**
 * Pickup page URL state — `step` (map/list/search), `selectedPvzId`,
 * partial URL updates. Audit #1: extracted from `app/checkout/pickup/page.jsx`.
 *
 * URL canonical: `searchParamsKey` (string) — stable id derived from
 * `useSearchParams().toString()`.
 *
 * @param {{ searchParamsKey: string, router: any }} params
 */
export function usePvzUrlState({ searchParamsKey, router }) {
  const initialStep = useMemo(() => {
    const step = new URLSearchParams(searchParamsKey).get('step');
    if (step === 'map' || step === 'list' || step === 'search') return step;
    return 'search';
  }, [searchParamsKey]);

  const [step, setStep] = useState(initialStep);

  useEffect(() => {
    setStep(initialStep);
  }, [initialStep]);

  const selectedPvzId = useMemo(() => {
    const id = new URLSearchParams(searchParamsKey).get('pvzId');
    return id && id.trim() ? id : null;
  }, [searchParamsKey]);

  const replacePickupUrl = useCallback(
    (update) => {
      const params = new URLSearchParams(searchParamsKey);
      update(params);
      router.replace(`/checkout/pickup?${params.toString()}`);
    },
    [router, searchParamsKey]
  );

  const setStepAndUrl = (next) => {
    setStep(next);
    replacePickupUrl((params) => {
      params.set('step', next);
      // CHK-016 Bug #8: when switching to the search step, clear old
      // pvzId/lat/lon/address so we don't leave corrupted state (when a
      // different city is selected, the old PVZ shouldn't be referenced).
      if (next === 'search') {
        params.delete('pvzId');
        params.delete('lat');
        params.delete('lon');
        params.delete('address');
        params.delete('radius');
      }
    });
  };

  return { step, setStep, selectedPvzId, replacePickupUrl, setStepAndUrl };
}
