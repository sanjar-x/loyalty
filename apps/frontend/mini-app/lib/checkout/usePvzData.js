'use client';

import { useEffect, useMemo, useState } from 'react';

import { useListPickupPointsQuery } from '@/lib/store/api';

import { useCheckoutStore } from './store';

/**
 * PVZ data layer — viewport-driven so'rov + accumulation Map (turli pan/zoom
 * natijalarini saqlab qoladi). Audit #1: `app/checkout/pickup/page.jsx`'dan
 * ajratildi.
 *
 * Quantization: lat/lon ~0.01° (~1km), radius 5km step — `useLeafletPvzMap`'da
 * `moveend` listener `setViewportArgs`'ni shu qiymatlar bilan chaqiradi va RTKQ
 * cache hit'i maksimal bo'ladi.
 *
 * CHK-016 Bug #3: `pvzAccum` `sessionStorage`'da Zustand orqali keshlanadi —
 * pickup sahifa qayta mount paytida eski markerlar darhol qayta paydo bo'ladi.
 *
 * @param {{ searchParamsKey: string }} params
 */
export function usePvzData({ searchParamsKey }) {
  // Backend query argumentlari URL params'dan derive qilinadi:
  //   ?lat=55&lon=37&radius=50  (geolokatsiya yoki search'dan tanlangan shahar)
  //   ?city=Moskva              (geolokatsiya yo'q bo'lganda fallback)
  // Default radius 50km — yirik shaharlar metropoliya zonasini qoplaydi.
  const initialPickupArgs = useMemo(() => {
    const params = new URLSearchParams(searchParamsKey);
    const latStr = params.get('lat');
    const lonStr = params.get('lon');
    const lat = latStr != null ? Number(latStr) : NaN;
    const lon = lonStr != null ? Number(lonStr) : NaN;
    if (Number.isFinite(lat) && Number.isFinite(lon)) {
      const radiusStr = params.get('radius');
      const radiusKm = radiusStr ? Number(radiusStr) : 50;
      return {
        latitude: lat,
        longitude: lon,
        radiusKm: Number.isFinite(radiusKm) ? radiusKm : 50,
      };
    }
    const city = params.get('city');
    if (city && city.trim()) {
      return { city: city.trim(), countryCode: 'RU' };
    }
    return null;
  }, [searchParamsKey]);

  const [viewportArgs, setViewportArgs] = useState(initialPickupArgs);

  // URL search/initial argument o'zgarganda viewportArgs'ni qayta sync qilamiz.
  useEffect(() => {
    if (initialPickupArgs) setViewportArgs(initialPickupArgs);
  }, [initialPickupArgs]);

  const {
    data: pickupData,
    isFetching: isPickupFetching,
    isError: isPickupError,
  } = useListPickupPointsQuery(viewportArgs ?? {}, {
    skip: !viewportArgs,
  });

  // Accumulated PVZ map — barcha viewport so'rovlaridan kelgan point'lar
  // id bo'yicha mergetilgan.
  const [pvzAccum, setPvzAccum] = useState(() => {
    const cached = useCheckoutStore.getState().pvzAccumCache;
    return new Map(Array.isArray(cached) ? cached : []);
  });

  useEffect(() => {
    const incoming = pickupData?.points;
    if (!Array.isArray(incoming) || incoming.length === 0) return;
    setPvzAccum((prev) => {
      const next = new Map(prev);
      for (const p of incoming) {
        if (!p?.id) continue;
        next.set(p.id, p);
      }
      return next;
    });
  }, [pickupData]);

  // pvzAccum o'zgarganda store cache yangilash. Map → entries array
  // (sessionStorage Map'ni serialize qila olmaydi).
  useEffect(() => {
    useCheckoutStore.getState().setPvzAccumEntries(Array.from(pvzAccum.entries()));
  }, [pvzAccum]);

  const pvzPoints = useMemo(() => Array.from(pvzAccum.values()), [pvzAccum]);
  const providerErrors = pickupData?.errors ?? {};
  const pvzPointById = pvzAccum;

  return {
    viewportArgs,
    setViewportArgs,
    pvzPoints,
    pvzPointById,
    providerErrors,
    isPickupFetching,
    isPickupError,
  };
}
