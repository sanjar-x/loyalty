"use client";
import React, { useCallback, useMemo } from "react";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import BrandsSection from "@/components/blocks/favorites/BrandsSection";
import EmptyState from "@/components/blocks/favorites/EmptyState";
import ProductSection from "@/components/blocks/product/ProductSection";
import styles from "./page.module.css";

import {
  buildBackendAssetUrl,
  buildBrandLogoUrl,
  buildProductPhotoUrl,
} from "@/lib/format/backendAssets";

function uniqStrings(arr) {
  const out = [];
  const seen = new Set();
  for (const v of arr) {
    const s = typeof v === "string" ? v : "";
    if (!s) continue;
    if (seen.has(s)) continue;
    seen.add(s);
    out.push(s);
  }
  return out;
}

function getBrandLogoCandidates(brand) {
  const id = brand?.id;
  const logo = brand?.logo;

  const byPath = buildBrandLogoUrl(logo);

  const byId =
    id != null
      ? `/api/backend/api/v1/brands/${encodeURIComponent(String(id))}/logo`
      : "";

  return uniqStrings([
    byPath,
    byId,
    buildBackendAssetUrl(logo),
    buildBackendAssetUrl(logo, ["media"]),
    buildBackendAssetUrl(logo, ["static"]),
    buildBackendAssetUrl(logo, ["uploads"]),
  ]);
}

const EMPTY_SET = new Set();
const NOOP = () => {};

export default function FavoritesPage() {
  const brandsData = [];
  const brandFav = { favoriteItemIds: EMPTY_SET, toggleFavorite: NOOP };
  const productFav = { favoriteItemIds: EMPTY_SET, toggleFavorite: NOOP };

  const brands = useMemo(() => {
    const rows = Array.isArray(brandsData) ? brandsData : [];
    return rows
      .map((b) => {
        const id = b?.id;
        const name = b?.name ?? "";
        const candidates = getBrandLogoCandidates(b);
        const image = candidates[0] || "";
        const imageFallbacks = candidates.slice(1);
        return {
          id,
          name,
          image,
          imageFallbacks,
          isFavorite: brandFav.favoriteItemIds.has(id),
        };
      })
      .filter((b) => b.id != null);
  }, [brandFav.favoriteItemIds, brandsData]);

  const favoriteProductIds = [];

  const favoriteProductsRaw = [];
  const isFavoriteProductsLoading = false;

  const formatRub = (amount) => {
    const n = Number(amount);
    if (!Number.isFinite(n)) return "";
    const formatted = Math.round(n)
      .toString()
      .replace(/\B(?=(\d{3})+(?!\d))/g, " ");
    return `${formatted} ₽`;
  };

  const getProductPhotoCandidates = (product) => {
    const photos = Array.isArray(product?.photos) ? product.photos : [];
    const filename = photos?.[0]?.filename;
    const raw = typeof filename === "string" ? filename.trim() : "";
    if (!raw) return [];
    return [
      buildProductPhotoUrl(raw),
      buildBackendAssetUrl(raw, ["media"]),
      buildBackendAssetUrl(raw, ["static"]),
      buildBackendAssetUrl(raw, ["uploads"]),
      buildBackendAssetUrl(raw),
    ].filter(Boolean);
  };

  const favoriteProducts = useMemo(() => {
    const rows = Array.isArray(favoriteProductsRaw) ? favoriteProductsRaw : [];
    return rows
      .map((p) => {
        const id = p?.id;
        if (id == null) return null;
        const candidates = getProductPhotoCandidates(p);
        const image = candidates[0] || "";
        const imageFallbacks = candidates.slice(1);
        const brandName =
          (typeof p?.brand === "object" ? p.brand?.name : p?.brand) ??
          p?.brand_name ??
          "";
        const deliveryDate =
          typeof p?.delivery === "string" && p.delivery.trim()
            ? p.delivery.trim()
            : "";

        const serverIsFavorite =
          typeof p?.is_favourite === "boolean"
            ? p.is_favourite
            : typeof p?.is_favorite === "boolean"
              ? p.is_favorite
              : typeof p?.isFavorite === "boolean"
                ? p.isFavorite
                : null;
        return {
          id,
          name: String(p?.name ?? ""),
          brand: String(brandName || ""),
          price: formatRub(p?.price),
          image,
          imageFallbacks,
          isFavorite: Boolean(serverIsFavorite ?? true),
          deliveryDate,
        };
      })
      .filter(Boolean);
  }, [favoriteProductsRaw]);

  const forYouRaw = [];
  const isForYouLoading = false;
  const isForYouFetching = false;

  const recommendedProducts = useMemo(() => {
    const rows = Array.isArray(forYouRaw) ? forYouRaw : [];
    return (
      rows
        .map((p) => {
          const id = p?.id;
          if (id == null) return null;
          const candidates = getProductPhotoCandidates(p);
          const image = candidates[0] || "";
          const imageFallbacks = candidates.slice(1);
          const brandName =
            (typeof p?.brand === "object" ? p.brand?.name : p?.brand) ??
            p?.brand_name ??
            "";

          const serverIsFavorite =
            typeof p?.is_favourite === "boolean"
              ? p.is_favourite
              : typeof p?.is_favorite === "boolean"
                ? p.is_favorite
                : typeof p?.isFavorite === "boolean"
                  ? p.isFavorite
                  : null;
          return {
            id,
            name: String(p?.name ?? ""),
            brand: String(brandName || ""),
            price: formatRub(p?.price),
            image,
            imageFallbacks,
            isFavorite: Boolean(
              (serverIsFavorite ?? false) || productFav.favoriteItemIds.has(id),
            ),
          };
        })
        .filter(Boolean)
        // On Favorites page, 'Для вас' should suggest only non-favorited items.
        // Once user favorites an item, it should move into Favorites list.
        .filter((p) => !p.isFavorite)
    );
  }, [forYouRaw, productFav.favoriteItemIds]);

  const handleToggleBrandFavorite = useCallback(
    (id) => brandFav.toggleFavorite(id),
    [brandFav],
  );
  const handleToggleProductFavorite = useCallback(
    (id) => productFav.toggleFavorite(id),
    [productFav],
  );

  const isFavoritesBootstrapping = false;

  const hasFavorites =
    favoriteProductIds.length > 0 || brands.some((b) => b.isFavorite);

  return (
    <div className={styles.page}>
      <main className={styles.c1}>
        <div className={styles.header}>
          <Header title="Избранное" />
          {brands.some((b) => b.isFavorite) && (
            <BrandsSection
              brands={brands.filter((b) => b.isFavorite)}
              onToggleFavorite={handleToggleBrandFavorite}
            />
          )}
        </div>

        {/* Пустое состояние или товары */}
        {!hasFavorites && !isFavoritesBootstrapping ? (
          <EmptyState />
        ) : (
          <>
            {/* Секция товаров */}
            {favoriteProductIds.length > 0 && (
              <div className={styles.c2}>
                <ProductSection
                  products={favoriteProducts}
                  onToggleFavorite={handleToggleProductFavorite}
                  layout="grid"
                  isLoading={isFavoriteProductsLoading}
                />
              </div>
            )}

            {/* Пока грузим избранное (первый заход) — не показываем EmptyState, а даём скелетоны */}
            {isFavoritesBootstrapping && (
              <div className={styles.c2}>
                <ProductSection
                  products={[]}
                  onToggleFavorite={() => {}}
                  layout="grid"
                  isLoading={true}
                  skeletonCount={6}
                  hideFavoriteButton={true}
                />
              </div>
            )}
          </>
        )}
        <ProductSection
          title="Для вас"
          products={recommendedProducts}
          onToggleFavorite={handleToggleProductFavorite}
          layout="grid"
          hideFavoriteButton={false}
          isLoading={Boolean(isForYouLoading || isForYouFetching)}
          skeletonCount={6}
        />
      </main>
      <Footer />
    </div>
  );
}
