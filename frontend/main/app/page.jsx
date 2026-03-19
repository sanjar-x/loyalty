"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  useGetLatestPurchasedProductsQuery,
  useGetProductsQuery,
  useLazyGetProductsQuery,
} from "@/lib/store/api";

import SearchBar from "@/components/blocks/search/SearchBar";
import Footer from "@/components/layout/Footer";
import CategoryTabs from "@/components/blocks/home/CategoryTabs";
import FriendsSection from "@/components/blocks/home/FriendsSection";
import HomeDeliveryStatusCard from "@/components/blocks/home/HomeDeliveryStatusCard";
import ProductSection from "@/components/blocks/product/ProductSection";

import { useItemFavorites } from "@/lib/hooks/useItemFavorites";

import styles from "./page.module.css";

import {
  buildBackendAssetUrl,
  buildProductPhotoUrl,
} from "@/lib/format/backendAssets";

function formatRubPrice(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "";
  const rounded = Math.trunc(n);
  const formatted = rounded.toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return `${formatted} ₽`;
}

function getProductPhotoCandidates(product) {
  const photos = Array.isArray(product?.photos) ? product.photos : [];
  const filename = photos?.[0]?.filename;
  const raw = typeof filename === "string" ? filename.trim() : "";
  if (!raw) return [];

  return [
    // New API (path passed as a single encoded param, e.g. 1%2Ffile.png)
    buildProductPhotoUrl(raw),
    // Legacy/static roots (fallbacks)
    buildBackendAssetUrl(raw, ["media"]),
    buildBackendAssetUrl(raw, ["static"]),
    buildBackendAssetUrl(raw, ["uploads"]),
    buildBackendAssetUrl(raw),
  ].filter(Boolean);
}

function mapApiProductToCard(product, favoriteIds) {
  const id = product?.id;
  if (id == null) return null;

  const candidates = getProductPhotoCandidates(product);
  const image = candidates[0] || "";
  const imageFallbacks = candidates.slice(1);

  const deliveryRaw =
    typeof product?.delivery === "string" ? product.delivery : "";
  const deliveryText = deliveryRaw.trim()
    ? `Доставка: ${deliveryRaw.trim()}`
    : "";

  const serverIsFavorite =
    typeof product?.is_favourite === "boolean"
      ? product.is_favourite
      : typeof product?.is_favorite === "boolean"
        ? product.is_favorite
        : typeof product?.isFavorite === "boolean"
          ? product.isFavorite
          : null;

  return {
    id,
    name: String(product?.name ?? ""),
    price: formatRubPrice(product?.price),
    image,
    imageFallbacks,
    isFavorite: Boolean(
      (serverIsFavorite ?? false) || (favoriteIds?.has?.(id) ?? false),
    ),
    deliveryText,
  };
}

export default function Home() {
  const { favoriteItemIds, toggleFavorite } = useItemFavorites("product");

  const {
    data: latestData,
    isLoading: isLatestLoading,
    isFetching: isLatestFetching,
  } = useGetLatestPurchasedProductsQuery(10);

  const isLatestInitialLoading =
    Boolean(isLatestLoading || isLatestFetching) &&
    (!Array.isArray(latestData) || latestData.length === 0);

  const PAGE_SIZE = 10;
  const {
    data: initialProductsData,
    isLoading: isInitialProductsLoading,
    isFetching: isInitialProductsFetching,
  } = useGetProductsQuery({ skip: 0, limit: PAGE_SIZE });

  const [extraRecommendedRaw, setExtraRecommendedRaw] = useState([]);
  const [recommendedHasMore, setRecommendedHasMore] = useState(true);

  const [triggerGetProducts, productsQuery] = useLazyGetProductsQuery();
  const sentinelRef = useRef(null);

  const mergeUniqueById = useCallback((prev, next) => {
    const out = Array.isArray(prev) ? [...prev] : [];
    const seen = new Set(
      out
        .map((p) => (p && typeof p === "object" ? p.id : null))
        .filter((id) => id != null),
    );
    const rows = Array.isArray(next) ? next : [];
    for (const p of rows) {
      const id = p && typeof p === "object" ? p.id : null;
      if (id == null) continue;
      if (seen.has(id)) continue;
      seen.add(id);
      out.push(p);
    }
    return out;
  }, []);

  const loadMoreRecommended = useCallback(async () => {
    const baseArr = Array.isArray(initialProductsData)
      ? initialProductsData
      : [];
    const extraArr = Array.isArray(extraRecommendedRaw)
      ? extraRecommendedRaw
      : [];
    const currentSkip = baseArr.length + extraArr.length;

    // If initial page isn't full, there's likely nothing more.
    if (baseArr.length < PAGE_SIZE) return;
    if (!recommendedHasMore) return;
    if (productsQuery.isFetching) return;
    try {
      const rows = await triggerGetProducts({
        skip: currentSkip,
        limit: PAGE_SIZE,
      }).unwrap();
      const arr = Array.isArray(rows) ? rows : [];
      setExtraRecommendedRaw((prev) => mergeUniqueById(prev, arr));
      setRecommendedHasMore(arr.length === PAGE_SIZE);
    } catch {
      setRecommendedHasMore(false);
    }
  }, [
    PAGE_SIZE,
    extraRecommendedRaw,
    initialProductsData,
    mergeUniqueById,
    productsQuery.isFetching,
    recommendedHasMore,
    triggerGetProducts,
  ]);

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el) return;
    const baseArr = Array.isArray(initialProductsData)
      ? initialProductsData
      : [];
    if (baseArr.length < PAGE_SIZE) return;
    if (!recommendedHasMore) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const first = entries[0];
        if (!first?.isIntersecting) return;
        loadMoreRecommended();
      },
      {
        root: null,
        rootMargin: "200px",
        threshold: 0.01,
      },
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [PAGE_SIZE, initialProductsData, loadMoreRecommended, recommendedHasMore]);

  const recentProducts = useMemo(() => {
    const rows = Array.isArray(latestData) ? latestData : [];
    return rows
      .map((p) => mapApiProductToCard(p, favoriteItemIds))
      .filter(Boolean);
  }, [favoriteItemIds, latestData]);

  const recommendedProducts = useMemo(() => {
    const baseArr = Array.isArray(initialProductsData)
      ? initialProductsData
      : [];
    const extraArr = Array.isArray(extraRecommendedRaw)
      ? extraRecommendedRaw
      : [];
    const merged = mergeUniqueById(baseArr, extraArr);
    return merged
      .map((p) => mapApiProductToCard(p, favoriteItemIds))
      .filter(Boolean);
  }, [
    extraRecommendedRaw,
    favoriteItemIds,
    initialProductsData,
    mergeUniqueById,
  ]);

  const isRecommendedInitialLoading =
    (isInitialProductsLoading || isInitialProductsFetching) &&
    (!Array.isArray(initialProductsData) || initialProductsData.length === 0);

  const isRecommendedLoadingMore =
    productsQuery.isFetching &&
    Array.isArray(initialProductsData) &&
    initialProductsData.length > 0;

  return (
    <div
      className="lm-app-bg"
      style={{ minHeight: "var(--tg-viewport-height)" }}
    >
      <div className={styles.container}>
        <SearchBar navigateOnFocusTo="/search" readOnly />
        <CategoryTabs />
        <FriendsSection />

        <div className={styles.sectionSpacing}>
          <HomeDeliveryStatusCard />
          <HomeDeliveryStatusCard />
        </div>

        <ProductSection
          title="Только что купили"
          products={recentProducts}
          onToggleFavorite={toggleFavorite}
          layout="horizontal"
          isLoading={isLatestInitialLoading}
          skeletonCount={5}
        />

        <ProductSection
          title="Для вас"
          products={recommendedProducts}
          onToggleFavorite={toggleFavorite}
          layout="grid"
          isLoading={isRecommendedInitialLoading}
          skeletonCount={6}
        />

        {isRecommendedLoadingMore ? (
          <div className={styles.loadMore} aria-live="polite" aria-busy="true">
            <div className={styles.spinner} aria-hidden="true" />
            <div className={styles.loadMoreText}>Загрузка…</div>
          </div>
        ) : null}

        <div ref={sentinelRef} style={{ height: 1 }} aria-hidden="true" />

        <Footer />
      </div>
    </div>
  );
}
