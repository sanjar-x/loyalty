'use client';

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { cn } from '@/shared/lib/ui-utils';

import Button from '@/shared/ui/Button';
import Header from '@/widgets/Header';
import { PvzDetailSheet } from '@/features/pickup-selection';
import { useBackHandlerStore } from '@/features/telegram-api';
import { distanceKm } from '@/features/checkout-flow/lib/geo';
import { usePvzData } from '@/features/pickup-selection/model/usePvzData';
import { usePvzUrlState } from '@/features/pickup-selection/model/usePvzUrlState';
import { useAddressSuggest } from '@/features/checkout-flow/model/useAddressSuggest';
import { useLeafletPvzMap } from '@/features/pickup-selection/model/useLeafletPvzMap';

import ProviderChips from '@/features/pickup-selection/ui/ProviderChips';
import PickupModeToggle from '@/features/pickup-selection/ui/PickupModeToggle';
import styles from './page.module.css';

/**
 * `/checkout/pickup` — PVZ selection page (map / list / search steps).
 *
 * Audit #1 (god-component decomposition): this used to be a single
 * 1493-line file. Now it's an orchestrator:
 *  • pure helpers       → `lib/checkout/{geo,pvzProviders,pvzMarkerIcon}.js`
 *  • URL state          → `lib/checkout/usePvzUrlState.js`
 *  • PVZ data           → `lib/checkout/usePvzData.js`
 *  • Address suggest    → `lib/checkout/useAddressSuggest.js`
 *  • Leaflet imperative → `lib/checkout/useLeafletPvzMap.js` (the densest part)
 *  • presentation       → `./{ProviderChips,PickupModeToggle}.jsx`
 *
 * Marker click ↔ routing cycle: `useLeafletPvzMap` accepts `onMarkerClickRef`;
 * we write `selectPvzOnMap` to that ref via an effect — that way the page
 * glue can use the hook's `stopUserTracking`.
 */

export default function CheckoutPickupPage() {
  return (
    <Suspense fallback={<div className={styles.c1} />}>
      <CheckoutPickupPageInner />
    </Suspense>
  );
}

function CheckoutPickupPageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const searchParamsKey = searchParams.toString();

  // Ref to break the marker click → routing cycle (see the note above).
  const onMarkerClickRef = useRef(null);

  // PVZ data (viewport-driven query + accumulation).
  const {
    viewportArgs,
    setViewportArgs,
    pvzPoints,
    pvzPointById,
    providerErrors,
    isPickupFetching,
    isPickupError,
  } = usePvzData({ searchParamsKey });

  // URL state (step + selectedPvzId).
  const { step, setStep, selectedPvzId, replacePickupUrl, setStepAndUrl } = usePvzUrlState({
    searchParamsKey,
    router,
  });

  // Address suggest (search step).
  const { query, setQuery, setSuggestions, items } = useAddressSuggest();

  // PVZ list filter state.
  const [pvzQuery, setPvzQuery] = useState('');
  // "all" | "cdek" | "yandex_delivery"
  const [activeProvider, setActiveProvider] = useState('all');

  // Leaflet map subsystem.
  const { startUserTracking, stopUserTracking, isUserTracking, geoError, userLocation } =
    useLeafletPvzMap({
      step,
      searchParamsKey,
      pvzPoints,
      pvzPointById,
      activeProvider,
      selectedPvzId,
      setViewportArgs,
      onMarkerClickRef,
    });

  const selectedPvz = useMemo(() => {
    if (!selectedPvzId) return null;
    return pvzPointById.get(selectedPvzId) ?? null;
  }, [pvzPointById, selectedPvzId]);

  const [isPvzModalOpen, setIsPvzModalOpen] = useState(() => {
    const initialId = new URLSearchParams(searchParamsKey).get('pvzId');
    return Boolean(initialId && initialId.trim());
  });

  useEffect(() => {
    if (step === 'map' && selectedPvzId) {
      setIsPvzModalOpen(true);
    }
  }, [step, selectedPvzId]);

  // Distance pre-compute: when `userLocation` changes, Haversine is
  // computed once for each point and written to the `_distanceKm` field.
  // 500 PVZ × text-typing — a noticeable win.
  const pointsWithDistance = useMemo(() => {
    if (!userLocation) return pvzPoints;
    return pvzPoints.map((p) => ({
      ...p,
      _distanceKm: distanceKm(userLocation, { lat: p.lat, lon: p.lon }),
    }));
  }, [pvzPoints, userLocation]);

  const filteredPvz = useMemo(() => {
    if (step !== 'list') return [];

    const q = pvzQuery.trim().toLowerCase();
    const base = !q
      ? pointsWithDistance
      : pointsWithDistance.filter((x) => {
          const hay = `${x.providerLabel} ${x.addressLine}`.toLowerCase();
          return hay.includes(q);
        });

    const providerFiltered =
      activeProvider === 'all' ? base : base.filter((x) => x.providerCode === activeProvider);

    if (!userLocation) return providerFiltered;

    // O(n log n) sort, but the distance is already computed.
    return [...providerFiltered].sort(
      (a, b) => (a._distanceKm ?? Infinity) - (b._distanceKm ?? Infinity)
    );
  }, [pointsWithDistance, activeProvider, pvzQuery, step, userLocation]);

  /* ── Page glue: routing + PVZ selection ── */

  // CHK-016 Bug #2: when a PVZ is selected we KEEP lat/lon in the URL —
  // on refresh/back the map opens centered correctly and the
  // viewport-driven query immediately reloads PVZ around it.
  const selectPvzOnMap = useCallback(
    (pvzId) => {
      const selectedPoint = pvzPointById.get(pvzId);
      setIsPvzModalOpen(true);
      stopUserTracking();
      setStep('map');
      replacePickupUrl((params) => {
        params.set('step', 'map');
        params.set('pvzId', pvzId);
        if (selectedPoint?.lat != null && selectedPoint?.lon != null) {
          params.set('lat', String(selectedPoint.lat));
          params.set('lon', String(selectedPoint.lon));
          // Small radius around the selected PVZ — focus is on its center
          params.set('radius', '10');
        }
        // Keep `address` — used to show where the user is currently located
      });
    },
    [pvzPointById, replacePickupUrl, stopUserTracking, setStep]
  );

  // Passes `selectPvzOnMap` to `useLeafletPvzMap`'s marker click handler
  // via a ref — breaks the hook ↔ page cycle (the hook exposes
  // `stopUserTracking` and `selectPvzOnMap` calls it).
  useEffect(() => {
    onMarkerClickRef.current = selectPvzOnMap;
  }, [selectPvzOnMap]);

  // CHK-016 Bug #7: when the modal closes, remove pvzId from the URL.
  const closePvzModal = useCallback(() => {
    setIsPvzModalOpen(false);
    replacePickupUrl((params) => {
      params.delete('pvzId');
      // Keep lat/lon — the user is still in this area
    });
  }, [replacePickupUrl]);

  // CHK-019: step-aware "select PVZ" intent.
  //  • map step — the original selectPvzOnMap (writes lat/lon to URL and opens the modal)
  //  • list step — modal-only (don't jump to the map, the step is preserved)
  const openPvzDetail = useCallback(
    (pvzId) => {
      if (step === 'map') {
        selectPvzOnMap(pvzId);
        return;
      }
      setIsPvzModalOpen(true);
      replacePickupUrl((params) => {
        params.set('pvzId', pvzId);
        // The list step is preserved
      });
    },
    [step, selectPvzOnMap, replacePickupUrl]
  );

  // CHK-019: single "Доставить сюда" handler.
  const handleConfirmPvz = useCallback(
    (point) => {
      if (!point?.externalId || !point?.providerCode) return;
      const params = new URLSearchParams();
      params.set('pickupPvzId', point.externalId);
      params.set('pickupProvider', point.providerCode);
      params.set('pickupAddress', point.addressLine || '');
      if (point.lat != null && point.lon != null) {
        params.set('pickupLat', String(point.lat));
        params.set('pickupLon', String(point.lon));
      }
      router.push(`/checkout?${params.toString()}`);
    },
    [router]
  );

  // CHK-016 Bug #1/#5: step-based back. The Telegram BackButton and the
  // Header close button trigger this intent — a logical "one step back"
  // instead of a history pop.
  const onPickupBack = useCallback(() => {
    if (step === 'map' || step === 'list') {
      replacePickupUrl((params) => {
        params.set('step', 'search');
        params.delete('pvzId');
        // Keep lat/lon — after search the user may come back to the map
      });
      setStep('search');
      return;
    }
    router.push('/checkout');
  }, [step, replacePickupUrl, router, setStep]);

  const setPickupBack = useBackHandlerStore((s) => s.setPickupBack);
  const clearPickupBack = useBackHandlerStore((s) => s.clearPickupBack);
  useEffect(() => {
    setPickupBack(onPickupBack);
    return () => clearPickupBack();
  }, [onPickupBack, setPickupBack, clearPickupBack]);

  /* ── Render: the 3-step branch ── */

  if (step === 'map') {
    return (
      <div className={styles.c16}>
        <Header title="Оформление заказа" showClose onClose={onPickupBack} hideOnTelegram />

        <div className={cn(styles.c17, styles.tw10)}>
          <div id="pickup-leaflet-map" className={styles.c18} />

          {/* CHK-016 Bug #4: if viewportArgs is null, prompt the user. */}
          {!viewportArgs ? (
            <div className={styles.mapBootstrap}>
              <div className={styles.mapBootstrapTitle}>Укажите адрес или включите геолокацию</div>
              <div className={styles.mapBootstrapActions}>
                <Button variant="primary" onClick={() => setStepAndUrl('search')}>
                  Поиск города
                </Button>
                <Button variant="secondary" onClick={startUserTracking}>
                  Моё местоположение
                </Button>
              </div>
            </div>
          ) : null}

          {/* PVZ loading overlay loader */}
          {isPickupFetching ? (
            <div className={styles.pickupLoading}>
              <span className={styles.pickupLoadingDot} />
              Загружаем пункты выдачи…
            </div>
          ) : null}

          <button
            type="button"
            aria-label="Определить моё местоположение"
            aria-pressed={isUserTracking}
            onClick={() => (isUserTracking ? stopUserTracking() : startUserTracking())}
            // Hide the geo button when the PVZ modal is open (z-index conflict).
            style={{ display: selectedPvz && isPvzModalOpen ? 'none' : undefined }}
            className={cn(styles.geoButton, isUserTracking && styles.geoButtonActive)}
          >
            <svg
              width="22"
              height="22"
              viewBox="0 0 22 22"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M21.4566 0.373774C21.6762 0.59353 21.7407 0.924882 21.6202 1.21139L13.2144 21.2113C13.0858 21.5172 12.775 21.7044 12.4444 21.6761C12.2602 21.6603 12.0931 21.5802 11.9686 21.4558C11.8697 21.3568 11.7973 21.2302 11.7642 21.087L9.69747 12.1315L0.743318 10.0661C0.419889 9.9914 0.18136 9.71645 0.152911 9.38593C0.124616 9.0553 0.313079 8.74455 0.619021 8.61599L20.619 0.210118C20.9055 0.0896715 21.2368 0.154019 21.4566 0.373774ZM3.39566 9.10696L10.5075 10.7497C10.65 10.7826 10.7768 10.8547 10.8762 10.9541C10.9756 11.0536 11.0477 11.1804 11.0806 11.3229L12.7227 18.434L19.4851 2.34525L3.39566 9.10696Z"
                fill="black"
                stroke="black"
                strokeWidth="0.3"
              />
            </svg>
          </button>

          {geoError ? (
            <div className={cn(styles.c19, styles.tw11)}>
              <div className={cn(styles.c20, styles.tw12)}>{geoError}</div>
            </div>
          ) : null}

          {/* Per-provider degradation: if one provider is degraded,
              markers from the remaining providers are still visible. */}
          {Object.keys(providerErrors).length > 0 ? (
            <div className={cn(styles.c19, styles.tw11)}>
              <div className={cn(styles.c20, styles.tw12)}>
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
            </div>
          ) : null}

          {isPickupError ? (
            <div className={cn(styles.c19, styles.tw11)}>
              <div className={cn(styles.c20, styles.tw12)}>Не удалось загрузить пункты выдачи</div>
            </div>
          ) : null}

          <div className={cn(styles.c21, styles.tw13)}>
            <div className={cn(styles.c22, styles.tw14)}>
              <PickupModeToggle step={step} onSelectStep={setStepAndUrl} />
            </div>
          </div>
        </div>

        <PvzDetailSheet
          open={isPvzModalOpen && Boolean(selectedPvz)}
          point={selectedPvz}
          onClose={closePvzModal}
          onConfirm={handleConfirmPvz}
        />

        {selectedPvz && isPvzModalOpen ? null : (
          <div className={cn(styles.c58, styles.tw38, styles.leftHalf)}>
            <div className={styles.c59}>
              <ProviderChips activeProvider={activeProvider} onSelectProvider={setActiveProvider} />
            </div>
            <Button
              type="button"
              variant="primary"
              size="lg"
              className={styles.c60}
              onClick={() => setStepAndUrl('search')}
            >
              Поиск города
            </Button>
          </div>
        )}
      </div>
    );
  }

  if (step === 'search') {
    return (
      <div className={styles.c61}>
        <div className={styles.c62}>
          <div className={cn(styles.c63, styles.tw39)}>
            <img
              src="/icons/global/Search.svg"
              alt="search"
              className={cn(styles.c64, styles.tw40)}
            />
            <input
              value={query}
              onChange={(e) => {
                const next = e.target.value;
                setQuery(next);
                if (!next.trim()) {
                  setSuggestions([]);
                }
              }}
              className={cn(styles.c65, styles.tw41)}
              placeholder="Адрес"
            />
            {query.length > 0 ? (
              <button
                type="button"
                onClick={() => {
                  setQuery('');
                  setSuggestions([]);
                }}
                className={cn(styles.c66, styles.tw42)}
                aria-label="Clear"
              >
                <img
                  src="/icons/global/xicon.svg"
                  alt="clear"
                  className={cn(styles.c67, styles.tw43)}
                />
              </button>
            ) : null}
          </div>
        </div>

        <div className={styles.c68}>
          {items.map((p, idx) => (
            <button
              type="button"
              key={p.id}
              onClick={() => {
                stopUserTracking();
                const params = new URLSearchParams();
                params.set('step', 'map');
                params.set('address', p.title);
                if (p.lat != null) params.set('lat', String(p.lat));
                if (p.lon != null) params.set('lon', String(p.lon));
                // radius_km=10 (default) — for the backend bounding box.
                if (p.lat != null && p.lon != null) params.set('radius', '10');

                router.replace(`/checkout/pickup?${params.toString()}`);
                setStep('map');
              }}
              className={cn(
                styles.searchItem,
                idx === items.length - 1 ? null : styles.searchItemBorder
              )}
            >
              <img
                src="/icons/global/locationGrey.svg"
                alt="location"
                className={cn(styles.c69, styles.tw44)}
              />
              <div className={cn(styles.c70, styles.tw45)}>
                <div className={styles.c71}>{p.title}</div>
                {p.subtitle ? <div className={styles.c72}>{p.subtitle}</div> : null}
              </div>
            </button>
          ))}

          {query.trim() && items.length === 0 ? (
            <div className={styles.c73}>Ничего не найдено</div>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <div className={styles.c74}>
      <Header title="Оформление заказа" showClose onClose={onPickupBack} hideOnTelegram />
      <div className={styles.c75}>
        <div className={styles.c76}>
          <PickupModeToggle step={step} onSelectStep={setStepAndUrl} />
        </div>
        <div className={cn(styles.c77, styles.tw46)}>
          <img
            src="/icons/global/Search.svg"
            alt="search"
            className={cn(styles.c78, styles.tw47)}
          />
          <input
            value={pvzQuery}
            onChange={(e) => setPvzQuery(e.target.value)}
            className={cn(styles.c79, styles.tw48)}
            placeholder="Адрес"
          />
          {pvzQuery.length > 0 ? (
            <button
              type="button"
              onClick={() => setPvzQuery('')}
              className={cn(styles.c80, styles.tw49)}
              aria-label="Clear"
            >
              <img
                src="/icons/global/xicon.svg"
                alt="clear"
                className={cn(styles.c81, styles.tw50)}
              />
            </button>
          ) : null}
        </div>
      </div>

      <div className={styles.c82}>
        {filteredPvz.map((p, idx) => {
          const isActive = selectedPvzId === p.id;

          return (
            <button
              type="button"
              key={p.id}
              aria-pressed={isActive}
              onClick={() => {
                // CHK-019: in the list step we don't jump to the map —
                // the detail sheet opens and the step is preserved.
                openPvzDetail(p.id);
              }}
              className={cn(
                styles.pvzListItem,
                isActive ? styles.pvzListItemActive : styles.pvzListItemInactive,
                idx === filteredPvz.length - 1 ? null : styles.pvzListItemBorder
              )}
            >
              <div className={cn(styles.c83, styles.tw51)}>
                <div className={cn(styles.c84)}>
                  {p.providerLabel}
                  {p.pickupPointTypeLabel ? ` · ${p.pickupPointTypeLabel}` : ''}
                </div>
                <div className={styles.c85}>{p.addressLine}</div>
                {p.workSchedule ? <div className={styles.c86}>{p.workSchedule}</div> : null}
              </div>
            </button>
          );
        })}

        {filteredPvz.length === 0 && !isPickupFetching ? (
          <div className={styles.emptyState}>
            {viewportArgs ? (
              <>
                <div className={styles.emptyTitle}>В этом районе нет пунктов выдачи</div>
                <div className={styles.emptySubtitle}>
                  Попробуйте другой район или включите геолокацию
                </div>
              </>
            ) : (
              <>
                <div className={styles.emptyTitle}>Укажите адрес или включите геолокацию</div>
                <div className={styles.emptyActions}>
                  <Button variant="primary" onClick={() => setStepAndUrl('search')}>
                    Поиск города
                  </Button>
                  <Button variant="secondary" onClick={startUserTracking}>
                    Моё местоположение
                  </Button>
                </div>
              </>
            )}
          </div>
        ) : null}

        {isPickupFetching ? <div className={styles.c88}>Загружаем пункты выдачи…</div> : null}
      </div>

      {/* CHK-019: detail sheet on the list step too — we don't jump to the map */}
      <PvzDetailSheet
        open={isPvzModalOpen && Boolean(selectedPvz)}
        point={selectedPvz}
        onClose={closePvzModal}
        onConfirm={handleConfirmPvz}
      />
    </div>
  );
}
