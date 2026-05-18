'use client';

import { useEffect, useMemo } from 'react';
import { useSearchParams } from 'next/navigation';

import { emitPickupSelected } from '@/shared/lib/events';

/**
 * The `/checkout` page receives the pickup selection via URL search params —
 * the `/checkout/pickup` page returns with `?pickupPvzId=...&pickupProvider=...`.
 * This hook bundles three responsibilities (audit #1: extracted from the
 * `checkout/page.jsx` god-component):
 *
 *  1. parses URL params into a `pickup` object
 *  2. syncs it to the canonical checkout store — quote/checkout APIs
 *     always read from the store, not from the URL
 *  3. builds the deep-link URL to return to `/checkout/pickup`
 *
 * ⚠ `providerCode` is required: if missing, store sync is skipped. The default
 * fallback (`|| 'cdek'`) caused a hidden bug — when the user selected a Yandex PVZ,
 * a rate quote was called to CDEK and a 422 was returned. `/checkout/pickup`
 * always sets `pickupProvider`.
 *
 * @returns {{ pickup: {
 *   pickupPvzId: string|null, pickupAddress: string|null,
 *   pickupProvider: string|null, pickupLat: number|null, pickupLon: number|null
 * }, openPickupSelection: string }}
 */
export function usePickupFromUrl() {
  const searchParams = useSearchParams();
  const searchParamsKey = searchParams.toString();

  const pickup = useMemo(() => {
    const params = new URLSearchParams(searchParamsKey);
    const pickupPvzId = params.get('pickupPvzId')?.trim() || null;
    const pickupAddress = params.get('pickupAddress')?.trim() || null;
    const pickupProvider = params.get('pickupProvider')?.trim() || null;
    // CHK-018 Layer B: lat/lon is read from the URL and passed to the store —
    // when the pickup tile is tapped, the map opens at that location.
    const latStr = params.get('pickupLat');
    const lonStr = params.get('pickupLon');
    const lat = latStr ? Number(latStr) : null;
    const lon = lonStr ? Number(lonStr) : null;
    return {
      pickupPvzId,
      pickupAddress,
      pickupProvider,
      pickupLat: Number.isFinite(lat) ? lat : null,
      pickupLon: Number.isFinite(lon) ? lon : null,
    };
  }, [searchParamsKey]);

  // Sprint 3e: URL → event-bus emit. The checkout-flow store listens for
  // onPickupSelected and invokes setPickup (FSM action). Breaks the
  // cross-feature dep pickup-selection → checkout-flow.
  useEffect(() => {
    if (!pickup.pickupPvzId || !pickup.pickupProvider) return;
    emitPickupSelected({
      externalId: pickup.pickupPvzId,
      providerCode: pickup.pickupProvider,
      address: pickup.pickupAddress || '',
      lat: pickup.pickupLat,
      lon: pickup.pickupLon,
    });
  }, [
    pickup.pickupPvzId,
    pickup.pickupProvider,
    pickup.pickupAddress,
    pickup.pickupLat,
    pickup.pickupLon,
  ]);

  // `/checkout/pickup` deep-link: when a PVZ is selected, map step + lat/lon,
  // otherwise search step.
  const openPickupSelection = useMemo(() => {
    if (pickup.pickupPvzId) {
      const params = new URLSearchParams();
      params.set('step', 'map');
      params.set('pvzId', pickup.pickupPvzId);
      if (pickup.pickupLat != null && pickup.pickupLon != null) {
        params.set('lat', String(pickup.pickupLat));
        params.set('lon', String(pickup.pickupLon));
        params.set('radius', '10');
      }
      return `/checkout/pickup?${params.toString()}`;
    }
    return '/checkout/pickup?step=search';
  }, [pickup.pickupPvzId, pickup.pickupLat, pickup.pickupLon]);

  return { pickup, openPickupSelection };
}
