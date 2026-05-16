'use client';

import { useEffect, useMemo } from 'react';
import { useSearchParams } from 'next/navigation';

import { useCheckoutStore } from './store';

/**
 * `/checkout` sahifasi pickup tanlovini URL search-param orqali oladi —
 * `/checkout/pickup` sahifasi `?pickupPvzId=...&pickupProvider=...` bilan
 * qaytaradi. Bu hook uchta mas'uliyatni jamlaydi (audit #1: `checkout/page.jsx`
 * god-komponentidan ajratildi):
 *
 *  1. URL param'larini `pickup` obyektiga parse qiladi
 *  2. uni canonical checkout store'ga sync qiladi — quote/checkout API'lar
 *     doim store'dan o'qiydi, URL'dan emas
 *  3. `/checkout/pickup` ga qaytish uchun deep-link URL'ni quradi
 *
 * ⚠ `providerCode` majburiy: yo'q bo'lsa store sync skip qilinadi. Default
 * fallback (`|| 'cdek'`) yashirin xato beradi — foydalanuvchi Yandex PVZ
 * tanlasa, CDEK'ga rate quote chaqirilib 422 olinardi. `/checkout/pickup`
 * doim `pickupProvider`'ni o'rnatadi.
 *
 * @returns {{ pickup: {
 *   pickupPvzId: string|null, pickupAddress: string|null,
 *   pickupProvider: string|null, pickupLat: number|null, pickupLon: number|null
 * }, openPickupSelection: string }}
 */
export function usePickupFromUrl() {
  const searchParams = useSearchParams();
  const searchParamsKey = searchParams.toString();
  const setPickupAction = useCheckoutStore((s) => s.setPickup);

  const pickup = useMemo(() => {
    const params = new URLSearchParams(searchParamsKey);
    const pickupPvzId = params.get('pickupPvzId')?.trim() || null;
    const pickupAddress = params.get('pickupAddress')?.trim() || null;
    const pickupProvider = params.get('pickupProvider')?.trim() || null;
    // CHK-018 Layer B: lat/lon URL'dan o'qiladi va store'ga uzatiladi —
    // pickup tile bossa map shu hududda ochiladi.
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

  // URL → canonical store. `providerCode` yo'q bo'lsa skip (yuqoridagi izoh).
  useEffect(() => {
    if (!pickup.pickupPvzId || !pickup.pickupProvider) return;
    setPickupAction({
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
    setPickupAction,
  ]);

  // `/checkout/pickup` deep-link: PVZ tanlangan bo'lsa map step + lat/lon,
  // aks holda search step.
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
