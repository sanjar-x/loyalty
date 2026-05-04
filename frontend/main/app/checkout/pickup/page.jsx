"use client";

import React, {
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
/* Leaflet CSS is loaded dynamically in initMap() to avoid blocking initial render */
import Button from "@/components/ui/Button";
import Header from "@/components/layout/Header";
import {
  Clock,
  CreditCard,
  MapPin,
  Phone,
} from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import styles from "./page.module.css";
import cn from "clsx";

import { useListPickupPointsQuery } from "@/lib/store/api";
import { parsePickupCompoundId } from "@/lib/format/mapPickupPoints";

/**
 * @typedef {Object} GeoSuggestResponse
 * @property {{ value?: string, data?: { geo_lat?: (number|null), geo_lon?: (number|null), region_with_type?: string, city_with_type?: string, settlement_with_type?: (string|null), area_with_type?: (string|null), country?: string, subdivision_code?: (string|null) } }[]=} suggestions
 *
 * @typedef {{ id: string, title: string, subtitle: string, lat: (number|null), lon: (number|null) }} SuggestItem
 * @typedef {{ lat: number, lon: number }} LatLon
 */

function distanceKm(a, b) {
  const R = 6371;
  const toRad = (deg) => (deg * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat);
  const dLon = toRad(b.lon - a.lon);
  const lat1 = toRad(a.lat);
  const lat2 = toRad(b.lat);
  const sinDLat = Math.sin(dLat / 2);
  const sinDLon = Math.sin(dLon / 2);
  const h =
    sinDLat * sinDLat + Math.cos(lat1) * Math.cos(lat2) * sinDLon * sinDLon;
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(h)));
}

// Backend qo'llab-quvvatlaydigan provider'lar — `openapi.json` enum'i.
// (Boxberry, Pochta Rossii hozircha qo'llab-quvvatlanmaydi.)
const PVZ_PROVIDERS = [
  { code: "cdek", label: "CDEK", short: "CDEK" },
  { code: "yandex_delivery", label: "Яндекс Доставка", short: "Яндекс" },
];
const PVZ_PROVIDER_CODES = PVZ_PROVIDERS.map((p) => p.code);

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

  // Backend query argumentlari URL params'dan derive qilinadi:
  //   ?lat=55&lon=37&radius=50  (geolokatsiya yoki search'dan tanlangan shahar coords)
  //   ?city=Moskva              (geolokatsiya yo'q bo'lganda fallback)
  //
  // Default radius 50km (oldin 10km edi) — yirik shaharlar (Moskva, SPb)
  // metropoliya zonasini qoplaydi. Backend max=100km, so'rov boshlanishida
  // shu yetadi; foydalanuvchi xaritani pan qilganda viewport-driven query
  // yangilanadi (pastdagi `viewportArgs` state).
  const initialPickupArgs = useMemo(() => {
    const params = new URLSearchParams(searchParamsKey);
    const latStr = params.get("lat");
    const lonStr = params.get("lon");
    const lat = latStr != null ? Number(latStr) : NaN;
    const lon = lonStr != null ? Number(lonStr) : NaN;
    if (Number.isFinite(lat) && Number.isFinite(lon)) {
      const radiusStr = params.get("radius");
      const radiusKm = radiusStr ? Number(radiusStr) : 50;
      return {
        latitude: lat,
        longitude: lon,
        radiusKm: Number.isFinite(radiusKm) ? radiusKm : 50,
      };
    }
    const city = params.get("city");
    if (city && city.trim()) {
      return { city: city.trim(), countryCode: "RU" };
    }
    return null;
  }, [searchParamsKey]);

  // Viewport-driven query args: xaritani pan/zoom qilinganda yangilanadi.
  // Initial — URL'dan; keyin map `moveend` event listener'i o'zgartiradi.
  const [viewportArgs, setViewportArgs] = useState(initialPickupArgs);

  // URL search/initial argument o'zgarganda viewportArgs'ni qayta sync qilamiz
  // (foydalanuvchi yangi shahar tanlasa map shu hududga ko'chadi va query ham
  // yangilanadi). RTKQ cache hit'iga e'tibor bering — bir xil quantized
  // qiymat'lar takror fetch qilmaydi.
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

  // Accumulated PVZ map: barcha viewport so'rovlaridan kelgan point'lar
  // id bo'yicha mergetilgan. Foydalanuvchi xaritani pan qilib qaytsa,
  // eski markerlar yo'qolmaydi va `pvzMarkersRef` diff strategiyasi
  // ularni saqlab qoladi.
  //
  // Eslatma: bir sessiya ichida 1000+ PVZ bo'lsa ham marker cluster va
  // CSS `display:none` orqali render qilinadi — xotira foydalanishi xavfsiz.
  const [pvzAccum, setPvzAccum] = useState(() => new Map());

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

  const pvzPoints = useMemo(
    () => Array.from(pvzAccum.values()),
    [pvzAccum],
  );
  const providerErrors = pickupData?.errors ?? {};

  const pvzPointById = pvzAccum;

  const initialStep = useMemo(() => {
    const step = new URLSearchParams(searchParamsKey).get("step");
    if (step === "map" || step === "list" || step === "search") return step;
    return "search";
  }, [searchParamsKey]);

  const [step, setStep] = useState(initialStep);

  useEffect(() => {
    setStep(initialStep);
  }, [initialStep]);

  const [pvzQuery, setPvzQuery] = useState("");

  // "all" | "cdek" | "yandex_delivery"
  const [activeProvider, setActiveProvider] = useState("all");

  const selectedPvzId = useMemo(() => {
    const id = new URLSearchParams(searchParamsKey).get("pvzId");
    return id && id.trim() ? id : null;
  }, [searchParamsKey]);

  const selectedPvz = useMemo(() => {
    if (!selectedPvzId) return null;
    return pvzPointById.get(selectedPvzId) ?? null;
  }, [pvzPointById, selectedPvzId]);

  const [isPvzModalOpen, setIsPvzModalOpen] = useState(() => {
    const initialId = new URLSearchParams(searchParamsKey).get("pvzId");
    return Boolean(initialId && initialId.trim());
  });

  useEffect(() => {
    if (step === "map" && selectedPvzId) {
      setIsPvzModalOpen(true);
    }
  }, [step, selectedPvzId]);

  const [isUserTracking, setIsUserTracking] = useState(false);
  const [geoError, setGeoError] = useState(null);
  const [userLocation, setUserLocation] = useState(null);
  const lastUserLocationRef = useRef(null);

  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState([]);

  useEffect(() => {
    const q = query.trim();
    if (!q) {
      setSuggestions([]);
      return;
    }

    const ctrl = new AbortController();

    const t = window.setTimeout(async () => {
      try {
        const res = await fetch("/api/geo/suggest/address", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: q, count: 10 }),
          signal: ctrl.signal,
        });

        if (!res.ok) {
          setSuggestions([]);
          return;
        }

        const data = await res.json();
        const s = data?.suggestions;
        setSuggestions(Array.isArray(s) ? s : []);
      } catch {
        if (ctrl.signal.aborted) return;
        setSuggestions([]);
      }
    }, 250);

    return () => {
      window.clearTimeout(t);
      ctrl.abort();
    };
  }, [query]);

  const items = useMemo(() => {
    if (!query.trim()) return [];
    if (suggestions.length === 0) return [];

    return suggestions.map((x, index) => {
      const d = x.data;
      const subtitle =
        d?.city_with_type ||
        d?.settlement_with_type ||
        d?.area_with_type ||
        d?.country ||
        "";

      const latRaw = d?.geo_lat ?? null;
      const lonRaw = d?.geo_lon ?? null;
      const lat = latRaw == null ? null : Number(latRaw);
      const lon = lonRaw == null ? null : Number(lonRaw);

      return {
        id: `geo-${d?.subdivision_code || index}`,
        title: x.value || query,
        subtitle,
        lat: Number.isFinite(lat) ? lat : null,
        lon: Number.isFinite(lon) ? lon : null,
      };
    });
  }, [query, suggestions]);

  const replacePickupUrl = useCallback(
    (update) => {
      const params = new URLSearchParams(searchParamsKey);
      update(params);
      router.replace(`/checkout/pickup?${params.toString()}`);
    },
    [router, searchParamsKey],
  );

  const setStepAndUrl = (next) => {
    setStep(next);
    replacePickupUrl((params) => {
      params.set("step", next);
    });
  };

  // Distance pre-compute: `userLocation` o'zgarganda har bir point uchun
  // bir martagina Haversine hisoblanadi va `_distanceKm` maydoniga yoziladi.
  // `pvzQuery`/`activeProvider`/`step` o'zgarishlarida sort qayta hisoblansa
  // ham trig chaqiriqlari yo'q. 500 PVZ × text-typing — sezilarli yutuq.
  const pointsWithDistance = useMemo(() => {
    if (!userLocation) return pvzPoints;
    return pvzPoints.map((p) => ({
      ...p,
      _distanceKm: distanceKm(userLocation, { lat: p.lat, lon: p.lon }),
    }));
  }, [pvzPoints, userLocation]);

  const filteredPvz = useMemo(() => {
    if (step !== "list") return [];

    const q = pvzQuery.trim().toLowerCase();
    const base = !q
      ? pointsWithDistance
      : pointsWithDistance.filter((x) => {
          const hay = `${x.providerLabel} ${x.addressLine}`.toLowerCase();
          return hay.includes(q);
        });

    const providerFiltered =
      activeProvider === "all"
        ? base
        : base.filter((x) => x.providerCode === activeProvider);

    if (!userLocation) return providerFiltered;

    // O(n log n) sort, lekin distance allaqachon hisoblangan.
    return [...providerFiltered].sort(
      (a, b) => (a._distanceKm ?? Infinity) - (b._distanceKm ?? Infinity),
    );
  }, [pointsWithDistance, activeProvider, pvzQuery, step, userLocation]);

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

  const selectPvzOnMap = useCallback(
    (pvzId) => {
      setIsPvzModalOpen(true);
      stopUserTracking();
      setStep("map");
      replacePickupUrl((params) => {
        params.set("step", "map");
        params.set("pvzId", pvzId);
        params.delete("address");
        params.delete("lat");
        params.delete("lon");
      });
    },
    [replacePickupUrl, stopUserTracking],
  );

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
    [isUserTracking],
  );

  // Provider filter bo'yicha marker'lar visibility'ini boshqarish.
  // Cluster'da `clearLayers + addLayers` o'rniga `addLayer/removeLayer`
  // bilan stable instances'ni saqlaymiz — DOM nodes qayta yaratilmaydi.
  useEffect(() => {
    if (step !== "map") return;

    const cluster = pvzClusterRef.current;
    if (!cluster) return;

    const enabledProviders = new Set(
      activeProvider === "all" ? PVZ_PROVIDER_CODES : [activeProvider],
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
      setGeoError("Карта ещё загружается");
      return;
    }

    if (typeof navigator === "undefined" || !navigator.geolocation) {
      setGeoError("Геолокация недоступна в этом браузере");
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
              color: "#111111",
              weight: 2,
              fillColor: "#111111",
              fillOpacity: 1,
            }).addTo(map);
          } else {
            // CircleMarker supports setLatLng
            userMarkerRef.current.setLatLng?.(latlng);
          }

          if (!userAccuracyCircleRef.current) {
            userAccuracyCircleRef.current = L.circle(latlng, {
              radius: accuracy,
              color: "#111111",
              weight: 1,
              opacity: 0.2,
              fillColor: "#111111",
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
        setGeoError(err.message || "Не удалось получить геолокацию");
        stopUserTracking();
      },
      {
        enableHighAccuracy: true,
        maximumAge: 10_000,
      },
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

  // Marker ikonkasi tanlangan/tanlanmagan holatga qarab CSS orqali boshqariladi.
  // Selected state'i provider va selection'ga qarab `setIcon`'ni qayta chaqirmaydi —
  // shunchaki `<div>`'ga `pvz-selected` class qo'shilsa kifoya. SVG bir xil — width
  // CSS'da boshqariladi.
  //
  // CSS .pvz-selected'ni qo'shish kerak bo'ladi (`page.module.css` yoki global).
  // Bu yerda HTML faqat bir marta yaratiladi va keyin uni o'zgartirmaymiz —
  // 500 marker × selection-toggle uchun 0 ta `setIcon` chaqirig'i.
  const getPvzMarkerIcon = useCallback((L, provider) => {
    const bubble = 48;
    const tail = 14;
    const border = 2;
    const totalH = bubble + Math.floor(tail / 2);

    const iconHtml = (() => {
      switch (provider) {
        case "cdek":
          return `
            <svg width=${bubble} viewBox="0 0 55 65" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M27.127 1C41.5361 1 53.2606 12.7233 53.2607 27.127C53.2607 37.2436 47.341 46.5399 38.1758 50.8154C35.1511 52.2259 32.5883 54.7621 30.9814 57.9814L30.9805 57.9824L28.6836 62.5781C28.3908 63.1637 27.7905 63.5381 27.127 63.5381C26.4615 63.538 25.8751 63.1576 25.5801 62.5947L25.5752 62.5859L23.2734 57.9824V57.9814C21.7669 54.9632 19.4198 52.5454 16.6445 51.0928L16.084 50.8154C6.9189 46.54 1 37.2435 1 27.127C1.00013 12.7237 12.7175 1.00013 27.127 1Z" fill="#2D2D2D" stroke="white" stroke-width="2"/>
<path d="M18.1689 18.0692C18.0669 18.0247 17.9539 18 17.8352 18C17.3739 18 17 18.3739 17 18.8351C17 18.9686 17.0314 19.0944 17.0869 19.2061L17.0846 19.2088C18.1151 21.6694 19.2981 23.4658 20.2969 25.0282C18.8804 28.1752 18.1198 31.5479 17.5311 34.9918L17.5288 35.0051C17.5221 35.0489 17.5181 35.0937 17.5181 35.1395C17.5181 35.6009 17.892 35.9747 18.3532 35.9747C18.6382 35.9747 18.8894 35.8322 19.0402 35.6148L19.0409 35.6138C19.0512 35.599 19.0602 35.5841 19.0695 35.5688L19.0706 35.567C19.3998 35.0573 19.7657 34.5501 20.1209 34.0609C24.9094 27.4992 31.091 23.8532 38.494 21.1915C38.8563 21.0998 39.1239 20.772 39.1239 20.3818C39.1239 19.9205 38.7503 19.5469 38.2888 19.5469H38.2674L38.2629 19.5472C33.7828 19.578 29.9207 19.673 26.3935 19.5392C24.0635 19.4576 21.909 19.1308 19.7995 18.6074C19.2827 18.481 18.68 18.2706 18.1703 18.0679L18.1689 18.0692Z" fill="white"/>
<path d="M20.8751 39.1188C20.9035 39.0802 20.9286 39.0386 20.9504 38.9956C25.7854 31.022 31.6051 27.2918 39.7944 24.3636C39.814 24.3576 39.8329 24.3506 39.8517 24.3432L39.8574 24.3409C40.1617 24.2164 40.3765 23.9171 40.3765 23.5679C40.3765 23.1066 40.0025 22.7327 39.5413 22.7327C39.4741 22.7327 39.4089 22.7407 39.3459 22.7558H39.3449C39.2852 22.7702 39.2283 22.7913 39.1744 22.8177C31.1931 25.6954 25.0232 29.5542 20.1691 37.0769L19.4877 38.1922L19.4851 38.1966C19.4098 38.3219 19.3667 38.4681 19.3667 38.6251C19.3667 39.0863 19.7406 39.4603 20.2015 39.4603C20.4781 39.4603 20.7233 39.3252 20.8751 39.1188Z" fill="white"/>
</svg>
            `;
        case "yandex_delivery":
          return `
            <svg width=${bubble} viewBox="0 0 55 65" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M27.127 1C41.5361 1 53.2606 12.7233 53.2607 27.127C53.2607 37.2436 47.341 46.5399 38.1758 50.8154C35.1511 52.2259 32.5883 54.7621 30.9814 57.9814L30.9805 57.9824L28.6836 62.5781C28.3908 63.1637 27.7905 63.5381 27.127 63.5381C26.4615 63.538 25.8751 63.1576 25.5801 62.5947L25.5752 62.5859L23.2734 57.9824V57.9814C21.7669 54.9632 19.4198 52.5454 16.6445 51.0928L16.084 50.8154C6.9189 46.54 1 37.2435 1 27.127C1.00013 12.7237 12.7175 1.00013 27.127 1Z" fill="#2D2D2D" stroke="white" stroke-width="2"/>
<rect x="18.9238" y="17.769" width="16.1538" height="20.7692" fill="white"/>
<path fill-rule="evenodd" clip-rule="evenodd" d="M24.8087 12.0687C21.5952 12.5772 18.8776 13.9373 16.5004 16.227C14.3872 18.2626 13.1385 20.4245 12.2964 23.5051C11.8696 25.0669 11.9114 29.0769 12.3722 30.7556C14.534 38.6318 22.3557 43.3875 30.272 41.6387C32.9582 41.0452 35.2534 39.7952 37.3522 37.7823C43.4456 31.9389 43.5626 22.392 37.6143 16.4C35.7688 14.5409 33.253 13.0839 30.7402 12.4191C29.5099 12.0936 25.9724 11.8847 24.8087 12.0687ZM32.067 27.0914V35.9791H30.5061H28.9452V28.1645V20.3497L27.5793 20.4537C24.8978 20.6576 23.7159 21.7009 23.7486 23.8347C23.7589 24.499 23.8748 25.121 24.0686 25.5546C24.4167 26.3323 25.6149 27.5108 27.033 28.4701C27.5697 28.8331 28.0045 29.18 27.9995 29.2411C27.9945 29.3022 26.9937 30.8258 25.7752 32.6267L23.5599 35.9011L21.96 35.9456C20.9799 35.9728 20.36 35.9303 20.36 35.8359C20.36 35.7511 21.2312 34.3969 22.296 32.8264L24.2319 29.9713L23.0056 28.8379C22.0873 27.9892 21.65 27.4422 21.2647 26.6606C20.7816 25.6804 20.7502 25.5165 20.7502 23.9762C20.7502 22.532 20.7991 22.2315 21.1592 21.4647C21.6916 20.3303 22.5202 19.5194 23.7191 18.959C25.0839 18.3209 25.6697 18.24 29.0622 18.2208L32.067 18.2037V27.0914Z" fill="#2D2D2D"/>
</svg>
            `;
        default:
          return "";
      }
    })();

    return L.divIcon({
      className: "pvz-div-icon",
      iconSize: [bubble, totalH],
      iconAnchor: [bubble / 2, totalH],
      html: `
          <div style="position:relative; width:${bubble}px; height:${totalH}px;">
            <div style="
              position:absolute;
              left:0;
              top:0;
              width:${bubble + border}px;
              height:${bubble + border}px;
              display:flex;
              align-items:center;
              justify-content:center;
            ">
              <div style="display:flex; align-items:center; justify-content:center;">
                ${iconHtml}
              </div>
            </div>
          </div>
        `,
    });
  }, []);

  useEffect(() => {
    if (step !== "map") {
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
        import("leaflet/dist/leaflet.css"),
        import("leaflet.markercluster/dist/MarkerCluster.css"),
        import("leaflet.markercluster/dist/MarkerCluster.Default.css"),
      ]);

      const leafletModule = await import("leaflet");
      const L = leafletModule.default ?? leafletModule;

      // Marker clustering plugin patches Leaflet with markerClusterGroup().
      await import("leaflet.markercluster");

      if (cancelled || initSeqRef.current !== seq) return;

      leafletRef.current = L;

      if (!iconFixedRef.current) {
        try {
          // Fix default marker icon paths under bundlers
          const icon2x = (
            await import("leaflet/dist/images/marker-icon-2x.png")
          ).default;
          const icon1x = (await import("leaflet/dist/images/marker-icon.png"))
            .default;
          const shadow = (await import("leaflet/dist/images/marker-shadow.png"))
            .default;

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

      const el = document.getElementById("pickup-leaflet-map");
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
      const urlLat = Number(params.get("lat"));
      const urlLon = Number(params.get("lon"));
      const urlHasCenter = Number.isFinite(urlLat) && Number.isFinite(urlLon);

      const centerLat = urlHasCenter ? urlLat : 55.751244;
      const centerLon = urlHasCenter ? urlLon : 37.618423;

      const initialZoom = urlHasCenter ? 12 : 10;

      const map = L.map(el, {
        zoomControl: false,
        attributionControl: false,
      }).setView([centerLat, centerLon], initialZoom);

      mapRef.current = map;

      L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
        maxZoom: 19,
        subdomains: "abcd",
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
                className: "",
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
        const dKm = distanceKm(
          { lat: center.lat, lon: center.lng },
          { lat: ne.lat, lon: ne.lng },
        );
        const lat = Math.round(center.lat * 100) / 100;
        const lon = Math.round(center.lng * 100) / 100;
        const radiusKm = Math.min(
          100,
          Math.max(10, Math.ceil(dKm / 5) * 5),
        );
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
      map.on("moveend", onMoveEnd);

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
  }, [step, searchParamsKey, destroyMap]);

  // Backend `pvzPoints` o'zgarganda markerlarni **diff** qilamiz:
  //   - mavjud va kelgan IDlardagi point — saqlanadi (DOM node qayta yaratilmaydi)
  //   - kelmagan ID — cluster'dan o'chiriladi va `pvzMarkersRef`'dan tozalanadi
  //   - yangi ID — L.marker yaratiladi va cluster'ga qo'shiladi
  //
  // Filter bo'yicha visibility'ni alohida effect boshqaradi (provider filter
  // o'zgarganda marker'lar saqlanib qoladi, faqat addLayer/removeLayer chaqiriladi).
  // 500 PVZ × text-typing/filter — 0 ta DOM rebuild.
  useEffect(() => {
    if (step !== "map") return;
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
      activeProvider === "all" ? PVZ_PROVIDER_CODES : [activeProvider],
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
          icon: getPvzMarkerIcon(L, point.providerCode),
          keyboard: false,
          title: `${point.providerLabel} — ${point.addressLine}`,
        }).on("click", () => {
          selectPvzOnMap(point.id);
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
  }, [
    step,
    pvzPoints,
    pvzPointById,
    activeProvider,
    selectedPvzId,
    getPvzMarkerIcon,
    openPvzPopup,
    selectPvzOnMap,
  ]);

  // Selected marker'ga CSS class qo'shamiz — `setIcon`'dan saqlanamiz
  // (8KB SVG HTML qayta render bo'lmaydi). Marker `_icon` element Leaflet
  // tomonidan boshqariladi va biz unga `pvz-selected` class'ini qo'shamiz.
  // CSS .pvz-div-icon.pvz-selected'da hajm + border ko'rinishini boshqarish
  // mumkin (page.module.css yoki globals.css'da).
  useEffect(() => {
    if (step !== "map") return;

    const prev = prevSelectedPvzIdRef.current;
    if (prev && prev !== selectedPvzId) {
      const prevMarker = pvzMarkersRef.current.get(prev);
      try {
        prevMarker?._icon?.classList.remove("pvz-selected");
      } catch {
        // ignore
      }
    }

    if (selectedPvzId) {
      const marker = pvzMarkersRef.current.get(selectedPvzId);
      try {
        marker?._icon?.classList.add("pvz-selected");
      } catch {
        // ignore
      }
    }

    prevSelectedPvzIdRef.current = selectedPvzId;
  }, [step, selectedPvzId]);

  useEffect(() => {
    if (step !== "map") return;

    if (isUserTracking) return;

    const L = leafletRef.current;
    const map = mapRef.current;
    if (!L || !map) return;

    const params = new URLSearchParams(searchParamsKey);

    const selectedFromUrl = params.get("pvzId");
    const selectedPoint = selectedFromUrl
      ? pvzPointById.get(selectedFromUrl)
      : undefined;

    const urlLat = Number(params.get("lat"));
    const urlLon = Number(params.get("lon"));
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

  useEffect(() => {
    if (step !== "map") {
      stopUserTracking();
    }

    return () => {
      stopUserTracking();
    };
  }, [step, stopUserTracking]);

  const Toggle = (
    <div className={styles.c2}>
      <button
        type="button"
        aria-pressed={step === "map"}
        className={cn(
          styles.toggleButton,
          step === "map"
            ? styles.toggleButtonActive
            : styles.toggleButtonInactive,
        )}
        onClick={() => setStepAndUrl("map")}
      >
        На карте
      </button>
      <button
        type="button"
        aria-pressed={step === "list"}
        className={cn(
          styles.toggleButton,
          step === "list"
            ? styles.toggleButtonActive
            : styles.toggleButtonInactive,
        )}
        onClick={() => setStepAndUrl("list")}
      >
        Списком
      </button>
    </div>
  );

  if (step === "map") {
    const ProviderIcon = ({ providerCode }) => {
      if (providerCode === "cdek") {
        return (
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path
              fillRule="evenodd"
              clipRule="evenodd"
              d="M10.9998 0C17.0748 0 21.9999 4.9248 21.9999 10.9998C21.9999 17.0748 17.0748 21.9996 10.9998 21.9996C4.92461 21.9996 0 17.0748 0 10.9998C0 4.9248 4.92461 0 10.9998 0ZM4.83866 5.23205C4.91287 5.23205 4.98356 5.24751 5.04732 5.27531L5.04818 5.2745C5.36689 5.40123 5.74373 5.53277 6.06687 5.61181C7.38586 5.9391 8.73303 6.14343 10.1899 6.19447C12.3953 6.27812 14.8101 6.2187 17.6114 6.19946L17.6142 6.19924H17.6276V6.19905C17.9162 6.19905 18.1498 6.43285 18.1498 6.72127C18.1498 6.96528 17.9824 7.17022 17.7559 7.22755C13.127 8.89181 9.26192 11.1715 6.26782 15.2743C6.04574 15.5802 5.81695 15.8973 5.61114 16.2159C5.60508 16.2259 5.59921 16.2356 5.59254 16.2452L5.59211 16.2458C5.49782 16.3818 5.34075 16.4709 5.16256 16.4709C4.8742 16.4709 4.64038 16.2371 4.64038 15.9487C4.64038 15.92 4.64287 15.892 4.64706 15.8646L4.64855 15.8563C5.01661 13.703 5.49219 11.5942 6.37785 9.62646C5.75337 8.64961 5.01365 7.52637 4.36933 5.98785L4.3708 5.98618C4.33609 5.91631 4.31644 5.83765 4.31644 5.75423C4.31644 5.46586 4.55024 5.23205 4.83866 5.23205ZM6.78646 18.3597C6.77287 18.3866 6.75717 18.4126 6.73943 18.4367V18.4369C6.64447 18.566 6.49118 18.6502 6.31822 18.6502C6.03006 18.6502 5.79624 18.4164 5.79624 18.1281C5.79624 18.0299 5.8232 17.9385 5.87027 17.8601H5.87008L5.87193 17.8574L6.29796 17.16C9.33305 12.4564 13.1909 10.0437 18.1813 8.24433C18.215 8.22784 18.2506 8.21463 18.2879 8.20566H18.2886C18.3279 8.19622 18.3687 8.19121 18.4107 8.19121C18.6991 8.19121 18.9329 8.42501 18.9329 8.71343C18.9329 8.93173 18.7987 9.11893 18.6084 9.19673V9.19692L18.6048 9.19816C18.5931 9.20279 18.5812 9.20718 18.569 9.21094C13.4485 11.0418 9.80966 13.3741 6.78646 18.3597Z"
              fill="#2D2D2D"
            />
          </svg>
        );
      }
      // yandex_delivery
      return (
        <svg width="22" height="22" viewBox="0 0 22 22" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path
            fillRule="evenodd"
            clipRule="evenodd"
            d="M9.39303 0.0503741C7.03646 0.423252 5.04356 1.42068 3.30032 3.09983C1.75064 4.5926 0.83489 6.17798 0.217332 8.43709C-0.0956258 9.58236 -0.0649481 12.5231 0.272963 13.7541C1.85824 19.53 7.59415 23.0175 13.3994 21.735C15.3693 21.2998 17.0525 20.3831 18.5916 18.907C23.0601 14.6219 23.1459 7.62078 18.7838 3.22664C17.4304 1.86331 15.5856 0.794872 13.7428 0.307306C12.8406 0.0686694 10.2464 -0.0845525 9.39303 0.0503741ZM14.7158 11.067V17.5847H13.5711H12.4264V11.8539V6.1231L11.4248 6.19937C9.45839 6.34893 8.59163 7.11401 8.61567 8.67881C8.62323 9.16592 8.70816 9.62204 8.85033 9.94003C9.1056 10.5104 9.98426 11.3746 11.0242 12.078C11.4178 12.3442 11.7367 12.5987 11.733 12.6435C11.7293 12.6883 10.9954 13.8056 10.1018 15.1262L8.47728 17.5275L7.30397 17.5601C6.58523 17.5801 6.13067 17.5489 6.13067 17.4797C6.13067 17.4175 6.76952 16.4244 7.55043 15.2727L8.97007 13.179L8.0708 12.3478C7.39738 11.7254 7.07664 11.3243 6.79413 10.7511C6.43985 10.0323 6.41684 9.91213 6.41684 8.78253C6.41684 7.72347 6.45267 7.50312 6.71675 6.94078C7.1072 6.10892 7.7148 5.51421 8.59404 5.10326C9.59484 4.63536 10.0244 4.57602 12.5123 4.56195L14.7158 4.54938V11.067Z"
            fill="#2D2D2D"
          />
        </svg>
      );
    };

    const ProviderChips = (
      <div className={styles.c5}>
        <div className={cn(styles.c6, styles.tw2, styles.noScrollbar)}>
          <button
            type="button"
            aria-pressed={activeProvider === "all"}
            onClick={() => setActiveProvider("all")}
            className={cn(
              styles.providerChip,
              activeProvider === "all"
                ? styles.providerChipActive
                : styles.providerChipInactive,
            )}
          >
            <span className={cn(styles.c7, styles.tw3)}>
              <span className={cn(styles.c8, styles.tw4)}>
                <span className={cn(styles.c9, styles.tw5)} />
                <span className={cn(styles.c10, styles.tw6)} />
                <span className={cn(styles.c11, styles.tw7)} />
                <span className={cn(styles.c12, styles.tw8)} />
              </span>
            </span>
            <span className={cn(styles.c13, styles.nowrap)}>Все</span>
          </button>
          {PVZ_PROVIDERS.map((p) => {
            const isOn = activeProvider === p.code;
            return (
              <button
                key={p.code}
                type="button"
                aria-pressed={isOn}
                onClick={() => setActiveProvider(p.code)}
                className={cn(
                  styles.providerChip,
                  isOn
                    ? styles.providerChipActive
                    : styles.providerChipInactive,
                )}
              >
                <span className={cn(styles.c14, styles.tw9)}>
                  <ProviderIcon providerCode={p.code} />
                </span>
                <span className={cn(styles.c15, styles.nowrap)}>{p.short}</span>
              </button>
            );
          })}
        </div>
      </div>
    );

    return (
      <div className={styles.c16}>
        <Header title="Оформление заказа" showClose showMore />

        <div className={cn(styles.c17, styles.tw10)}>
          <div id="pickup-leaflet-map" className={styles.c18} />

          {/* PVZ yuklanish overlay loader — non-blocking, top-center */}
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
            onClick={() =>
              isUserTracking ? stopUserTracking() : startUserTracking()
            }
            // PVZ modal ochilganda geo tugmani yashirish (z-index conflict).
            style={{ display: selectedPvz && isPvzModalOpen ? "none" : undefined }}
            className={cn(
              styles.geoButton,
              isUserTracking && styles.geoButtonActive,
            )}
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

          {/* Per-provider degradation: bitta provider degraded bo'lsa, qolgan
              provider markerlari hali ham ko'rinadi. */}
          {Object.keys(providerErrors).length > 0 ? (
            <div className={cn(styles.c19, styles.tw11)}>
              <div className={cn(styles.c20, styles.tw12)}>
                {Object.entries(providerErrors)
                  .map(([code]) =>
                    code === "cdek"
                      ? "CDEK временно недоступен"
                      : code === "yandex_delivery"
                        ? "Яндекс Доставка временно недоступна"
                        : `${code}: ошибка`,
                  )
                  .join(" · ")}
              </div>
            </div>
          ) : null}

          {isPickupError ? (
            <div className={cn(styles.c19, styles.tw11)}>
              <div className={cn(styles.c20, styles.tw12)}>
                Не удалось загрузить пункты выдачи
              </div>
            </div>
          ) : null}

          <div className={cn(styles.c21, styles.tw13)}>
            <div className={cn(styles.c22, styles.tw14)}>{Toggle}</div>
          </div>
        </div>

        {selectedPvz && isPvzModalOpen ? (
          <div
            className={cn(styles.c23, styles.tw15, styles.leftHalf)}
            style={{ zIndex: 2000 }}
          >
            <div className={styles.c24}>
              <div className={cn(styles.c25)}>
                <div className={styles.c26}>
                  <div className={cn(styles.c27, styles.tw16)} />
                </div>

                <div className={styles.c28}>
                  <div className={cn(styles.c29, styles.tw17)}>
                    <div className={cn(styles.c30)}>
                      {selectedPvz.providerLabel}
                      {selectedPvz.pickupPointTypeLabel
                        ? ` · ${selectedPvz.pickupPointTypeLabel}`
                        : ""}
                    </div>
                    <button
                      type="button"
                      aria-label="Закрыть"
                      onClick={() => setIsPvzModalOpen(false)}
                      className={cn(styles.c31, styles.tw18)}
                    >
                      <img
                        src="/icons/global/xicon.svg"
                        alt=""
                        className={cn(styles.c32, styles.tw19)}
                      />
                    </button>
                  </div>

                  <div className={cn(styles.c33, styles.spaceY3)}>
                    <div className={cn(styles.c34, styles.tw20)}>
                      <MapPin className={cn(styles.c35, styles.tw21)} />
                      <div className={styles.c36}>
                        {selectedPvz.addressLine}
                      </div>
                    </div>

                    {selectedPvz.workSchedule ? (
                      <div className={cn(styles.c40, styles.tw24)}>
                        <Clock className={cn(styles.c41, styles.tw25)} />
                        <div className={styles.c52}>
                          {selectedPvz.workSchedule
                            .split(/[;\n]+/)
                            .map((s) => s.trim())
                            .filter(Boolean)
                            .map((line, i) => (
                              <div key={i}>{line}</div>
                            ))}
                        </div>
                      </div>
                    ) : null}

                    {selectedPvz.phone ? (
                      <div className={cn(styles.c50, styles.tw34)}>
                        <Phone className={cn(styles.c51, styles.tw35)} />
                        <a href={`tel:${selectedPvz.phone}`} className={styles.c52}>
                          {selectedPvz.phone}
                        </a>
                      </div>
                    ) : null}

                    {selectedPvz.isCashAllowed || selectedPvz.isCardAllowed ? (
                      <div className={cn(styles.c53, styles.tw36)}>
                        <CreditCard className={cn(styles.c54, styles.tw37)} />
                        <div className={styles.c55}>
                          {[
                            selectedPvz.isCashAllowed ? "наличные" : null,
                            selectedPvz.isCardAllowed ? "карта" : null,
                          ]
                            .filter(Boolean)
                            .join(", ")}
                        </div>
                      </div>
                    ) : null}
                  </div>

                  <div className={styles.c56}>
                    <Button
                      type="button"
                      variant="primary"
                      size="lg"
                      className={styles.c57}
                      onClick={() => {
                        if (!selectedPvz) return;
                        const params = new URLSearchParams();
                        params.set("pickupPvzId", selectedPvz.externalId);
                        params.set("pickupProvider", selectedPvz.providerCode);
                        params.set("pickupAddress", selectedPvz.addressLine);
                        router.push(`/checkout?${params.toString()}`);
                      }}
                    >
                      Доставить сюда
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className={cn(styles.c58, styles.tw38, styles.leftHalf)}>
            <div className={styles.c59}>{ProviderChips}</div>
            <Button
              type="button"
              variant="primary"
              size="lg"
              className={styles.c60}
              onClick={() => setStepAndUrl("search")}
            >
              Поиск города
            </Button>
          </div>
        )}
      </div>
    );
  }

  if (step === "search") {
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
                  setQuery("");
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
                params.set("step", "map");
                params.set("address", p.title);
                if (p.lat != null) params.set("lat", String(p.lat));
                if (p.lon != null) params.set("lon", String(p.lon));
                // radius_km=10 (default) — backend bounding box uchun.
                if (p.lat != null && p.lon != null) params.set("radius", "10");

                router.replace(`/checkout/pickup?${params.toString()}`);
                setStep("map");
              }}
              className={cn(
                styles.searchItem,
                idx === items.length - 1 ? null : styles.searchItemBorder,
              )}
            >
              <img
                src="/icons/global/locationGrey.svg"
                alt="location"
                className={cn(styles.c69, styles.tw44)}
              />
              <div className={cn(styles.c70, styles.tw45)}>
                <div className={styles.c71}>{p.title}</div>
                {p.subtitle ? (
                  <div className={styles.c72}>{p.subtitle}</div>
                ) : null}
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
      <Header title="Оформление заказа" showClose showMore />
      <div className={styles.c75}>
        <div className={styles.c76}>{Toggle}</div>
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
              onClick={() => setPvzQuery("")}
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
                selectPvzOnMap(p.id);
              }}
              className={cn(
                styles.pvzListItem,
                isActive
                  ? styles.pvzListItemActive
                  : styles.pvzListItemInactive,
                idx === filteredPvz.length - 1
                  ? null
                  : styles.pvzListItemBorder,
              )}
            >
              <div className={cn(styles.c83, styles.tw51)}>
                <div className={cn(styles.c84)}>
                  {p.providerLabel}
                  {p.pickupPointTypeLabel ? ` · ${p.pickupPointTypeLabel}` : ""}
                </div>
                <div className={styles.c85}>{p.addressLine}</div>
                {p.workSchedule ? (
                  <div className={styles.c86}>{p.workSchedule}</div>
                ) : null}
              </div>
            </button>
          );
        })}

        {filteredPvz.length === 0 && !isPickupFetching ? (
          <div className={styles.c88}>
            {pickupQueryArgs
              ? "Ничего не найдено"
              : "Сначала укажите адрес или включите геолокацию"}
          </div>
        ) : null}

        {isPickupFetching ? (
          <div className={styles.c88}>Загружаем пункты выдачи…</div>
        ) : null}
      </div>
    </div>
  );
}
