"use client";
import React, { useCallback, useMemo } from "react";
import Header from "@/components/layout/Header";
import Footer from "@/components/layout/Footer";
import BrandsSection from "@/components/blocks/favorites/BrandsSection";
import EmptyState from "@/components/blocks/favorites/EmptyState";
import ProductSection from "@/components/blocks/product/ProductSection";
import styles from "./page.module.css";

import {
  getProductPhotoCandidates,
  buildBackendAssetUrl,
  buildProductPhotoUrl,
} from "@/lib/format/product-image";
import { getBrandLogoCandidates } from "@/lib/format/brand-image";
import { formatRubPrice } from "@/lib/format/price";

interface ApiBrand {
  id?: number | string;
  name?: string;
  logo?: string;
}

interface ApiProduct {
  id?: number | string;
  name?: string;
  price?: number | string;
  brand?: string | { name?: string };
  brand_name?: string;
  delivery?: string;
  photos?: Array<string | { filename?: string; file?: string; path?: string; url?: string }>;
  is_favourite?: boolean;
  is_favorite?: boolean;
  isFavorite?: boolean;
  image?: string;
  image_url?: string;
  photo?: string;
  photo_url?: string;
}

interface BrandUi {
  id: number | string;
  name: string;
  image: string;
  imageFallbacks: string[];
  isFavorite: boolean;
}

interface ProductUi {
  id: number | string;
  name: string;
  brand: string;
  price: string;
  image: string;
  imageFallbacks: string[];
  isFavorite: boolean;
  deliveryDate: string;
}

interface FavState {
  favoriteItemIds: Set<number | string>;
  toggleFavorite: (id: number | string) => void;
}

const EMPTY_SET: Set<number | string> = new Set();
const NOOP = (): void => {};

export default function FavoritesPage(): React.JSX.Element {
  const brandsData: ApiBrand[] = [];
  const brandFav: FavState = { favoriteItemIds: EMPTY_SET, toggleFavorite: NOOP };
  const productFav: FavState = { favoriteItemIds: EMPTY_SET, toggleFavorite: NOOP };

  const brands = useMemo((): BrandUi[] => {
    const rows = Array.isArray(brandsData) ? brandsData : [];
    return rows
      .filter((b): b is ApiBrand & { id: number | string } => b?.id != null)
      .map((b) => {
        const id = b.id;
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
      });
  }, [brandFav.favoriteItemIds, brandsData]);

  const favoriteProductIds: number[] = [];

  const favoriteProductsRaw: ApiProduct[] = [];
  const isFavoriteProductsLoading = false;

  const favoriteProducts = useMemo((): ProductUi[] => {
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
          price: formatRubPrice(p?.price),
          image,
          imageFallbacks,
          isFavorite: Boolean(serverIsFavorite ?? true),
          deliveryDate,
        };
      })
      .filter((p): p is ProductUi => p !== null);
  }, [favoriteProductsRaw]);

  const forYouRaw: ApiProduct[] = [];
  const isForYouLoading = false;
  const isForYouFetching = false;

  const recommendedProducts = useMemo((): ProductUi[] => {
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
            price: formatRubPrice(p?.price),
            image,
            imageFallbacks,
            isFavorite: Boolean(
              (serverIsFavorite ?? false) || productFav.favoriteItemIds.has(id as number | string),
            ),
            deliveryDate: "",
          };
        })
        .filter((p): p is ProductUi => p !== null)
        // On Favorites page, 'Для вас' should suggest only non-favorited items.
        // Once user favorites an item, it should move into Favorites list.
        .filter((p) => !p.isFavorite)
    );
  }, [forYouRaw, productFav.favoriteItemIds]);

  const handleToggleBrandFavorite = useCallback(
    (id: number | string) => brandFav.toggleFavorite(id),
    [brandFav],
  );
  const handleToggleProductFavorite = useCallback(
    (id: number | string) => productFav.toggleFavorite(id),
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
