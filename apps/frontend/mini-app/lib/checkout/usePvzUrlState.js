'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';

/**
 * Pickup sahifa URL state — `step` (map/list/search), `selectedPvzId`,
 * URL'ni qisman yangilash. Audit #1: `app/checkout/pickup/page.jsx`'dan
 * ajratildi.
 *
 * URL canonical: `searchParamsKey` (string) — `useSearchParams().toString()`
 * dan derive qilingan stable id.
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
      // CHK-016 Bug #8: search step'ga o'tganda eski pvzId/lat/lon/address
      // corrupted state qoldirmasligi uchun tozalanadi (boshqa shahar
      // tanlanganda eski PVZ refer qilinmaydi).
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
