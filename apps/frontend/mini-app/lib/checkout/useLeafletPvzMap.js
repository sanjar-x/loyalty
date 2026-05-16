'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import { distanceKm } from './geo';
import { PVZ_PROVIDER_CODES } from './pvzProviders';
import { createPvzMarkerIcon } from './pvzMarkerIcon';

/**
 * Pickup sahifa Leaflet xaritasi — barcha imperativ map/cluster/marker
 * boshqaruvi + user geo tracking. Audit #1: `app/checkout/pickup/page.jsx`'dan
 * ajratildi (~450 satr, eng zich qism).
 *
 * Mas'uliyat sohalari:
 *  • Map shell init/destroy (CSS dinamik yuklash, tile, cluster, moveend listener)
 *  • Marker diff — kelayotgan `pvzPoints` bilan mavjud markerlar farqi
 *    (DOM rebuild qilinmaydi; cluster.addLayer/removeLayer)
 *  • Selected marker CSS class — `setIcon`'siz, 0 DOM rebuild
 *  • Provider filter visibility — addLayer/removeLayer toggling
 *  • Recenter — selected PVZ yoki URL lat/lon bo'yicha (auto-zoom-in only)
 *  • User geo tracking — `watchPosition` + circleMarker + accuracy circle
 *
 * **Marker click ↔ routing tsikli**: PVZ tanlanganda sahifa
 * `replacePickupUrl`/`setStep` + `stopUserTracking` chaqirishi kerak. Lekin
 * `stopUserTracking` bu hook ichida; cycle bo'lmasligi uchun sahifa
 * `onMarkerClickRef.current = selectPvzOnMap` qiladi va marker click handler
 * uni stable ref orqali o'qiydi.
 *
 * @param {{
 *   step: string,
 *   searchParamsKey: string,
 *   pvzPoints: any[],
 *   pvzPointById: Map<string, any>,
 *   activeProvider: string,
 *   selectedPvzId: string|null,
 *   setViewportArgs: (args: any) => void,
 *   onMarkerClickRef: import('react').RefObject<((pvzId: string) => void) | null>,
 * }} params
 */
export function useLeafletPvzMap({
  step,
  searchParamsKey,
  pvzPoints,
  pvzPointById,
  activeProvider,
  selectedPvzId,
  setViewportArgs,
  onMarkerClickRef,
}) {
  const leafletRef = useRef(null);
  const mapRef = useRef(null);
  const markerRef = useRef(null);
  const pvzClusterRef = useRef(null);
  const pvzMarkersRef = useRef(new Map());
  const pvzProviderByIdRef = useRef(new Map());
  const prevSelectedPvzIdRef = useRef(null);
  const userMarkerRef = useRef(null);
  const userAccuracyCircleRef = useRef(null);
  const geoWatchIdRef = useRef(null);
  const userEverCenteredRef = useRef(false);
  const initSeqRef = useRef(0);
  const iconFixedRef = useRef(false);

  const [isUserTracking, setIsUserTracking] = useState(false);
  const [geoError, setGeoError] = useState(null);
  const [userLocation, setUserLocation] = useState(null);
  const lastUserLocationRef = useRef(null);

  const stopUserTracking = useCallback(() => {
    if (geoWatchIdRef.current != null) {
      try {
        navigator.geolocation.clearWatch(geoWatchIdRef.current);
      } catch {}
      geoWatchIdRef.current = null;
    }

    try {
      userMarkerRef.current?.remove();
    } catch {
      // ignore
    }
    userMarkerRef.current = null;

    try {
      userAccuracyCircleRef.current?.remove();
    } catch {
      // ignore
    }
    userAccuracyCircleRef.current = null;

    userEverCenteredRef.current = false;
    lastUserLocationRef.current = null;
    setUserLocation(null);
    setIsUserTracking(false);
  }, []);

  const openPvzPopup = useCallback(
    (pvzId) => {
      const marker = pvzMarkersRef.current.get(pvzId);
      if (!marker) return;

      if (isUserTracking) return;

      const map = mapRef.current;
      const panToMarker = () => {
        if (!map) return;
        try {
          const latlng = marker.getLatLng?.();
          if (!latlng) return;
          map.panTo(latlng, { animate: true });
        } catch {
          // ignore
        }
      };

      const cluster = pvzClusterRef.current;

      const tryOpen = () => {
        panToMarker();
      };

      if (cluster?.zoomToShowLayer) {
        try {
          cluster.zoomToShowLayer(marker, tryOpen);
          return;
        } catch {
          // ignore and fallback
        }
      }

      tryOpen();
    },
    [isUserTracking]
  );

  // Provider filter bo'yicha marker'lar visibility'ini boshqarish.
  // Cluster'da `clearLayers + addLayers` o'rniga `addLayer/removeLayer`
  // bilan stable instances'ni saqlaymiz — DOM nodes qayta yaratilmaydi.
  useEffect(() => {
    if (step !== 'map') return;

    const cluster = pvzClusterRef.current;
    if (!cluster) return;

    const enabledProviders = new Set(
      activeProvider === 'all' ? PVZ_PROVIDER_CODES : [activeProvider]
    );

    // Safety: keep selected PVZ visible even if filter doesn't match.
    if (selectedPvzId) {
      const selectedProvider = pvzPointById.get(selectedPvzId)?.providerCode;
      if (selectedProvider) enabledProviders.add(selectedProvider);
    }

    for (const [id, marker] of pvzMarkersRef.current.entries()) {
      const provider = pvzProviderByIdRef.current.get(id);
      if (!provider) continue;
      const shouldShow = enabledProviders.has(provider);
      const isOnMap = cluster.hasLayer?.(marker) ?? false;
      if (shouldShow && !isOnMap) cluster.addLayer(marker);
      else if (!shouldShow && isOnMap) cluster.removeLayer(marker);
    }

    if (selectedPvzId) {
      requestAnimationFrame(() => openPvzPopup(selectedPvzId));
    }
  }, [openPvzPopup, activeProvider, pvzPointById, selectedPvzId, step]);

  const startUserTracking = () => {
    setGeoError(null);

    const L = leafletRef.current;
    const map = mapRef.current;

    if (!L || !map) {
      setGeoError('Карта ещё загружается');
      return;
    }

    if (typeof navigator === 'undefined' || !navigator.geolocation) {
      setGeoError('Геолокация недоступна в этом браузере');
      return;
    }

    // Ensure previous session is stopped
    stopUserTracking();
    setIsUserTracking(true);

    const watchId = navigator.geolocation.watchPosition(
      (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        const accuracy = Math.max(0, pos.coords.accuracy || 0);

        const latlng = [lat, lon];

        // Keep the latest user location for sorting PVZ list.
        const prev = lastUserLocationRef.current;
        const nextLoc = { lat, lon };
        // GPS can be noisy; avoid re-sorting PVZ list on tiny jitter.
        if (!prev || distanceKm(prev, nextLoc) > 0.03) {
          lastUserLocationRef.current = nextLoc;
          setUserLocation(nextLoc);
        }

        try {
          if (!userMarkerRef.current) {
            userMarkerRef.current = L.circleMarker(latlng, {
              radius: 6,
              color: '#111111',
              weight: 2,
              fillColor: '#111111',
              fillOpacity: 1,
            }).addTo(map);
          } else {
            // CircleMarker supports setLatLng
            userMarkerRef.current.setLatLng?.(latlng);
          }

          if (!userAccuracyCircleRef.current) {
            userAccuracyCircleRef.current = L.circle(latlng, {
              radius: accuracy,
              color: '#111111',
              weight: 1,
              opacity: 0.2,
              fillColor: '#111111',
              fillOpacity: 0.06,
            }).addTo(map);
          } else {
            userAccuracyCircleRef.current.setLatLng(latlng);
            userAccuracyCircleRef.current.setRadius(accuracy);
          }
        } catch {
          // ignore
        }

        // Follow user while tracking
        try {
          if (!userEverCenteredRef.current) {
            userEverCenteredRef.current = true;
            map.setView(latlng, Math.max(map.getZoom(), 14), { animate: true });
          } else {
            map.panTo(latlng, { animate: true });
          }
        } catch {
          // ignore
        }
      },
      (err) => {
        setGeoError(err.message || 'Не удалось получить геолокацию');
        stopUserTracking();
      },
      {
        enableHighAccuracy: true,
        maximumAge: 10_000,
      }
    );

    geoWatchIdRef.current = watchId;
  };

  const destroyMap = useCallback(() => {
    stopUserTracking();

    try {
      markerRef.current?.remove();
    } catch {
      // ignore
    }
    markerRef.current = null;

    try {
      pvzClusterRef.current?.remove();
    } catch {
      // ignore
    }
    pvzClusterRef.current = null;
    pvzMarkersRef.current.clear();
    pvzProviderByIdRef.current.clear();
    prevSelectedPvzIdRef.current = null;

    try {
      mapRef.current?.remove();
    } catch {
      // ignore
    }
    mapRef.current = null;
  }, [stopUserTracking]);

  /* ── Map init effect ── */
  useEffect(() => {
    if (step !== 'map') {
      destroyMap();
      return;
    }

    // If a map already exists, do not redo heavy init / imports.
    if (mapRef.current) return;

    const seq = ++initSeqRef.current;
    let cancelled = false;

    const init = async () => {
      // Load CSS dynamically to avoid blocking initial render
      await Promise.all([
        import('leaflet/dist/leaflet.css'),
        import('leaflet.markercluster/dist/MarkerCluster.css'),
        import('leaflet.markercluster/dist/MarkerCluster.Default.css'),
      ]);

      const leafletModule = await import('leaflet');
      const L = leafletModule.default ?? leafletModule;

      // Marker clustering plugin patches Leaflet with markerClusterGroup().
      await import('leaflet.markercluster');

      if (cancelled || initSeqRef.current !== seq) return;

      leafletRef.current = L;

      if (!iconFixedRef.current) {
        try {
          // Fix default marker icon paths under bundlers
          const icon2x = (await import('leaflet/dist/images/marker-icon-2x.png')).default;
          const icon1x = (await import('leaflet/dist/images/marker-icon.png')).default;
          const shadow = (await import('leaflet/dist/images/marker-shadow.png')).default;

          delete L.Icon.Default.prototype._getIconUrl;
          L.Icon.Default.mergeOptions({
            iconRetinaUrl: icon2x,
            iconUrl: icon1x,
            shadowUrl: shadow,
          });
        } catch {
          // ignore
        }

        iconFixedRef.current = true;
      }

      const el = document.getElementById('pickup-leaflet-map');
      if (!el) return;

      // If a map already exists, do not create a new one.
      if (mapRef.current) return;

      // Defensive: if some previous init left a leaflet id on the element.
      const anyEl = el;
      if (anyEl._leaflet_id) {
        try {
          delete anyEl._leaflet_id;
        } catch {
          anyEl._leaflet_id = undefined;
        }
      }

      const params = new URLSearchParams(searchParamsKey);

      // Map'ni initial center bilan ochamiz. Markerlar alohida effekt'da
      // backend response kelishi bilan qo'shiladi (data-driven).
      const urlLat = Number(params.get('lat'));
      const urlLon = Number(params.get('lon'));
      const urlHasCenter = Number.isFinite(urlLat) && Number.isFinite(urlLon);

      // CHK-016 Bug #2 edge case: agar URL'da lat/lon yo'q, lekin pvzId bor
      // (eski URL format yoki cache hit'dan kelgan), tanlangan PVZ koordinatasi
      // bo'yicha markazlanadi — Moskva default'iga otib yuborilmaydi.
      const urlPvzId = params.get('pvzId');
      const selectedPoint = urlPvzId ? pvzPointById.get(urlPvzId) : null;
      const fallbackHasPvz = selectedPoint?.lat != null && selectedPoint?.lon != null;

      const centerLat = urlHasCenter ? urlLat : fallbackHasPvz ? selectedPoint.lat : 55.751244;
      const centerLon = urlHasCenter ? urlLon : fallbackHasPvz ? selectedPoint.lon : 37.618423;

      const initialZoom = urlHasCenter || fallbackHasPvz ? 12 : 10;

      const map = L.map(el, {
        zoomControl: false,
        attributionControl: false,
      }).setView([centerLat, centerLon], initialZoom);

      mapRef.current = map;

      L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
        subdomains: 'abcd',
      }).addTo(map);

      const markerClusterGroupFactory = L.markerClusterGroup;

      const clusterGroup = markerClusterGroupFactory
        ? markerClusterGroupFactory({
            showCoverageOnHover: false,
            spiderfyOnMaxZoom: true,
            zoomToBoundsOnClick: true,
            maxClusterRadius: 52,
            chunkedLoading: true,
            iconCreateFunction: (cluster) => {
              const count = cluster.getChildCount();
              const size = count < 10 ? 34 : count < 100 ? 40 : 46;

              return L.divIcon({
                className: '',
                iconSize: [size, size],
                iconAnchor: [size / 2, size / 2],
                html: `<div style="
                  width:${size}px;
                  height:${size}px;
                  border-radius:9999px;
                  background: rgba(17,17,17,0.92);
                  color: #fff;
                  font-weight: 700;
                  font-size: 14px;
                  display:flex;
                  align-items:center;
                  justify-content:center;
                  box-shadow: 0 10px 24px rgba(0,0,0,0.20);
                  border: 2px solid rgba(255,255,255,0.8);
                ">${count}</div>`,
              });
            },
          })
        : L.layerGroup();

      pvzClusterRef.current = clusterGroup;
      clusterGroup.addTo(map);

      // Viewport-driven query: foydalanuvchi xaritani pan/zoom qilganda
      // yangi center+radius bilan qayta so'rov yuboramiz.
      // - Quantization: lat/lon 0.01° (~1km) gridga, radius 5km step'ga.
      //   Mikro-harakatlar takror fetch qilmaydi va RTKQ cache mosroq hit oladi.
      // - Debounce: 400ms — pan tugagandan keyin so'rov.
      // - Accumulator: yangi point'lar `pvzAccum`'ga merge qilinadi.
      const computeViewportArgs = () => {
        const center = map.getCenter();
        const bounds = map.getBounds();
        const ne = bounds.getNorthEast();
        const dKm = distanceKm({ lat: center.lat, lon: center.lng }, { lat: ne.lat, lon: ne.lng });
        const lat = Math.round(center.lat * 100) / 100;
        const lon = Math.round(center.lng * 100) / 100;
        const radiusKm = Math.min(100, Math.max(10, Math.ceil(dKm / 5) * 5));
        return { latitude: lat, longitude: lon, radiusKm };
      };

      let moveendTimer = 0;
      const onMoveEnd = () => {
        window.clearTimeout(moveendTimer);
        moveendTimer = window.setTimeout(() => {
          if (cancelled || initSeqRef.current !== seq) return;
          setViewportArgs(computeViewportArgs());
        }, 400);
      };
      map.on('moveend', onMoveEnd);

      // Initial viewport sync (bir tick'dan keyin bounds aniq bo'ladi)
      window.setTimeout(() => {
        if (cancelled || initSeqRef.current !== seq) return;
        setViewportArgs(computeViewportArgs());
      }, 0);

      // Cleanup: map.off + clearTimeout — bu callback init() async returns
      // qiladigan handle. destroyMap()'da listener avtomatik tushadi
      // (`map.remove()` barcha event'lardan tozalaydi), shu sabab faqat
      // timer'ni tozalaymiz (mapref'dan oldinroq tushishi mumkin).
      mapRef.current.__lmCleanupMoveend = () => {
        window.clearTimeout(moveendTimer);
      };

      // Markerlar alohida effekt'da yaratiladi (data-driven). Bu ish faqat
      // map mount paytida bo'ladi — center va cluster shell tayyor bo'ladi.
    };

    void init();

    return () => {
      cancelled = true;
      // Async init paytida cleanup chaqirilsa, moveend timer'ni tozalash
      try {
        mapRef.current?.__lmCleanupMoveend?.();
      } catch {
        // ignore
      }
    };
    // pvzPointById/setViewportArgs deps'da emas — original sahifada ham shu xil
    // (faqat step/searchParamsKey/destroyMap o'zgarganda map qayta init bo'lsin).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, searchParamsKey, destroyMap]);

  /* ── Marker diff effect ── */
  // Backend `pvzPoints` o'zgarganda markerlarni **diff** qilamiz:
  //   - mavjud va kelgan IDlardagi point — saqlanadi (DOM node qayta yaratilmaydi)
  //   - kelmagan ID — cluster'dan o'chiriladi va `pvzMarkersRef`'dan tozalanadi
  //   - yangi ID — L.marker yaratiladi va cluster'ga qo'shiladi
  // 500 PVZ × text-typing/filter — 0 ta DOM rebuild.
  useEffect(() => {
    if (step !== 'map') return;
    const L = leafletRef.current;
    const cluster = pvzClusterRef.current;
    if (!L || !cluster) return;

    const incomingIds = new Set(pvzPoints.map((p) => p.id));

    // 1) Eski markerlarni o'chirish
    for (const [id, marker] of pvzMarkersRef.current.entries()) {
      if (incomingIds.has(id)) continue;
      try {
        cluster.removeLayer?.(marker);
      } catch {
        // ignore
      }
      pvzMarkersRef.current.delete(id);
      pvzProviderByIdRef.current.delete(id);
    }

    // 2) Provider filter (selected ham doimo ko'rinishi kerak)
    const enabledProviders = new Set(
      activeProvider === 'all' ? PVZ_PROVIDER_CODES : [activeProvider]
    );
    if (selectedPvzId) {
      const sel = pvzPointById.get(selectedPvzId);
      if (sel?.providerCode) enabledProviders.add(sel.providerCode);
    }

    // 3) Yangi markerlarni yaratish (yoki existing'ga visibility qo'llash)
    const toAdd = [];
    for (const point of pvzPoints) {
      pvzProviderByIdRef.current.set(point.id, point.providerCode);
      const visible = enabledProviders.has(point.providerCode);

      let marker = pvzMarkersRef.current.get(point.id);
      if (!marker) {
        marker = L.marker([point.lat, point.lon], {
          icon: createPvzMarkerIcon(L, point.providerCode),
          keyboard: false,
          title: `${point.providerLabel} — ${point.addressLine}`,
        }).on('click', () => {
          // Cycle-breaking: sahifa `selectPvzOnMap`'ni ref'ga yozadi.
          onMarkerClickRef.current?.(point.id);
        });
        pvzMarkersRef.current.set(point.id, marker);
        if (visible) toAdd.push(marker);
      } else if (visible && !cluster.hasLayer?.(marker)) {
        toAdd.push(marker);
      } else if (!visible && cluster.hasLayer?.(marker)) {
        try {
          cluster.removeLayer(marker);
        } catch {
          // ignore
        }
      }
    }

    if (toAdd.length > 0) {
      if (cluster.addLayers) cluster.addLayers(toAdd);
      else for (const m of toAdd) cluster.addLayer(m);
    }

    if (selectedPvzId && pvzMarkersRef.current.get(selectedPvzId)) {
      requestAnimationFrame(() => openPvzPopup(selectedPvzId));
    }
    // `onMarkerClickRef` — stable ref'i, dep'da bo'lishi xulqqa ta'sir qilmaydi
    // (exhaustive-deps qoidasini qondirish uchun ro'yxatlangan).
  }, [
    step,
    pvzPoints,
    pvzPointById,
    activeProvider,
    selectedPvzId,
    openPvzPopup,
    onMarkerClickRef,
  ]);

  /* ── Selected marker CSS class ── */
  // CSS class qo'shamiz — `setIcon`'siz (8KB SVG HTML qayta render bo'lmaydi).
  useEffect(() => {
    if (step !== 'map') return;

    const prev = prevSelectedPvzIdRef.current;
    if (prev && prev !== selectedPvzId) {
      const prevMarker = pvzMarkersRef.current.get(prev);
      try {
        prevMarker?._icon?.classList.remove('pvz-selected');
      } catch {
        // ignore
      }
    }

    if (selectedPvzId) {
      const marker = pvzMarkersRef.current.get(selectedPvzId);
      try {
        marker?._icon?.classList.add('pvz-selected');
      } catch {
        // ignore
      }
    }

    prevSelectedPvzIdRef.current = selectedPvzId;
  }, [step, selectedPvzId]);

  /* ── Recenter on URL/selected change ── */
  useEffect(() => {
    if (step !== 'map') return;

    if (isUserTracking) return;

    const L = leafletRef.current;
    const map = mapRef.current;
    if (!L || !map) return;

    const params = new URLSearchParams(searchParamsKey);

    const selectedFromUrl = params.get('pvzId');
    const selectedPoint = selectedFromUrl ? pvzPointById.get(selectedFromUrl) : undefined;

    const urlLat = Number(params.get('lat'));
    const urlLon = Number(params.get('lon'));
    const urlHasCenter = Number.isFinite(urlLat) && Number.isFinite(urlLon);

    // When closing the PVZ modal we remove `pvzId`. In that case we must not
    // re-center the map to a default location; keep the current view.
    if (!selectedPoint && !urlHasCenter) return;

    const centerLat = selectedPoint?.lat ?? (urlHasCenter ? urlLat : 55.751244);
    const centerLon = selectedPoint?.lon ?? (urlHasCenter ? urlLon : 37.618423);

    const hasMarker = !selectedPoint && urlHasCenter;
    const hasSelectedPvz = Boolean(selectedPoint);

    // UX: never auto-zoom-out, only zoom-in when needed.
    const desiredZoom = hasSelectedPvz ? 14 : hasMarker ? 12 : 10;
    const currentCenter = map.getCenter();
    const currentZoom = map.getZoom();
    const eps = 1e-6;
    const needsMove =
      Math.abs(currentCenter.lat - centerLat) > eps ||
      Math.abs(currentCenter.lng - centerLon) > eps;
    const nextZoom = Math.max(currentZoom, desiredZoom);
    const needsZoomIn = currentZoom < nextZoom;

    if (needsMove || needsZoomIn) {
      map.setView([centerLat, centerLon], nextZoom, { animate: true });
    }

    if (hasSelectedPvz && selectedFromUrl) {
      openPvzPopup(selectedFromUrl);
    }
  }, [pvzPointById, openPvzPopup, step, searchParamsKey, isUserTracking]);

  /* ── Stop tracking on step change / unmount ── */
  useEffect(() => {
    if (step !== 'map') {
      stopUserTracking();
    }

    return () => {
      stopUserTracking();
    };
  }, [step, stopUserTracking]);

  return {
    startUserTracking,
    stopUserTracking,
    isUserTracking,
    geoError,
    userLocation,
  };
}
