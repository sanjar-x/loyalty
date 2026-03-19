"use client";

import React, {
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";
import "leaflet.markercluster/dist/MarkerCluster.Default.css";
import Button from "@/components/ui/Button";
import {
  CalendarDays,
  Clock,
  CreditCard,
  Hourglass,
  MapPin,
} from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import styles from "./page.module.css";
import cn from "clsx";

/**
 * @typedef {Object} DaDataSuggestAddressResponse
 * @property {{ value?: string, data?: { geo_lat?: (string|null), geo_lon?: (string|null), region_with_type?: string, city_with_type?: string, settlement_with_type?: string, area_with_type?: string, country?: string } }[]=} suggestions
 *
 * @typedef {{ id: string, title: string, subtitle: string, lat: (number|null), lon: (number|null) }} SuggestItem
 * @typedef {{ id: string, provider: string, address: string, deliveryText: string, priceText: string, lat: number, lon: number }} PvzPoint
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

const PVZ_PROVIDERS = ["Яндекс Доставка", "CDEK", "Boxberry", "Почта России"];

function generateTestPvzPoints(count) {
  const cities = [
    { city: "Москва", lat: 55.751244, lon: 37.618423 },
    { city: "Санкт-Петербург", lat: 59.938732, lon: 30.316229 },
    { city: "Новосибирск", lat: 55.030199, lon: 82.92043 },
    { city: "Екатеринбург", lat: 56.838011, lon: 60.597465 },
    { city: "Казань", lat: 55.796127, lon: 49.106414 },
    { city: "Нижний Новгород", lat: 56.326944, lon: 44.0075 },
    { city: "Самара", lat: 53.195873, lon: 50.100193 },
    { city: "Омск", lat: 54.989342, lon: 73.368212 },
    { city: "Ростов-на-Дону", lat: 47.235713, lon: 39.701505 },
    { city: "Уфа", lat: 54.738762, lon: 55.972055 },
    { city: "Красноярск", lat: 56.010563, lon: 92.852572 },
    { city: "Воронеж", lat: 51.660781, lon: 39.200269 },
    { city: "Пермь", lat: 58.010455, lon: 56.229443 },
    { city: "Волгоград", lat: 48.708048, lon: 44.513303 },
    { city: "Краснодар", lat: 45.03547, lon: 38.975313 },
    { city: "Саратов", lat: 51.533103, lon: 46.034158 },
    { city: "Тюмень", lat: 57.153033, lon: 65.534328 },
    { city: "Тольятти", lat: 53.507836, lon: 49.420393 },
    { city: "Ижевск", lat: 56.852744, lon: 53.211396 },
    { city: "Барнаул", lat: 53.347997, lon: 83.779806 },
    { city: "Иркутск", lat: 52.286387, lon: 104.28066 },
    { city: "Хабаровск", lat: 48.480223, lon: 135.071917 },
    { city: "Владивосток", lat: 43.115536, lon: 131.885485 },
    { city: "Ярославль", lat: 57.626074, lon: 39.88447 },
    { city: "Сочи", lat: 43.585472, lon: 39.723098 },
    { city: "Калининград", lat: 54.710426, lon: 20.452214 },
    { city: "Мурманск", lat: 68.970682, lon: 33.074981 },
    { city: "Севастополь", lat: 44.61665, lon: 33.525367 },
  ];

  const streets = [
    "Ленина ул",
    "Советская ул",
    "Мира ул",
    "Победы ул",
    "Школьная ул",
    "Набережная ул",
    "Садовая ул",
    "Центральная ул",
    "Парковая ул",
    "Зеленая ул",
  ];

  const deliveryTextByProvider = {
    "Яндекс Доставка": "Доставка 1-3 дня",
    CDEK: "Доставка 2-5 дней",
    Boxberry: "Доставка 2-6 дней",
    "Почта России": "Доставка 3-7 дней",
  };

  const points = [];

  const mulberry32 = (seed) => {
    let t = seed >>> 0;
    return () => {
      t += 0x6d2b79f5;
      let x = Math.imul(t ^ (t >>> 15), 1 | t);
      x ^= x + Math.imul(x ^ (x >>> 7), 61 | x);
      return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
    };
  };

  const perCityBase = Math.floor(count / cities.length);
  const remainder = count % cities.length;
  let globalIndex = 0;

  for (let cityIndex = 0; cityIndex < cities.length; cityIndex++) {
    const city = cities[cityIndex];
    const cityCount = perCityBase + (cityIndex < remainder ? 1 : 0);

    for (let j = 0; j < cityCount; j++) {
      if (globalIndex >= count) break;

      const provider = PVZ_PROVIDERS[j % PVZ_PROVIDERS.length];
      const street = streets[(globalIndex + cityIndex) % streets.length];
      const house = 1 + ((globalIndex * 7) % 140);
      const building = 1 + (globalIndex % 5);

      const rand = mulberry32(cityIndex * 10_000 + j + 1);
      const angle = rand() * Math.PI * 2;
      const radius = 0.01 + rand() * 0.18; // ~1km..20km (rough)
      const dLat = Math.sin(angle) * radius;
      const dLon =
        Math.cos(angle) * radius * Math.cos((city.lat * Math.PI) / 180);

      const lat = city.lat + dLat;
      const lon = city.lon + dLon;

      const price = 199 + ((globalIndex * 37) % 1200);

      points.push({
        id: `pvz-${globalIndex + 1}`,
        provider,
        address: `${city.city}, ${street}, д. ${house}, стр. ${building}`,
        deliveryText: deliveryTextByProvider[provider],
        priceText: `Стоимость — ${price}₽`,
        lat,
        lon,
      });

      globalIndex++;
    }
  }

  return points;
}

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
  const pvzPointsRef = useRef(null);
  const pvzPointByIdRef = useRef(null);
  const pvzMarkersRef = useRef(new Map());
  const pvzProviderByIdRef = useRef(new Map());
  const prevSelectedPvzIdRef = useRef(null);
  const userMarkerRef = useRef(null);
  const userAccuracyCircleRef = useRef(null);
  const geoWatchIdRef = useRef(null);
  const userEverCenteredRef = useRef(false);
  const initSeqRef = useRef(0);
  const iconFixedRef = useRef(false);

  const ensurePvzPoints = useCallback(() => {
    if (!pvzPointsRef.current) {
      pvzPointsRef.current = generateTestPvzPoints(500);
    }
    return pvzPointsRef.current;
  }, []);

  const ensurePvzIndex = useCallback(() => {
    if (!pvzPointByIdRef.current) {
      const index = new Map();
      for (const p of ensurePvzPoints()) index.set(p.id, p);
      pvzPointByIdRef.current = index;
    }
    return pvzPointByIdRef.current;
  }, [ensurePvzPoints]);

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

  const [activeProvider, setActiveProvider] = useState("all");

  const selectedPvzId = useMemo(() => {
    const id = new URLSearchParams(searchParamsKey).get("pvzId");
    return id && id.trim() ? id : null;
  }, [searchParamsKey]);

  const selectedPvz = useMemo(() => {
    if (!selectedPvzId) return null;
    return ensurePvzIndex().get(selectedPvzId) ?? null;
  }, [ensurePvzIndex, selectedPvzId]);

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
        const res = await fetch("/api/dadata/suggest/address", {
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
        id: `dadata-${index}`,
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

  const filteredPvz = useMemo(() => {
    if (step !== "list") return [];

    const allPoints = ensurePvzPoints();
    const q = pvzQuery.trim().toLowerCase();
    const base = !q
      ? allPoints
      : allPoints.filter((x) => {
          const hay = `${x.provider} ${x.address}`.toLowerCase();
          return hay.includes(q);
        });

    const providerFiltered =
      activeProvider === "all"
        ? base
        : base.filter((x) => x.provider === activeProvider);

    if (!userLocation) return providerFiltered;

    // Show nearest PVZ first once user's location is known.
    return [...providerFiltered].sort((a, b) => {
      const da = distanceKm(userLocation, { lat: a.lat, lon: a.lon });
      const db = distanceKm(userLocation, { lat: b.lat, lon: b.lon });
      return da - db;
    });
  }, [ensurePvzPoints, activeProvider, pvzQuery, step, userLocation]);

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

  useEffect(() => {
    if (step !== "map") return;

    const cluster = pvzClusterRef.current;

    if (!cluster?.clearLayers) return;

    const enabledProviders = new Set(
      activeProvider === "all" ? PVZ_PROVIDERS : [activeProvider],
    );

    // Safety: keep selected PVZ visible even if filter doesn't match yet.
    if (selectedPvzId) {
      const selectedProvider = ensurePvzIndex().get(selectedPvzId)?.provider;
      if (selectedProvider) enabledProviders.add(selectedProvider);
    }

    const markers = [];
    for (const [id, marker] of pvzMarkersRef.current.entries()) {
      const provider = pvzProviderByIdRef.current.get(id);
      if (!provider) continue;
      if (!enabledProviders.has(provider)) continue;
      markers.push(marker);
    }

    try {
      cluster.clearLayers();
    } catch {
      // ignore
    }

    if (cluster.addLayers) {
      cluster.addLayers(markers);
    } else if (cluster.addLayer) {
      for (const m of markers) cluster.addLayer(m);
    }

    if (selectedPvzId) {
      requestAnimationFrame(() => openPvzPopup(selectedPvzId));
    }
  }, [openPvzPopup, activeProvider, ensurePvzIndex, selectedPvzId, step]);

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

  const getPvzMarkerIcon = useCallback((L, provider, isSelected) => {
    const bubble = isSelected ? 54 : 48;
    const tail = isSelected ? 16 : 14;
    const border = isSelected ? 3 : 2;
    const totalH = bubble + Math.floor(tail / 2);

    const iconHtml = (() => {
      switch (provider) {
        case "CDEK":
          return `
            <svg width=${bubble} height="auto" viewBox="0 0 55 65" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M27.127 1C41.5361 1 53.2606 12.7233 53.2607 27.127C53.2607 37.2436 47.341 46.5399 38.1758 50.8154C35.1511 52.2259 32.5883 54.7621 30.9814 57.9814L30.9805 57.9824L28.6836 62.5781C28.3908 63.1637 27.7905 63.5381 27.127 63.5381C26.4615 63.538 25.8751 63.1576 25.5801 62.5947L25.5752 62.5859L23.2734 57.9824V57.9814C21.7669 54.9632 19.4198 52.5454 16.6445 51.0928L16.084 50.8154C6.9189 46.54 1 37.2435 1 27.127C1.00013 12.7237 12.7175 1.00013 27.127 1Z" fill="#2D2D2D" stroke="white" stroke-width="2"/>
<path d="M18.1689 18.0692C18.0669 18.0247 17.9539 18 17.8352 18C17.3739 18 17 18.3739 17 18.8351C17 18.9686 17.0314 19.0944 17.0869 19.2061L17.0846 19.2088C18.1151 21.6694 19.2981 23.4658 20.2969 25.0282C18.8804 28.1752 18.1198 31.5479 17.5311 34.9918L17.5288 35.0051C17.5221 35.0489 17.5181 35.0937 17.5181 35.1395C17.5181 35.6009 17.892 35.9747 18.3532 35.9747C18.6382 35.9747 18.8894 35.8322 19.0402 35.6148L19.0409 35.6138C19.0512 35.599 19.0602 35.5841 19.0695 35.5688L19.0706 35.567C19.3998 35.0573 19.7657 34.5501 20.1209 34.0609C24.9094 27.4992 31.091 23.8532 38.494 21.1915C38.8563 21.0998 39.1239 20.772 39.1239 20.3818C39.1239 19.9205 38.7503 19.5469 38.2888 19.5469H38.2674L38.2629 19.5472C33.7828 19.578 29.9207 19.673 26.3935 19.5392C24.0635 19.4576 21.909 19.1308 19.7995 18.6074C19.2827 18.481 18.68 18.2706 18.1703 18.0679L18.1689 18.0692Z" fill="white"/>
<path d="M20.8751 39.1188C20.9035 39.0802 20.9286 39.0386 20.9504 38.9956C25.7854 31.022 31.6051 27.2918 39.7944 24.3636C39.814 24.3576 39.8329 24.3506 39.8517 24.3432L39.8574 24.3409C40.1617 24.2164 40.3765 23.9171 40.3765 23.5679C40.3765 23.1066 40.0025 22.7327 39.5413 22.7327C39.4741 22.7327 39.4089 22.7407 39.3459 22.7558H39.3449C39.2852 22.7702 39.2283 22.7913 39.1744 22.8177C31.1931 25.6954 25.0232 29.5542 20.1691 37.0769L19.4877 38.1922L19.4851 38.1966C19.4098 38.3219 19.3667 38.4681 19.3667 38.6251C19.3667 39.0863 19.7406 39.4603 20.2015 39.4603C20.4781 39.4603 20.7233 39.3252 20.8751 39.1188Z" fill="white"/>
</svg>

            `;
        case "Boxberry":
          return `
              <svg width=${bubble} height="auto" viewBox="0 0 55 65" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M27.127 1C41.5361 1 53.2606 12.7233 53.2607 27.127C53.2607 37.2436 47.341 46.5399 38.1758 50.8154C35.1511 52.2259 32.5883 54.7621 30.9814 57.9814L30.9805 57.9824L28.6836 62.5781C28.3908 63.1637 27.7905 63.5381 27.127 63.5381C26.4615 63.538 25.8751 63.1576 25.5801 62.5947L25.5752 62.5859L23.2734 57.9824V57.9814C21.7669 54.9632 19.4198 52.5454 16.6445 51.0928L16.084 50.8154C6.9189 46.54 1 37.2435 1 27.127C1.00013 12.7237 12.7175 1.00013 27.127 1Z" fill="#2D2D2D" stroke="white" stroke-width="2"/>
<path d="M30.1228 27.5C30.1228 28.9877 28.9485 30.1937 27.5 30.1937C26.0515 30.1937 24.8772 28.9877 24.8772 27.5C24.8772 26.0123 26.0515 24.8063 27.5 24.8063C28.9485 24.8063 30.1228 26.0123 30.1228 27.5Z" fill="white"/>
<path d="M25.6842 23.045C25.6842 24.5327 24.5099 25.7387 23.0614 25.7387C21.6129 25.7387 20.4386 24.5327 20.4386 23.045C20.4386 21.5574 21.6129 20.3514 23.0614 20.3514C24.5099 20.3514 25.6842 21.5574 25.6842 23.045Z" fill="white"/>
<path d="M21.2456 27.5C21.2456 28.9877 20.0713 30.1937 18.6228 30.1937C17.1743 30.1937 16 28.9877 16 27.5C16 26.0123 17.1743 24.8063 18.6228 24.8063C20.0713 24.8063 21.2456 26.0123 21.2456 27.5Z" fill="white"/>
<path d="M30.1228 36.3063C30.1228 37.794 28.9485 39 27.5 39C26.0515 39 24.8772 37.794 24.8772 36.3063C24.8772 34.8186 26.0515 33.6126 27.5 33.6126C28.9485 33.6126 30.1228 34.8186 30.1228 36.3063Z" fill="white"/>
<path d="M25.6842 31.8514C25.6842 33.339 24.5099 34.545 23.0614 34.545C21.6129 34.545 20.4386 33.339 20.4386 31.8514C20.4386 30.3637 21.6129 29.1577 23.0614 29.1577C24.5099 29.1577 25.6842 30.3637 25.6842 31.8514Z" fill="white"/>
<path d="M34.5614 31.8514C34.5614 33.339 33.3871 34.545 31.9386 34.545C30.4901 34.545 29.3158 33.339 29.3158 31.8514C29.3158 30.3637 30.4901 29.1577 31.9386 29.1577C33.3871 29.1577 34.5614 30.3637 34.5614 31.8514Z" fill="white"/>
<path d="M39 27.5C39 28.9877 37.8257 30.1937 36.3772 30.1937C34.9287 30.1937 33.7544 28.9877 33.7544 27.5C33.7544 26.0123 34.9287 24.8063 36.3772 24.8063C37.8257 24.8063 39 26.0123 39 27.5Z" fill="white"/>
<path d="M34.5614 23.045C34.5614 24.5327 33.3871 25.7387 31.9386 25.7387C30.4901 25.7387 29.3158 24.5327 29.3158 23.045C29.3158 21.5574 30.4901 20.3514 31.9386 20.3514C33.3871 20.3514 34.5614 21.5574 34.5614 23.045Z" fill="white"/>
<path d="M30.1228 18.6937C30.1228 20.1814 28.9485 21.3874 27.5 21.3874C26.0515 21.3874 24.8772 20.1814 24.8772 18.6937C24.8772 17.206 26.0515 16 27.5 16C28.9485 16 30.1228 17.206 30.1228 18.6937Z" fill="white"/>
</svg>

            `;
        case "Яндекс Доставка":
          return `
             <svg width=${bubble} height="auto" viewBox="0 0 55 65" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M27.127 1C41.5361 1 53.2606 12.7233 53.2607 27.127C53.2607 37.2436 47.341 46.5399 38.1758 50.8154C35.1511 52.2259 32.5883 54.7621 30.9814 57.9814L30.9805 57.9824L28.6836 62.5781C28.3908 63.1637 27.7905 63.5381 27.127 63.5381C26.4615 63.538 25.8751 63.1576 25.5801 62.5947L25.5752 62.5859L23.2734 57.9824V57.9814C21.7669 54.9632 19.4198 52.5454 16.6445 51.0928L16.084 50.8154C6.9189 46.54 1 37.2435 1 27.127C1.00013 12.7237 12.7175 1.00013 27.127 1Z" fill="#2D2D2D" stroke="white" stroke-width="2"/>
<rect x="18.9238" y="17.769" width="16.1538" height="20.7692" fill="white"/>
<path fill-rule="evenodd" clip-rule="evenodd" d="M24.8087 12.0687C21.5952 12.5772 18.8776 13.9373 16.5004 16.227C14.3872 18.2626 13.1385 20.4245 12.2964 23.5051C11.8696 25.0669 11.9114 29.0769 12.3722 30.7556C14.534 38.6318 22.3557 43.3875 30.272 41.6387C32.9582 41.0452 35.2534 39.7952 37.3522 37.7823C43.4456 31.9389 43.5626 22.392 37.6143 16.4C35.7688 14.5409 33.253 13.0839 30.7402 12.4191C29.5099 12.0936 25.9724 11.8847 24.8087 12.0687ZM32.067 27.0914V35.9791H30.5061H28.9452V28.1645V20.3497L27.5793 20.4537C24.8978 20.6576 23.7159 21.7009 23.7486 23.8347C23.7589 24.499 23.8748 25.121 24.0686 25.5546C24.4167 26.3323 25.6149 27.5108 27.033 28.4701C27.5697 28.8331 28.0045 29.18 27.9995 29.2411C27.9945 29.3022 26.9937 30.8258 25.7752 32.6267L23.5599 35.9011L21.96 35.9456C20.9799 35.9728 20.36 35.9303 20.36 35.8359C20.36 35.7511 21.2312 34.3969 22.296 32.8264L24.2319 29.9713L23.0056 28.8379C22.0873 27.9892 21.65 27.4422 21.2647 26.6606C20.7816 25.6804 20.7502 25.5165 20.7502 23.9762C20.7502 22.532 20.7991 22.2315 21.1592 21.4647C21.6916 20.3303 22.5202 19.5194 23.7191 18.959C25.0839 18.3209 25.6697 18.24 29.0622 18.2208L32.067 18.2037V27.0914Z" fill="#2D2D2D"/>
</svg>

            `;
        case "Почта России":
          return `
<svg width=${bubble} height="auto" viewBox="0 0 55 65" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M27.127 1C41.5361 1 53.2606 12.7233 53.2607 27.127C53.2607 37.2436 47.341 46.5399 38.1758 50.8154C35.1511 52.2259 32.5883 54.7621 30.9814 57.9814L30.9805 57.9824L28.6836 62.5781C28.3908 63.1637 27.7905 63.5381 27.127 63.5381C26.4615 63.538 25.8751 63.1576 25.5801 62.5947L25.5752 62.5859L23.2734 57.9824V57.9814C21.7669 54.9632 19.4198 52.5454 16.6445 51.0928L16.084 50.8154C6.9189 46.54 1 37.2435 1 27.127C1.00013 12.7237 12.7175 1.00013 27.127 1Z" fill="#2D2D2D" stroke="white" stroke-width="2"/>
<mask id="mask0_0_11985" style="mask-type:luminance" maskUnits="userSpaceOnUse" x="13" y="19" width="28" height="18">
<path d="M41 19H13V36.0643H41V19Z" fill="white"/>
</mask>
<g mask="url(#mask0_0_11985)">
<path d="M17.7158 19.1265V26.7709H16.4418V20.2265H14.2741V26.7709H13V19.1265H17.7158Z" fill="white"/>
<path d="M20.0163 26.4686C19.6347 26.1181 19.3571 25.6691 19.2141 25.171C19.0049 24.4719 18.9055 23.7446 18.9192 23.0151C18.9057 22.2652 19.0052 21.5175 19.2141 20.7972C19.3545 20.2827 19.6317 19.8159 20.0163 19.4465C20.3526 19.1581 20.781 18.9995 21.2241 18.9995C21.6671 18.9995 22.0955 19.1581 22.4318 19.4465C22.8184 19.8126 23.0952 20.2794 23.231 20.7943C23.4403 21.5155 23.5397 22.2642 23.5259 23.0151C23.5396 23.7456 23.4401 24.4738 23.231 25.1739C23.0917 25.6722 22.8159 26.1217 22.4347 26.4716C22.0918 26.7481 21.6646 26.8988 21.2241 26.8988C20.7835 26.8988 20.3563 26.7481 20.0134 26.4716L20.0163 26.4686ZM20.329 24.5339C20.3788 24.8673 20.5017 25.1855 20.6888 25.4659C20.7477 25.5541 20.8269 25.627 20.9198 25.6783C21.0127 25.7296 21.1165 25.7579 21.2226 25.7608C21.5381 25.7608 21.7859 25.5308 21.9687 25.0707C22.1803 24.4039 22.2722 23.705 22.2401 23.0062C22.2482 22.4746 22.2067 21.9434 22.1162 21.4195C22.0686 21.0751 21.9469 20.745 21.7593 20.4522C21.7067 20.3562 21.6293 20.2762 21.5351 20.2204C21.4409 20.1647 21.3335 20.1352 21.2241 20.1352C21.1146 20.1352 21.0072 20.1647 20.913 20.2204C20.8188 20.2762 20.7414 20.3562 20.6888 20.4522C20.5035 20.7453 20.381 21.0737 20.329 21.4166C20.2374 21.9394 20.1949 22.4696 20.2022 23.0003C20.1941 23.5144 20.2366 24.0281 20.329 24.5339Z" fill="white"/>
<path d="M27.7334 19.1265V22.058H27.058C26.8132 22.0714 26.5687 22.027 26.3443 21.9282C26.1672 21.8342 26.0315 21.6775 25.9638 21.4888C25.8737 21.2262 25.8327 20.9493 25.8429 20.6719V19.1265H24.5688V20.666C24.5318 21.33 24.7302 21.9859 25.1292 22.5181C25.3387 22.7508 25.5984 22.9328 25.8886 23.0503C26.1788 23.1678 26.492 23.2178 26.8044 23.1964H27.7334V26.7709H29.0074V19.1265H27.7334Z" fill="white"/>
<path d="M34.5966 20.2265H33.1014V26.7709H31.8273V20.2265H30.332V19.1265H34.5966V20.2265Z" fill="white"/>
<path d="M37.1628 19.1257H38.1832C38.6036 19.1029 39.0216 19.2056 39.3835 19.4206C39.6995 19.6317 39.9451 19.9327 40.0885 20.2847C40.2639 20.7214 40.3741 21.1815 40.4158 21.6502L41.0057 26.7553H39.7317L39.3188 23.1897H37.1568V26.7701H35.8828V19.1257H37.1628ZM37.1628 22.1044H39.1978L39.1448 21.6649C39.1212 21.3826 39.0626 21.1042 38.9706 20.8362C38.9061 20.6559 38.7797 20.5043 38.6137 20.4086C38.3998 20.306 38.1634 20.2593 37.9266 20.2729H37.1628V22.1044Z" fill="white"/>
<path d="M14.4038 28.2928C14.8286 28.2815 15.2479 28.391 15.613 28.6084C15.971 28.8362 16.2501 29.1688 16.4123 29.5609C16.6194 30.0606 16.7199 30.5981 16.7072 31.1388C16.7203 31.6503 16.629 32.1591 16.4388 32.634C16.2979 32.9989 16.0702 33.3239 15.7752 33.5808C15.5758 33.7686 15.3172 33.8813 15.0438 33.8993C14.9022 33.9092 14.7602 33.8879 14.6277 33.837C14.4952 33.786 14.3755 33.7066 14.277 33.6044V35.9372H13V28.2928H14.4038ZM14.3478 32.2506C14.3792 32.3873 14.4441 32.5139 14.5365 32.6193C14.5667 32.6564 14.6044 32.6866 14.6471 32.7079C14.6898 32.7293 14.7366 32.7413 14.7843 32.7432C14.8962 32.737 15.0016 32.6885 15.0792 32.6075C15.1983 32.4837 15.2836 32.3314 15.3269 32.1651C15.3986 31.911 15.4314 31.6475 15.4243 31.3836C15.4243 30.6699 15.3387 30.1655 15.1618 29.8706C15.0893 29.7343 14.9803 29.621 14.8469 29.5433C14.7135 29.4657 14.5611 29.4269 14.4068 29.4312H14.277V31.6608C14.2731 31.8597 14.2969 32.0583 14.3478 32.2506Z" fill="white"/>
<path d="M18.114 35.6312C17.7307 35.2808 17.4528 34.8304 17.3118 34.3306C17.1024 33.6316 17.0029 32.9043 17.0169 32.1747C17.0034 31.4258 17.1028 30.6791 17.3118 29.9598C17.451 29.4457 17.7285 28.9795 18.114 28.612C18.4503 28.3236 18.8787 28.165 19.3217 28.165C19.7648 28.165 20.1932 28.3236 20.5294 28.612C20.9144 28.9783 21.191 29.4436 21.3287 29.9569C21.5377 30.6782 21.6372 31.4268 21.6236 32.1776C21.6425 32.9074 21.548 33.6357 21.3434 34.3365C21.2049 34.8351 20.929 35.2848 20.5471 35.6341C20.2052 35.9127 19.7776 36.0648 19.3365 36.0648C18.8954 36.0648 18.4678 35.9127 18.1258 35.6341L18.114 35.6312ZM18.4296 33.6994C18.4813 34.0245 18.6031 34.3344 18.7864 34.6078C18.8448 34.6953 18.9231 34.7676 19.0149 34.8189C19.1066 34.8702 19.2093 34.8989 19.3144 34.9027C19.629 34.9027 19.8767 34.6727 20.0576 34.2126C20.2721 33.5465 20.365 32.8472 20.3318 32.1482C20.3399 31.6165 20.2984 31.0854 20.208 30.5614C20.159 30.2192 20.0374 29.8913 19.8511 29.6C19.7985 29.5041 19.7211 29.424 19.6269 29.3682C19.5327 29.3125 19.4253 29.2831 19.3158 29.2831C19.2064 29.2831 19.099 29.3125 19.0048 29.3682C18.9106 29.424 18.8332 29.5041 18.7806 29.6C18.5949 29.9018 18.4753 30.2396 18.4296 30.5909C18.3383 31.1138 18.2958 31.644 18.3028 32.1747C18.2954 32.6858 18.3378 33.1965 18.4296 33.6994Z" fill="white"/>
<path d="M22.4935 30.0189C22.8045 29.443 23.294 28.9834 23.8885 28.7095C24.5845 28.4073 25.3392 28.2642 26.0975 28.2907V29.4379C25.1891 29.4379 24.4961 29.665 24.0153 30.1251C23.5346 30.5852 23.2928 31.2665 23.2928 32.1896C23.2928 33.1127 23.5317 33.7232 24.0124 34.1538C24.4931 34.5844 25.1921 34.8026 26.0975 34.8026V35.9351C24.7939 35.9351 23.7882 35.6205 23.0804 34.9914C22.3726 34.3622 22.0187 33.4234 22.0187 32.1748C21.9907 31.4275 22.1541 30.6854 22.4935 30.0189Z" fill="white"/>
<path d="M26.7819 30.0214C27.0931 29.4445 27.5839 28.9848 28.1799 28.7119C28.8712 28.407 29.6217 28.2599 30.377 28.2813V29.4286C29.4716 29.4286 28.7786 29.6557 28.2949 30.1158C27.8112 30.5758 27.5723 31.2689 27.5723 32.1773C27.5723 33.0856 27.8112 33.7109 28.2919 34.1415C28.7727 34.5721 29.4716 34.7903 30.3741 34.7903V35.9375C29.0705 35.9375 28.0648 35.623 27.357 34.9938C26.6492 34.3646 26.2953 33.4258 26.2953 32.1773C26.2709 31.4289 26.4384 30.6867 26.7819 30.0214Z" fill="white"/>
<path d="M32.2497 28.2926V31.0207L34.4144 29.1951L35.6885 28.1216V35.937H34.4144V30.7346L32.2497 32.5602V35.937H30.9727V28.2926H32.2497Z" fill="white"/>
<path d="M37.5613 28.2911V31.0192L39.7261 29.1936L40.9941 28.126V35.9355H39.7201V30.7331L37.5554 32.5587V35.9355H36.2871V28.2911H37.5613Z" fill="white"/>
</g>
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

      const selectedFromUrl = params.get("pvzId");
      const pvzIndex = ensurePvzIndex();
      const selectedPoint = selectedFromUrl
        ? pvzIndex.get(selectedFromUrl)
        : undefined;

      const urlLat = Number(params.get("lat"));
      const urlLon = Number(params.get("lon"));
      const urlHasCenter = Number.isFinite(urlLat) && Number.isFinite(urlLon);

      const centerLat =
        selectedPoint?.lat ?? (urlHasCenter ? urlLat : 55.751244);
      const centerLon =
        selectedPoint?.lon ?? (urlHasCenter ? urlLon : 37.618423);

      const hasMarker = !selectedPoint && urlHasCenter;
      const hasSelectedPvz = Boolean(selectedPoint);

      const initialZoom = hasSelectedPvz ? 14 : hasMarker ? 12 : 10;

      const map = L.map(el, {
        zoomControl: false,
        attributionControl: false,
      }).setView([centerLat, centerLon], initialZoom);

      mapRef.current = map;

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
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

      const allPoints = ensurePvzPoints();
      const markers = [];

      // Create PVZ markers once; clustering will handle zoom-out aggregation.
      for (const point of allPoints) {
        pvzProviderByIdRef.current.set(point.id, point.provider);
        const isSelected = selectedFromUrl === point.id;

        const marker = L.marker([point.lat, point.lon], {
          icon: getPvzMarkerIcon(L, point.provider, isSelected),
          keyboard: false,
          title: `${point.provider} — ${point.address}`,
        }).on("click", () => {
          selectPvzOnMap(point.id);
        });

        pvzMarkersRef.current.set(point.id, marker);

        markers.push(marker);
      }

      const clusterAny = clusterGroup;

      if (clusterAny.addLayers) {
        clusterAny.addLayers(markers);
      } else if (clusterAny.addLayer) {
        for (const m of markers) clusterAny.addLayer(m);
      } else {
        for (const m of markers) m.addTo(clusterGroup);
      }

      // Do not add any non-PVZ marker when coming from Search.

      if (hasSelectedPvz && selectedFromUrl) {
        openPvzPopup(selectedFromUrl);
      }
    };

    void init();

    return () => {
      cancelled = true;
    };
  }, [
    step,
    searchParamsKey,
    destroyMap,
    ensurePvzIndex,
    ensurePvzPoints,
    getPvzMarkerIcon,
    openPvzPopup,
    selectPvzOnMap,
  ]);

  useEffect(() => {
    if (step !== "map") return;
    const L = leafletRef.current;
    if (!L) return;

    const prev = prevSelectedPvzIdRef.current;
    if (prev && prev !== selectedPvzId) {
      const prevMarker = pvzMarkersRef.current.get(prev);
      const prevProvider = pvzProviderByIdRef.current.get(prev);
      if (prevMarker && prevProvider) {
        try {
          prevMarker.setIcon(getPvzMarkerIcon(L, prevProvider, false));
        } catch {
          // ignore
        }
      }
    }

    if (selectedPvzId) {
      const marker = pvzMarkersRef.current.get(selectedPvzId);
      const provider = pvzProviderByIdRef.current.get(selectedPvzId);
      if (marker && provider) {
        try {
          marker.setIcon(getPvzMarkerIcon(L, provider, true));
        } catch {
          // ignore
        }
      }
    }

    prevSelectedPvzIdRef.current = selectedPvzId;
  }, [step, selectedPvzId, getPvzMarkerIcon]);

  useEffect(() => {
    if (step !== "map") return;

    if (isUserTracking) return;

    const L = leafletRef.current;
    const map = mapRef.current;
    if (!L || !map) return;

    const params = new URLSearchParams(searchParamsKey);

    const selectedFromUrl = params.get("pvzId");
    const pvzIndex = ensurePvzIndex();
    const selectedPoint = selectedFromUrl
      ? pvzIndex.get(selectedFromUrl)
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

    // Do not add any non-PVZ marker when coming from Search.

    if (hasSelectedPvz && selectedFromUrl) {
      openPvzPopup(selectedFromUrl);
    }
  }, [ensurePvzIndex, openPvzPopup, step, searchParamsKey, isUserTracking]);

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
    const ProviderIcon = ({ provider }) => {
      if (provider === "CDEK") {
        return (
          <svg
            width="22"
            height="22"
            viewBox="0 0 22 22"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              fillRule="evenodd"
              clipRule="evenodd"
              d="M10.9998 0C17.0748 0 21.9999 4.9248 21.9999 10.9998C21.9999 17.0748 17.0748 21.9996 10.9998 21.9996C4.92461 21.9996 0 17.0748 0 10.9998C0 4.9248 4.92461 0 10.9998 0ZM4.83866 5.23205C4.91287 5.23205 4.98356 5.24751 5.04732 5.27531L5.04818 5.2745C5.36689 5.40123 5.74373 5.53277 6.06687 5.61181C7.38586 5.9391 8.73303 6.14343 10.1899 6.19447C12.3953 6.27812 14.8101 6.2187 17.6114 6.19946L17.6142 6.19924H17.6276V6.19905C17.9162 6.19905 18.1498 6.43285 18.1498 6.72127C18.1498 6.96528 17.9824 7.17022 17.7559 7.22755C13.127 8.89181 9.26192 11.1715 6.26782 15.2743C6.04574 15.5802 5.81695 15.8973 5.61114 16.2159C5.60508 16.2259 5.59921 16.2356 5.59254 16.2452L5.59211 16.2458C5.49782 16.3818 5.34075 16.4709 5.16256 16.4709C4.8742 16.4709 4.64038 16.2371 4.64038 15.9487C4.64038 15.92 4.64287 15.892 4.64706 15.8646L4.64855 15.8563C5.01661 13.703 5.49219 11.5942 6.37785 9.62646C5.75337 8.64961 5.01365 7.52637 4.36933 5.98785L4.3708 5.98618C4.33609 5.91631 4.31644 5.83765 4.31644 5.75423C4.31644 5.46586 4.55024 5.23205 4.83866 5.23205ZM6.78646 18.3597C6.77287 18.3866 6.75717 18.4126 6.73943 18.4367V18.4369C6.64447 18.566 6.49118 18.6502 6.31822 18.6502C6.03006 18.6502 5.79624 18.4164 5.79624 18.1281C5.79624 18.0299 5.8232 17.9385 5.87027 17.8601H5.87008L5.87193 17.8574L6.29796 17.16C9.33305 12.4564 13.1909 10.0437 18.1813 8.24433C18.215 8.22784 18.2506 8.21463 18.2879 8.20566H18.2886C18.3279 8.19622 18.3687 8.19121 18.4107 8.19121C18.6991 8.19121 18.9329 8.42501 18.9329 8.71343C18.9329 8.93173 18.7987 9.11893 18.6084 9.19673V9.19692L18.6048 9.19816C18.5931 9.20279 18.5812 9.20718 18.569 9.21094C13.4485 11.0418 9.80966 13.3741 6.78646 18.3597Z"
              fill="#2D2D2D"
            />
          </svg>
        );
      }

      if (provider === "Boxberry") {
        return (
          <svg
            width="22"
            height="22"
            viewBox="0 0 22 22"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <rect width="22" height="22" rx="11" fill="#2D2D2D" />
            <path
              d="M12.4593 11.0001C12.4593 11.828 11.8058 12.4992 10.9996 12.4992C10.1935 12.4992 9.53996 11.828 9.53996 11.0001C9.53996 10.1722 10.1935 9.501 10.9996 9.501C11.8058 9.501 12.4593 10.1722 12.4593 11.0001Z"
              fill="white"
            />
            <path
              d="M9.98908 8.52082C9.98908 9.34875 9.33558 10.0199 8.52943 10.0199C7.72329 10.0199 7.06978 9.34875 7.06978 8.52082C7.06978 7.69289 7.72329 7.02172 8.52943 7.02172C9.33558 7.02172 9.98908 7.69289 9.98908 8.52082Z"
              fill="white"
            />
            <path
              d="M7.51891 11.0001C7.51891 11.828 6.8654 12.4992 6.05926 12.4992C5.25312 12.4992 4.59961 11.828 4.59961 11.0001C4.59961 10.1722 5.25312 9.501 6.05926 9.501C6.8654 9.501 7.51891 10.1722 7.51891 11.0001Z"
              fill="white"
            />
            <path
              d="M12.4593 15.901C12.4593 16.7289 11.8058 17.4001 10.9996 17.4001C10.1935 17.4001 9.53996 16.7289 9.53996 15.901C9.53996 15.0731 10.1935 14.4019 10.9996 14.4019C11.8058 14.4019 12.4593 15.0731 12.4593 15.901Z"
              fill="white"
            />
            <path
              d="M9.98908 13.4217C9.98908 14.2496 9.33558 14.9208 8.52943 14.9208C7.72329 14.9208 7.06978 14.2496 7.06978 13.4217C7.06978 12.5938 7.72329 11.9226 8.52943 11.9226C9.33558 11.9226 9.98908 12.5938 9.98908 13.4217Z"
              fill="white"
            />
            <path
              d="M14.9294 13.4217C14.9294 14.2496 14.2759 14.9208 13.4698 14.9208C12.6636 14.9208 12.0101 14.2496 12.0101 13.4217C12.0101 12.5938 12.6636 11.9226 13.4698 11.9226C14.2759 11.9226 14.9294 12.5938 14.9294 13.4217Z"
              fill="white"
            />
            <path
              d="M17.3996 11.0001C17.3996 11.828 16.7461 12.4992 15.94 12.4992C15.1338 12.4992 14.4803 11.828 14.4803 11.0001C14.4803 10.1722 15.1338 9.501 15.94 9.501C16.7461 9.501 17.3996 10.1722 17.3996 11.0001Z"
              fill="white"
            />
            <path
              d="M14.9294 8.52082C14.9294 9.34875 14.2759 10.0199 13.4698 10.0199C12.6636 10.0199 12.0101 9.34875 12.0101 8.52082C12.0101 7.69289 12.6636 7.02172 13.4698 7.02172C14.2759 7.02172 14.9294 7.69289 14.9294 8.52082Z"
              fill="white"
            />
            <path
              d="M12.4593 6.0992C12.4593 6.92713 11.8058 7.5983 10.9996 7.5983C10.1935 7.5983 9.53996 6.92713 9.53996 6.0992C9.53996 5.27127 10.1935 4.6001 10.9996 4.6001C11.8058 4.6001 12.4593 5.27127 12.4593 6.0992Z"
              fill="white"
            />
          </svg>
        );
      }

      if (provider === "Яндекс Доставка") {
        return (
          <svg
            width="22"
            height="22"
            viewBox="0 0 22 22"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              fillRule="evenodd"
              clipRule="evenodd"
              d="M9.39303 0.0503741C7.03646 0.423252 5.04356 1.42068 3.30032 3.09983C1.75064 4.5926 0.83489 6.17798 0.217332 8.43709C-0.0956258 9.58236 -0.0649481 12.5231 0.272963 13.7541C1.85824 19.53 7.59415 23.0175 13.3994 21.735C15.3693 21.2998 17.0525 20.3831 18.5916 18.907C23.0601 14.6219 23.1459 7.62078 18.7838 3.22664C17.4304 1.86331 15.5856 0.794872 13.7428 0.307306C12.8406 0.0686694 10.2464 -0.0845525 9.39303 0.0503741ZM14.7158 11.067V17.5847H13.5711H12.4264V11.8539V6.1231L11.4248 6.19937C9.45839 6.34893 8.59163 7.11401 8.61567 8.67881C8.62323 9.16592 8.70816 9.62204 8.85033 9.94003C9.1056 10.5104 9.98426 11.3746 11.0242 12.078C11.4178 12.3442 11.7367 12.5987 11.733 12.6435C11.7293 12.6883 10.9954 13.8056 10.1018 15.1262L8.47728 17.5275L7.30397 17.5601C6.58523 17.5801 6.13067 17.5489 6.13067 17.4797C6.13067 17.4175 6.76952 16.4244 7.55043 15.2727L8.97007 13.179L8.0708 12.3478C7.39738 11.7254 7.07664 11.3243 6.79413 10.7511C6.43985 10.0323 6.41684 9.91213 6.41684 8.78253C6.41684 7.72347 6.45267 7.50312 6.71675 6.94078C7.1072 6.10892 7.7148 5.51421 8.59404 5.10326C9.59484 4.63536 10.0244 4.57602 12.5123 4.56195L14.7158 4.54938V11.067Z"
              fill="#2D2D2D"
            />
          </svg>
        );
      }

      return (
        <svg
          width="22"
          height="22"
          viewBox="0 0 22 22"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <rect width="22" height="22" rx="11" fill="#2D2D2D" />
          <mask
            id="mask0_0_11784"
            style={{ maskType: "luminance" }}
            maskUnits="userSpaceOnUse"
            x="2"
            y="5"
            width="18"
            height="12"
          >
            <path
              d="M19.2286 5.98535H2.77148V16.015H19.2286V5.98535Z"
              fill="white"
            />
          </mask>
          <g mask="url(#mask0_0_11784)">
            <path
              d="M5.54323 6.05957V10.5526H4.79439V6.70614H3.52032V10.5526H2.77148V6.05957H5.54323Z"
              fill="white"
            />
            <path
              d="M6.89558 10.3749C6.67125 10.1688 6.50809 9.90492 6.42408 9.61216C6.30112 9.20128 6.24264 8.77383 6.25074 8.34503C6.24281 7.90427 6.30124 7.46484 6.42408 7.04149C6.50658 6.73909 6.66952 6.46472 6.89558 6.24758C7.09322 6.07805 7.34502 5.98486 7.60542 5.98486C7.8658 5.98486 8.1176 6.07805 8.31525 6.24758C8.54252 6.46277 8.7052 6.73712 8.78502 7.03975C8.90803 7.46367 8.96646 7.90369 8.95836 8.34503C8.96641 8.7744 8.90793 9.20242 8.78502 9.61389C8.70315 9.90678 8.54105 10.171 8.31699 10.3766C8.11543 10.5391 7.86432 10.6277 7.60542 10.6277C7.3465 10.6277 7.09539 10.5391 6.89385 10.3766L6.89558 10.3749ZM7.07932 9.23773C7.10861 9.43367 7.18082 9.62071 7.2908 9.7855C7.32543 9.83738 7.37198 9.88019 7.42657 9.91034C7.48117 9.94051 7.54221 9.95714 7.60455 9.95884C7.79002 9.95884 7.93563 9.82363 8.04311 9.55322C8.16747 9.16134 8.22147 8.75053 8.20258 8.33982C8.20734 8.02738 8.18298 7.71516 8.12978 7.40724C8.10182 7.20478 8.03025 7.01079 7.92003 6.83868C7.8891 6.78228 7.84357 6.73523 7.78823 6.70245C7.73288 6.66968 7.66974 6.65239 7.60542 6.65239C7.54109 6.65239 7.47794 6.66968 7.42259 6.70245C7.36725 6.73523 7.32172 6.78228 7.2908 6.83868C7.1819 7.01098 7.1099 7.20398 7.07932 7.40551C7.02548 7.71279 7.00054 8.02442 7.00479 8.33635C7.00004 8.63853 7.02501 8.94044 7.07932 9.23773Z"
              fill="white"
            />
            <path
              d="M11.4319 6.05957V7.7826H11.0349C10.891 7.79049 10.7473 7.76436 10.6154 7.70633C10.5113 7.65107 10.4316 7.55898 10.3918 7.44804C10.3389 7.29371 10.3148 7.13094 10.3208 6.96789V6.05957H9.57191V6.96442C9.55014 7.35474 9.66677 7.74023 9.90127 8.05301C10.0244 8.18977 10.177 8.29675 10.3476 8.36583C10.5182 8.43489 10.7023 8.46426 10.8859 8.4517H11.4319V10.5526H12.1807V6.05957H11.4319Z"
              fill="white"
            />
            <path
              d="M15.4645 6.70614H14.5857V10.5526H13.8369V6.70614H12.958V6.05957H15.4645V6.70614Z"
              fill="white"
            />
            <path
              d="M16.973 6.05895H17.5728C17.8199 6.0456 18.0655 6.10593 18.2783 6.23229C18.464 6.3564 18.6083 6.5333 18.6926 6.74019C18.7957 6.99685 18.8605 7.26726 18.885 7.54276L19.2317 10.5433H18.4829L18.2402 8.44761H16.9695V10.552H16.2207V6.05895H16.973ZM16.973 7.80971H18.1691L18.138 7.55142C18.1241 7.38546 18.0897 7.22186 18.0356 7.06434C17.9977 6.95835 17.9233 6.86927 17.8258 6.81299C17.7001 6.75271 17.5612 6.72528 17.4219 6.73325H16.973V7.80971Z"
              fill="white"
            />
            <path
              d="M3.5966 11.4472C3.84627 11.4406 4.0927 11.5049 4.3073 11.6327C4.51771 11.7666 4.68174 11.9621 4.77706 12.1926C4.89883 12.4863 4.95787 12.8022 4.9504 13.12C4.95811 13.4206 4.90444 13.7197 4.79266 13.9988C4.70985 14.2133 4.57598 14.4043 4.40264 14.5553C4.28543 14.6657 4.13343 14.7319 3.97275 14.7425C3.88952 14.7483 3.80602 14.7358 3.72815 14.7059C3.65028 14.6759 3.57993 14.6292 3.52206 14.5691V15.9403H2.77148V11.4472H3.5966ZM3.56366 13.7735C3.58213 13.8538 3.62025 13.9282 3.6746 13.9902C3.69231 14.012 3.71445 14.0297 3.73956 14.0423C3.76466 14.0548 3.79216 14.0619 3.82021 14.063C3.886 14.0593 3.94796 14.0308 3.99355 13.9832C4.06356 13.9105 4.1137 13.8209 4.13915 13.7232C4.18127 13.5739 4.20056 13.419 4.19636 13.2639C4.19636 12.8444 4.14609 12.548 4.04209 12.3746C3.99951 12.2945 3.9354 12.2279 3.857 12.1823C3.7786 12.1366 3.68901 12.1138 3.59833 12.1163H3.52206V13.4268C3.51975 13.5437 3.53375 13.6604 3.56366 13.7735Z"
              fill="white"
            />
            <path
              d="M5.77743 15.7603C5.55212 15.5544 5.38881 15.2897 5.30594 14.9959C5.18286 14.585 5.12438 14.1576 5.1326 13.7288C5.12465 13.2886 5.18309 12.8497 5.30594 12.427C5.38774 12.1248 5.55081 11.8508 5.77743 11.6348C5.97508 11.4653 6.22687 11.3721 6.48726 11.3721C6.74766 11.3721 6.99946 11.4653 7.1971 11.6348C7.42338 11.8501 7.58591 12.1236 7.66686 12.4252C7.78974 12.8492 7.84817 13.2892 7.8402 13.7305C7.85133 14.1594 7.79577 14.5875 7.67553 14.9994C7.5941 15.2924 7.43193 15.5567 7.2075 15.7621C7.0065 15.9258 6.75518 16.0152 6.49593 16.0152C6.23668 16.0152 5.98537 15.9258 5.78437 15.7621L5.77743 15.7603ZM5.9629 14.6249C5.9933 14.816 6.06487 14.9982 6.17265 15.1588C6.20694 15.2103 6.25295 15.2528 6.30689 15.2829C6.36084 15.313 6.42118 15.3299 6.48293 15.3322C6.66783 15.3322 6.81344 15.197 6.91976 14.9266C7.04583 14.535 7.10044 14.124 7.08096 13.7132C7.08568 13.4007 7.0613 13.0885 7.00816 12.7806C6.9794 12.5794 6.90788 12.3867 6.79841 12.2155C6.76749 12.1591 6.72196 12.112 6.66662 12.0793C6.61127 12.0465 6.54813 12.0292 6.48379 12.0292C6.41948 12.0292 6.35633 12.0465 6.30098 12.0793C6.24564 12.112 6.20011 12.1591 6.16918 12.2155C6.06008 12.3929 5.98977 12.5914 5.9629 12.7979C5.90922 13.1052 5.88427 13.4168 5.88837 13.7288C5.88401 14.0292 5.90897 14.3294 5.9629 14.6249Z"
              fill="white"
            />
            <path
              d="M8.35121 12.4619C8.53398 12.1234 8.82169 11.8533 9.17111 11.6923C9.58019 11.5147 10.0238 11.4306 10.4695 11.4462V12.1205C9.93556 12.1205 9.5282 12.2539 9.24565 12.5243C8.9631 12.7948 8.82096 13.1952 8.82096 13.7378C8.82096 14.2803 8.96138 14.6391 9.24393 14.8922C9.52646 15.1453 9.93728 15.2736 10.4695 15.2736V15.9392C9.70328 15.9392 9.11217 15.7543 8.69616 15.3845C8.28013 15.0147 8.07212 14.4629 8.07212 13.7291C8.05565 13.2898 8.15173 12.8537 8.35121 12.4619Z"
              fill="white"
            />
            <path
              d="M10.8723 12.4629C11.0552 12.1238 11.3437 11.8536 11.694 11.6933C12.1003 11.514 12.5415 11.4276 12.9854 11.4402V12.1145C12.4532 12.1145 12.0459 12.2479 11.7616 12.5184C11.4773 12.7888 11.3369 13.1961 11.3369 13.73C11.3369 14.2639 11.4773 14.6314 11.7599 14.8845C12.0424 15.1376 12.4532 15.2658 12.9837 15.2658V15.9401C12.2175 15.9401 11.6264 15.7552 11.2104 15.3854C10.7943 15.0157 10.5863 14.4638 10.5863 13.73C10.572 13.2902 10.6705 12.854 10.8723 12.4629Z"
              fill="white"
            />
            <path
              d="M14.0855 11.4472V13.0506L15.3579 11.9776L16.1067 11.3467V15.9403H15.3579V12.8825L14.0855 13.9555V15.9403H13.335V11.4472H14.0855Z"
              fill="white"
            />
            <path
              d="M17.2079 11.4462V13.0496L18.4802 11.9766L19.2255 11.3491V15.9392H18.4767V12.8815L17.2044 13.9545V15.9392H16.459V11.4462H17.2079Z"
              fill="white"
            />
          </g>
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
            const isOn = activeProvider === p;
            return (
              <button
                key={p}
                type="button"
                aria-pressed={isOn}
                onClick={() => setActiveProvider(p)}
                className={cn(
                  styles.providerChip,
                  isOn
                    ? styles.providerChipActive
                    : styles.providerChipInactive,
                )}
              >
                <span className={cn(styles.c14, styles.tw9)}>
                  <ProviderIcon provider={p} />
                </span>
                <span className={cn(styles.c15, styles.nowrap)}>
                  {p === "Яндекс Доставка"
                    ? "Яндекс"
                    : p === "Почта России"
                      ? "Почта"
                      : p}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    );

    return (
      <div className={styles.c16}>
        <div className={cn(styles.c17, styles.tw10)}>
          <div id="pickup-leaflet-map" className={styles.c18} />

          <button
            type="button"
            aria-label="Определить моё местоположение"
            aria-pressed={isUserTracking}
            onClick={() =>
              isUserTracking ? stopUserTracking() : startUserTracking()
            }
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
                    <div className={cn(styles.c30)}>{selectedPvz.provider}</div>
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
                      <div className={styles.c36}>{selectedPvz.address}</div>
                    </div>

                    <div className={cn(styles.c37, styles.tw22)}>
                      <CalendarDays className={cn(styles.c38, styles.tw23)} />
                      <div className={styles.c39}>
                        {selectedPvz.deliveryText}
                      </div>
                    </div>

                    <div className={cn(styles.c40, styles.tw24)}>
                      <Clock className={cn(styles.c41, styles.tw25)} />
                      <div className={cn(styles.c42, styles.tw26)}>
                        <div>Понедельник</div>
                        <div className={cn(styles.c43, styles.tw27)}>
                          08:30–20:00
                        </div>

                        <div>Вторник</div>
                        <div className={cn(styles.c44, styles.tw28)}>
                          08:30–20:00
                        </div>

                        <div>Среда</div>
                        <div className={cn(styles.c45, styles.tw29)}>
                          08:30–20:00
                        </div>

                        <div>Четверг</div>
                        <div className={cn(styles.c46, styles.tw30)}>
                          08:30–20:00
                        </div>

                        <div>Пятница</div>
                        <div className={cn(styles.c47, styles.tw31)}>
                          08:30–20:00
                        </div>

                        <div>Суббота</div>
                        <div className={cn(styles.c48, styles.tw32)}>
                          08:30–20:00
                        </div>

                        <div>Воскресенье</div>
                        <div className={cn(styles.c49, styles.tw33)}>
                          08:30–20:00
                        </div>
                      </div>
                    </div>

                    <div className={cn(styles.c50, styles.tw34)}>
                      <Hourglass className={cn(styles.c51, styles.tw35)} />
                      <div className={styles.c52}>Срок хранения — 7 дней</div>
                    </div>

                    <div className={cn(styles.c53, styles.tw36)}>
                      <CreditCard className={cn(styles.c54, styles.tw37)} />
                      <div className={styles.c55}>{selectedPvz.priceText}</div>
                    </div>
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
                        params.set("pickupPvzId", selectedPvz.id);
                        params.set("pickupProvider", selectedPvz.provider);
                        params.set("pickupAddress", selectedPvz.address);
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
                <div className={cn(styles.c84)}>{p.provider}</div>
                <div className={styles.c85}>{p.address}</div>
                <div className={styles.c86}>{p.deliveryText}</div>
                <div className={styles.c87}>{p.priceText}</div>
              </div>
            </button>
          );
        })}

        {filteredPvz.length === 0 ? (
          <div className={styles.c88}>Ничего не найдено</div>
        ) : null}
      </div>
    </div>
  );
}
