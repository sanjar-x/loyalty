'use client';
import React, { useMemo, useState } from 'react';

import Header from '@/widgets/Header';
import Footer from '@/widgets/Footer';
import FavoriteBrandsSection from '@/features/favorites/ui/brands/FavoriteBrandsSection';
import BrandsSearch from '@/features/favorites/ui/brands/BrandsSearch';
import AllBrandsList from '@/features/favorites/ui/brands/AllBrandsList';

import { useGetBrandsQuery } from '@/entities/brand';
import { useItemFavorites } from '@/features/favorites';
import { brandToCarouselItem } from '@/entities/favorite';

import styles from './page.module.css';

/**
 * `/favorites/brands` — full page with favorite brands + all brands.
 *
 * Contents:
 *   1. Header ("Бренды" title + close button)
 *   2. "Избранные" — favorite brands (vertical list, chevron right)
 *   3. "Все" — search panel + all brands alphabetically (each brand has
 *      a toggle heart)
 *
 * Empty states:
 *   - If there are no favorite brands, the "Избранные" section is hidden
 *   - If the "Все" search returns nothing, an empty list is shown
 */
export default function BrandsPage() {
  const [searchQuery, setSearchQuery] = useState('');

  const { data: brandsData } = useGetBrandsQuery();
  const { favoriteItemIds, toggleFavorite } = useItemFavorites('brand');

  const allBrands = useMemo(() => {
    const rows = Array.isArray(brandsData)
      ? brandsData
      : Array.isArray(brandsData?.items)
        ? brandsData.items
        : [];
    return rows.map((b) => brandToCarouselItem(b, favoriteItemIds)).filter(Boolean);
  }, [brandsData, favoriteItemIds]);

  const favoriteBrands = useMemo(() => allBrands.filter((b) => b.isFavorite), [allBrands]);

  const filteredBrands = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return allBrands;
    return allBrands.filter((brand) =>
      String(brand?.name || '')
        .toLowerCase()
        .includes(q)
    );
  }, [allBrands, searchQuery]);

  return (
    <div className={styles.pageMain}>
      <Header title="Бренды" showClose />

      <main className={styles.content}>
        {favoriteBrands.length > 0 ? <FavoriteBrandsSection brands={favoriteBrands} /> : null}

        <section className={styles.allCard}>
          <h2 className={styles.sectionTitle}>Все</h2>

          <div className={styles.searchWrap}>
            <BrandsSearch value={searchQuery} onChange={setSearchQuery} placeholder="Найти бренд" />
          </div>

          <AllBrandsList brands={filteredBrands} onToggleFavorite={toggleFavorite} />
        </section>
      </main>

      <Footer />
    </div>
  );
}
