'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { normalizeApiError } from '@/shared/api/errors';
import { toast } from '@/shared/ui/Toaster';
import { distanceKm } from '@/shared/lib/geo';

// Cross-feature import accepted: one-tap Buy Now UX (Q11) needs an inline
// pickup-selector. Same rationale as RecipientStep — see PHASE-9-TODO.md
// for the slated post-god-component refactor.
// eslint-disable-next-line no-restricted-imports
import {
  PickupModeToggle,
  ProviderChips,
  PvzDetailSheet,
  useLeafletPvzMap,
  usePvzData,
} from '@/features/pickup-selection';
// Cross-feature import accepted: reuse cart-flow's shared rate-quote →
// store mapper instead of duplicating shape juggling (audit FE-4 dedup).
// eslint-disable-next-line no-restricted-imports
import { mapRateQuoteResponseToQuote } from '@/features/checkout-flow';

import { useBuyNowStore } from '../../model/useBuyNowCheckout';
import { useBuyNowRateQuoteMutation } from '../../api/buyNowApi';
import styles from '../BuyNowSheet.module.css';
import stepStyles from './PickupStep.module.css';

/**
 * Step 3 — Pickup point + delivery quote.
 *
 * Inline pickup-selector that mirrors the full-screen /checkout/pickup
 * UX inside the BuyNowSheet. Composed of three reusable pieces from
 * `features/pickup-selection`:
 *
 *   • `usePvzData`           — viewport-driven PVZ query + accumulator
 *                              (sessionStorage merge across pan/zoom)
 *   • `useLeafletPvzMap`     — Leaflet imperative shell (markers,
 *                              cluster, geolocation tracking)
 *   • `PvzDetailSheet`       — single PVZ detail overlay with «Доставить
 *                              сюда» confirm
 *
 * The Leaflet container DOM id is dedicated (`buy-now-pvz-map`) so two
 * map instances can coexist while the customer navigates between the
 * cart-flow and Buy Now sheets. `useLeafletPvzMap` accepts the id as a
 * parameter (default kept for cart-flow page compatibility).
 *
 * Quote auto-fetch — once the customer confirms a PVZ:
 *   1. setPickup(point)            ── canonical store value
 *   2. useBuyNowRateQuoteMutation  ── POST /storefront/logistics/rates/quote
 *   3. mapRateQuoteResponseToQuote ── identical shape to cart-flow
 *   4. setQuote(quote)             ── unlock Confirm step
 *
 * UX (per product Q): polished sheet, not MVP. Map + list toggle, full
 * PVZ filter chips, automatic quote refresh after pickup change.
 *
 * Backend: ADR-010 I3 — Buy Now uses `Order.create(...)`, so the same
 * `resolve_delivery_quote` helper covers cart-flow and Buy Now quotes —
 * we can rely on identical ownership/currency/expiry semantics.
 */

export default function PickupStep() {
  const pickup = useBuyNowStore((s) => s.pickup);
  const quote = useBuyNowStore((s) => s.quote);
  const setPickup = useBuyNowStore((s) => s.setPickup);
  const setQuote = useBuyNowStore((s) => s.setQuote);
  const nextStep = useBuyNowStore((s) => s.nextStep);
  const skuId = useBuyNowStore((s) => s.skuId);
  const quantity = useBuyNowStore((s) => s.quantity);

  /* ── PVZ data + map state ── */

  // The selector lives inside a fixed-size bottom-sheet; we hand
  // `usePvzData` an empty URL-state key so it falls back to the
  // viewport-only path (lat/lon from `setViewportArgs`).
  const { setViewportArgs, pvzPoints, pvzPointById, providerErrors, isPickupFetching } = usePvzData(
    { searchParamsKey: '' }
  );

  const [activeProvider, setActiveProvider] = useState('all');
  const [step, setLocalStep] = useState('map'); // 'map' | 'list'
  const [selectedPvzId, setSelectedPvzId] = useState(pickup?.externalId ?? null);
  const [pvzSheetOpen, setPvzSheetOpen] = useState(false);
  const [listQuery, setListQuery] = useState('');

  const onMarkerClickRef = useRef(null);

  // Seed accum cache so the map shows previously-fetched markers
  // immediately on re-open. usePvzData also reads from this store.
  useEffect(() => {
    return () => {
      // Don't clear on unmount — accum cache survives sheet close so
      // re-opening Buy Now restores the same neighbourhood instantly.
    };
  }, []);

  const { startUserTracking, stopUserTracking, isUserTracking, geoError, userLocation } =
    useLeafletPvzMap({
      step,
      searchParamsKey: '',
      pvzPoints,
      pvzPointById,
      activeProvider,
      selectedPvzId,
      setViewportArgs,
      onMarkerClickRef,
      elementId: 'buy-now-pvz-map',
    });

  const openPvzDetail = useCallback((pvzId) => {
    setSelectedPvzId(pvzId);
    setPvzSheetOpen(true);
  }, []);

  useEffect(() => {
    onMarkerClickRef.current = openPvzDetail;
  }, [openPvzDetail]);

  const selectedPvz = useMemo(() => {
    if (!selectedPvzId) return null;
    return pvzPointById.get(selectedPvzId) ?? null;
  }, [pvzPointById, selectedPvzId]);

  /* ── Distance-sorted list view ── */

  const pointsWithDistance = useMemo(() => {
    if (!userLocation) return pvzPoints;
    return pvzPoints.map((p) => ({
      ...p,
      _distanceKm: distanceKm(userLocation, { lat: p.lat, lon: p.lon }),
    }));
  }, [pvzPoints, userLocation]);

  const filteredPvz = useMemo(() => {
    if (step !== 'list') return [];
    const q = listQuery.trim().toLowerCase();
    const base = !q
      ? pointsWithDistance
      : pointsWithDistance.filter((p) =>
          `${p.providerLabel} ${p.addressLine}`.toLowerCase().includes(q)
        );
    const filtered =
      activeProvider === 'all' ? base : base.filter((p) => p.providerCode === activeProvider);
    if (!userLocation) return filtered;
    return [...filtered].sort((a, b) => (a._distanceKm ?? Infinity) - (b._distanceKm ?? Infinity));
  }, [pointsWithDistance, activeProvider, listQuery, step, userLocation]);

  /* ── Quote fetch ── */

  const [requestQuote, quoteState] = useBuyNowRateQuoteMutation();
  const inflightQuoteRef = useRef(null);

  const refreshQuote = useCallback(
    async (point) => {
      if (!skuId || !point?.providerCode || !point?.externalId) return null;
      // Latest-wins: cancel the prior inflight request so the customer
      // sees the price for the *current* selection.
      if (inflightQuoteRef.current?.abort) {
        try {
          inflightQuoteRef.current.abort();
        } catch {
          // ignore
        }
      }
      const promise = requestQuote({
        items: [{ skuId, quantity }],
        providerCode: point.providerCode,
        pickupPointExternalId: point.externalId,
        serviceCode: null,
      });
      inflightQuoteRef.current = promise;
      try {
        const resp = await promise.unwrap();
        const mapped = mapRateQuoteResponseToQuote(resp);
        if (!mapped) {
          toast.error('Не удалось рассчитать стоимость доставки');
          return null;
        }
        setQuote(mapped);
        return mapped;
      } catch (err) {
        if (err?.name === 'AbortError' || err?.error?.name === 'AbortError') return null;
        const norm = normalizeApiError(err);
        toast.error(norm.message || 'Не удалось рассчитать стоимость доставки');
        return null;
      } finally {
        if (inflightQuoteRef.current === promise) inflightQuoteRef.current = null;
      }
    },
    [skuId, quantity, requestQuote, setQuote]
  );

  const handleConfirmPickup = useCallback(
    async (point) => {
      if (!point?.externalId || !point?.providerCode) return;
      setPvzSheetOpen(false);
      stopUserTracking();
      setPickup({
        externalId: point.externalId,
        providerCode: point.providerCode,
        address: point.addressLine || '',
        lat: point.lat,
        lon: point.lon,
        name: point.name,
        deliveryType: point.pickupPointType ?? null,
      });
      const mapped = await refreshQuote(point);
      if (mapped) {
        nextStep();
      }
    },
    [setPickup, stopUserTracking, refreshQuote, nextStep]
  );

  /* ── Render ── */

  const hasPickup = Boolean(pickup?.externalId);
  const isQuoting = quoteState.isLoading;

  return (
    <div className={styles.stepRoot}>
      <div className={styles.stepTitle}>3. Пункт выдачи</div>

      {hasPickup ? (
        <div className={stepStyles.selectedBanner}>
          <div className={stepStyles.selectedTitle}>
            {pickup.providerCode?.toUpperCase()} · {pickup.address || 'Точка выбрана'}
          </div>
          {quote ? (
            <div className={stepStyles.selectedSubtitle}>
              Доставка: {Math.floor((quote.deliveryAmount ?? 0) / 100)} ₽
              {quote.deliveryDaysMax ? ` · до ${quote.deliveryDaysMax} дн.` : ''}
            </div>
          ) : isQuoting ? (
            <div className={stepStyles.selectedSubtitle}>Рассчитываем стоимость…</div>
          ) : null}
          <button
            type="button"
            className={styles.secondaryBtn}
            onClick={() => {
              setPickup(null);
              setQuote(null);
            }}
          >
            Выбрать другой
          </button>
        </div>
      ) : null}

      <ProviderChips activeProvider={activeProvider} onSelectProvider={setActiveProvider} />

      <PickupModeToggle step={step} onSelectStep={setLocalStep} />

      {step === 'map' ? (
        <div className={stepStyles.mapWrap}>
          <div id="buy-now-pvz-map" className={stepStyles.mapHost} />
          {isPickupFetching ? (
            <div className={stepStyles.mapBadge}>Загружаем пункты выдачи…</div>
          ) : null}
          {geoError ? <div className={stepStyles.mapBadge}>{geoError}</div> : null}
          {Object.keys(providerErrors).length > 0 ? (
            <div className={stepStyles.mapBadge}>
              {Object.entries(providerErrors)
                .map(([code]) =>
                  code === 'cdek'
                    ? 'CDEK временно недоступен'
                    : code === 'yandex_delivery'
                      ? 'Яндекс Доставка временно недоступна'
                      : `${code}: ошибка`
                )
                .join(' · ')}
            </div>
          ) : null}
          <button
            type="button"
            className={stepStyles.geoButton}
            aria-pressed={isUserTracking}
            onClick={() => (isUserTracking ? stopUserTracking() : startUserTracking())}
          >
            {isUserTracking ? '⏸ Геолокация' : '📍 Моё местоположение'}
          </button>
        </div>
      ) : (
        <div className={stepStyles.listWrap}>
          <input
            type="search"
            placeholder="Адрес или название"
            value={listQuery}
            onChange={(e) => setListQuery(e.target.value)}
            className={stepStyles.listSearch}
          />
          {filteredPvz.length === 0 ? (
            <div className={styles.placeholder}>
              Ничего не найдено. Попробуйте сместить карту или сменить фильтр.
            </div>
          ) : (
            <div className={stepStyles.listScroll}>
              {filteredPvz.slice(0, 50).map((p) => (
                <button
                  key={p.id}
                  type="button"
                  className={stepStyles.listItem}
                  onClick={() => openPvzDetail(p.id)}
                >
                  <div className={stepStyles.listItemTitle}>
                    {p.providerLabel} · {p.pickupPointTypeLabel}
                  </div>
                  <div className={stepStyles.listItemSubtitle}>{p.addressLine}</div>
                  {p._distanceKm != null ? (
                    <div className={stepStyles.listItemDistance}>{p._distanceKm.toFixed(1)} км</div>
                  ) : null}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      <PvzDetailSheet
        open={pvzSheetOpen && Boolean(selectedPvz)}
        point={selectedPvz}
        onClose={() => setPvzSheetOpen(false)}
        onConfirm={handleConfirmPickup}
      />

      <button
        type="button"
        className={styles.primaryBtn}
        onClick={nextStep}
        disabled={!hasPickup || !quote || isQuoting}
      >
        {isQuoting ? 'Рассчитываем…' : 'К подтверждению'}
      </button>
    </div>
  );
}
