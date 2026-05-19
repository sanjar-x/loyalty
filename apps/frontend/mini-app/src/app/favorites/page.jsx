'use client';
import React, { useCallback, useMemo } from 'react';

import Header from '@/widgets/Header';
import Footer from '@/widgets/Footer';
import BrandsSection from '@/features/favorites/ui/BrandsSection';
import EmptyState from '@/features/favorites/ui/EmptyState';
import { ProductSection } from '@/entities/product';

import { useGetBrandsQuery } from '@/entities/brand';
import { useGetForYouFeedQuery, useGetProductsByIdsQuery } from '@/entities/product';
import { useItemFavorites } from '@/features/favorites';
import { mapProductCard } from '@/entities/product';
import { resolveI18N } from '@/shared/lib/i18n';
import {
  brandToCarouselItem,
  getProductPhotoCandidates,
} from '@/entities/favorite';

import styles from './page.module.css';

/**
 * Favorites page. UI structure (top → bottom):
 *
 *   1. Header — a single bar with the "Избранное" title
 *   2. Products block — favorite products grid or an Empty state
 *      (heart + explanation), inside a card-rounded container either way
 *   3. Brands carousel — ALWAYS shown:
 *        favorite brands (top) + popular brands (limit 20)
 *      Below the carousel a "все" button leads to `/favorites/brands`
 *   4. "Для вас" — `/api/v1/storefront/for-you` (personalized when
 *      authenticated, cold-start fallback otherwise)
 *
 * In the empty state (no favorites) the brands and "Для вас" sections
 * still render fully — even if the user hasn't added any favorites,
 * the page is rich and invites engagement.
 */

const POPULAR_BRANDS_LIMIT = 20;

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

  /* ─── Favorite BRANDS (from enriched item.brand) ─── */
  const favoriteBrands = useMemo(() => {
    const rows = Array.isArray(brandFav.favorites) ? brandFav.favorites : [];
    return rows
      .map((it) => {
        const b = it?.brand;
        if (!b || typeof b !== 'object' || !b.id) return null;
        return brandToCarouselItem(b, brandFav.favoriteItemIds);
      })
      .filter(Boolean)
      .map((b) => ({ ...b, isFavorite: true })); // came from the favorites list, guaranteed
  }, [brandFav.favorites, brandFav.favoriteItemIds]);

  /* ─── Popular brands overall (storefront) ─── */
  const { data: allBrandsRaw } = useGetBrandsQuery(undefined, {
    // Cache-friendly — the brands list changes rarely (30 min
    // keepUnusedDataFor is already set in `enhanceEndpoints`)
  });

  /**
   * Carousel source = favorite brands (top) + non-favorite popular brands.
   * If a favorite is removed, the list never goes empty — Loyalty UX
   * requirement: the user always sees brands.
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

  /* ─── Favorite PRODUCTS ─── */
  // FavoriteProductCardResponse → bulk PDP fetch (price/brand come per
  // product). `keepUnusedDataFor` on the PDP is 5min — re-entry renders
  // quickly.
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

  /* ─── "Для вас" recommendations ─── */
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
        // A product added to favorites moves to the list above —
        // avoid showing a duplicate here.
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

        {/* 1. Products or empty state — inside a card container either way */}
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

        {/* 2. Brands — ALWAYS shown (favorites + popular) */}
        {brandsCarouselSource.length > 0 ? (
          <BrandsSection
            brands={brandsCarouselSource}
            onToggleFavorite={handleToggleBrandFavorite}
          />
        ) : null}

        {/* 3. Для вас — if it's empty and not loading, it's fully hidden
            (to avoid empty space at the bottom of the page). During
            loading a skeleton is shown. */}
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
