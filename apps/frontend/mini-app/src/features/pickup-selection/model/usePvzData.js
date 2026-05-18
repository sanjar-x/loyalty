'use client';

import { useEffect, useMemo, useState } from 'react';

import { useListPickupPointsQuery, usePvzAccumStore } from '@/entities/pickup-point';

/**
 * PVZ data layer — viewport-driven query + accumulation Map (keeps results
 * from various pan/zoom). Audit #1: extracted from
 * `app/checkout/pickup/page.jsx`.
 *
 * Quantization: lat/lon ~0.01° (~1km), radius 5km step — in
 * `useLeafletPvzMap` the `moveend` listener calls `setViewportArgs` with
 * these values, maximizing RTKQ cache hits.
 *
 * CHK-016 Bug #3: `pvzAccum` is cached in `sessionStorage` via Zustand —
 * when the pickup page re-mounts, old markers reappear immediately.
 *
 * @param {{ searchParamsKey: string }} params
 */
export function usePvzData({ searchParamsKey }) {
  // Backend query arguments are derived from URL params:
  //   ?lat=55&lon=37&radius=50  (geolocation or city selected from search)
  //   ?city=Moskva              (fallback when there is no geolocation)
  // Default radius 50km — covers the metropolitan zone of major cities.
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

  // When URL search/initial argument changes, re-sync viewportArgs.
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

  // Accumulated PVZ map — points from all viewport queries merged by id.
  const [pvzAccum, setPvzAccum] = useState(() => {
    const cached = usePvzAccumStore.getState().entries;
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

  // When pvzAccum changes, update the pvz-accum store cache. Map → entries
  // array (sessionStorage can't serialize Map).
  useEffect(() => {
    usePvzAccumStore.getState().setEntries(Array.from(pvzAccum.entries()));
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
