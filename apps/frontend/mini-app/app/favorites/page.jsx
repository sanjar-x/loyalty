'use client';
import React, { useCallback, useMemo } from 'react';

import Header from '@/components/layout/Header';
import Footer from '@/components/layout/Footer';
import BrandsSection from '@/components/blocks/favorites/BrandsSection';
import EmptyState from '@/components/blocks/favorites/EmptyState';
import ProductSection from '@/components/blocks/product/ProductSection';

import {
  useGetBrandsQuery,
  useGetForYouFeedQuery,
  useGetProductsByIdsQuery,
} from '@/lib/store/api';
import { useItemFavorites } from '@/lib/hooks/useItemFavorites';
import { mapProductCard } from '@/lib/adapters/mapProductCard';
import { resolveI18N } from '@/lib/adapters/mapStorefrontProduct';
import { brandToCarouselItem, getProductPhotoCandidates } from '@/lib/adapters/favoriteAssets';

import styles from './page.module.css';

/**
 * Favorites sahifasi. UI tarkibi (top → bottom):
 *
 *   1. Header — yagona "Избранное" sarlavhali bar
 *   2. Mahsulotlar bloki — sevimli mahsulotlar grid yoki Empty state
 *      (heart + tushuntirish), har holda card-rounded konteyner ichida
 *   3. Brendlar carousel — DOIMO ko'rsatiladi:
 *        sevimli brendlar (tepada) + populyar brendlar (limit 20)
 *      Карусель ostida "все" tugmasi `/favorites/brands`'ga olib boradi
 *   4. "Для вас" — `/api/v1/storefront/for-you` (auth bo'lsa personalized,
 *      aks holda cold-start fallback)
 *
 * Empty state (sevimlilar yo'q) holatida ham brendlar va Для вас
 * to'liq render bo'ladi — foydalanuvchi sevimli qo'shmagan bo'lsa-da
 * sahifa boy va aktivlikka chaqiruvchi bo'ladi.
 */

const POPULAR_BRANDS_LIMIT = 20;

function formatRub(amount) {
  const n = Number(amount);
  if (!Number.isFinite(n)) return '';
  return `${Math.round(n)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, ' ')} ₽`;
}

function priceToRub(price) {
  if (price == null) return null;
  if (typeof price === 'number') return Number.isFinite(price) ? price : null;
  if (typeof price === 'object') {
    const a = Number(price.amount);
    return Number.isFinite(a) ? a / 100 : null;
  }
  return null;
}

function uniqStrings(arr) {
  const seen = new Set();
  const out = [];
  for (const v of arr) {
    const s = typeof v === 'string' ? v : '';
    if (!s || seen.has(s)) continue;
    seen.add(s);
    out.push(s);
  }
  return out;
}

export default function FavoritesPage() {
  const productFav = useItemFavorites('product');
  const brandFav = useItemFavorites('brand');

  /* ─── Sevimli BRENDLAR (enriched item.brand'dan) ─── */
  const favoriteBrands = useMemo(() => {
    const rows = Array.isArray(brandFav.favorites) ? brandFav.favorites : [];
    return rows
      .map((it) => {
        const b = it?.brand;
        if (!b || typeof b !== 'object' || !b.id) return null;
        return brandToCarouselItem(b, brandFav.favoriteItemIds);
      })
      .filter(Boolean)
      .map((b) => ({ ...b, isFavorite: true })); // sevimlilar ro'yxatidan kelgan, kafolatlangan
  }, [brandFav.favorites, brandFav.favoriteItemIds]);

  /* ─── Hammasidan populyar brendlar (storefront) ─── */
  const { data: allBrandsRaw } = useGetBrandsQuery(undefined, {
    // Cache bilan ishlash — brendlar ro'yxati kam o'zgaradi (30 daqiqa
    // keepUnusedDataFor allaqachon `enhanceEndpoints`'da o'rnatilgan)
  });

  /**
   * Carousel manbai = sevimli brendlar (tepada) + sevimli emas populyar brendlar.
   * Sevimlini olib tashlasa, hech qachon ro'yxat bo'shab qolmaydi — Loylik
   * UX talab: foydalanuvchi har doim brendlarni ko'rib turadi.
   */
  const brandsCarouselSource = useMemo(() => {
    const all = Array.isArray(allBrandsRaw) ? allBrandsRaw : [];
    const favIds = brandFav.favoriteItemIds;
    const remainingSlots = Math.max(0, POPULAR_BRANDS_LIMIT - favoriteBrands.length);
    const popularNonFav = all
      .filter((b) => b && b.id && !favIds.has(b.id))
      .slice(0, remainingSlots)
      .map((b) => brandToCarouselItem(b, favIds))
      .filter(Boolean);
    return [...favoriteBrands, ...popularNonFav];
  }, [favoriteBrands, allBrandsRaw, brandFav.favoriteItemIds]);

  /* ─── Sevimli MAHSULOTLAR ─── */
  // FavoriteProductCardResponse → bulk PDP fetch (bir mahsulot bo'yicha
  // narx/brand keladi). `keepUnusedDataFor` PDP'da 5min — qayta kirishda
  // tezda renderlanadi.
  const favoriteProductSlugs = useMemo(() => {
    const rows = Array.isArray(productFav.favorites) ? productFav.favorites : [];
    return uniqStrings(
      rows.map((it) => (typeof it?.product?.slug === 'string' ? it.product.slug : ''))
    ).sort();
  }, [productFav.favorites]);

  const { data: enrichedProducts, isLoading: isProductsEnriching } = useGetProductsByIdsQuery(
    favoriteProductSlugs,
    {
      skip: favoriteProductSlugs.length === 0,
    }
  );

  const favoriteProducts = useMemo(() => {
    const enriched = Array.isArray(enrichedProducts) ? enrichedProducts : [];
    const bySlug = new Map();
    for (const p of enriched) {
      if (p && typeof p === 'object' && typeof p.slug === 'string') {
        bySlug.set(p.slug, p);
      }
    }

    const rows = Array.isArray(productFav.favorites) ? productFav.favorites : [];
    return rows
      .map((it) => {
        const card = it?.product;
        if (!card || !card.id || !card.slug) return null;
        const full = bySlug.get(card.slug);
        const title = (full && (full.title || full.name)) || resolveI18N(card.title_i18n, '');
        const photoSource = full ?? card;
        const candidates = getProductPhotoCandidates(photoSource);
        const brandName =
          full && typeof full.brand === 'object'
            ? (full.brand?.name ?? '')
            : (full?.brand ?? full?.brand_name ?? '');
        const priceRub = priceToRub(full?.price);
        return {
          id: card.id,
          slug: card.slug,
          name: title,
          brand: brandName,
          price: priceRub != null ? formatRub(priceRub) : '',
          image: candidates[0] || '',
          imageFallbacks: candidates.slice(1),
          isFavorite: true,
        };
      })
      .filter(Boolean);
  }, [productFav.favorites, enrichedProducts]);

  /* ─── "Для вас" tavsiyalari ─── */
  const {
    data: forYouRaw,
    isLoading: isForYouLoading,
    isFetching: isForYouFetching,
  } = useGetForYouFeedQuery({ limit: 8 });

  const recommendedProducts = useMemo(() => {
    const items = Array.isArray(forYouRaw?.items) ? forYouRaw.items : [];
    return (
      items
        .map((p) => mapProductCard(p, productFav.favoriteItemIds))
        .filter(Boolean)
        // Sevimliga qo'shilgan mahsulot yuqoridagi ro'yxatga ko'chadi —
        // bu yerda dublikat ko'rinmasin.
        .filter((p) => !p.isFavorite)
    );
  }, [forYouRaw, productFav.favoriteItemIds]);

  /* ─── Handlers ─── */
  const handleToggleProductFavorite = useCallback(
    (id) => productFav.toggleFavorite(id),
    [productFav]
  );
  const handleToggleBrandFavorite = useCallback((id) => brandFav.toggleFavorite(id), [brandFav]);

  /* ─── Bootstrap state ─── */
  const isFavoritesBootstrapping =
    Boolean(productFav.isLoading || brandFav.isLoading) &&
    favoriteProducts.length === 0 &&
    favoriteBrands.length === 0;

  const showProductsCard = favoriteProducts.length > 0 || isFavoritesBootstrapping;

  return (
    <div className={styles.page}>
      <main className={styles.c1}>
        <Header title="Избранное" />

        {/* 1. Mahsulotlar yoki empty state — har holda card konteyner ichida */}
        {showProductsCard ? (
          <div className={styles.c2}>
            <ProductSection
              products={favoriteProducts}
              onToggleFavorite={handleToggleProductFavorite}
              favoriteItemIds={productFav.favoriteItemIds}
              layout="grid"
              isLoading={isProductsEnriching || isFavoritesBootstrapping}
              skeletonCount={6}
              hideFavoriteButton={false}
            />
          </div>
        ) : (
          <div className={styles.emptyCard}>
            <EmptyState />
          </div>
        )}

        {/* 2. Brendlar — DOIMO ko'rsatiladi (sevimlilar + populyar) */}
        {brandsCarouselSource.length > 0 ? (
          <BrandsSection
            brands={brandsCarouselSource}
            onToggleFavorite={handleToggleBrandFavorite}
          />
        ) : null}

        {/* 3. Для вас — bo'sh va loading emas bo'lsa butunlay yashiriladi
            (sahifa pastida bo'sh joy qoldirmaslik uchun). Loading paytida
            skeleton ko'rsatiladi. */}
        {recommendedProducts.length > 0 || isForYouLoading || isForYouFetching ? (
          <ProductSection
            title="Для вас"
            products={recommendedProducts}
            onToggleFavorite={handleToggleProductFavorite}
            favoriteItemIds={productFav.favoriteItemIds}
            layout="grid"
            hideFavoriteButton={false}
            isLoading={Boolean(isForYouLoading || isForYouFetching)}
            skeletonCount={6}
          />
        ) : null}
      </main>
      <Footer />
    </div>
  );
}
