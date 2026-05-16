'use client';
import React, { useMemo, useState } from 'react';

import Header from '@/components/layout/Header';
import Footer from '@/components/layout/Footer';
import FavoriteBrandsSection from '@/components/blocks/favorites/brands/FavoriteBrandsSection';
import BrandsSearch from '@/components/blocks/favorites/brands/BrandsSearch';
import AllBrandsList from '@/components/blocks/favorites/brands/AllBrandsList';

import { useGetBrandsQuery } from '@/lib/store/api';
import { useItemFavorites } from '@/lib/hooks/useItemFavorites';
import { brandToCarouselItem } from '@/lib/adapters/favoriteAssets';

import styles from './page.module.css';

/**
 * `/favorites/brands` — sevimli brendlar + barcha brendlar bilan to'liq sahifa.
 *
 * Tarkibi:
 *   1. Header ("Бренды" sarlavha + close button)
 *   2. "Избранные" — sevimli brendlar (vertical list, chevron right)
 *   3. "Все" — qidiruv paneli + alfavitli barcha brendlar (har bir
 *      brendda toggle yurakcha)
 *
 * Empty holatlar:
 *   - Sevimli brendlar yo'q bo'lsa "Избранные" seksiyasi yashirinadi
 *   - "Все" qidiruvda hech narsa topilmasa, bo'sh ro'yxat
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
