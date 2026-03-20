"use client";
const EMPTY_SET: Set<number | string> = new Set();
import React, { useMemo, useState } from "react";
import Footer from "@/components/layout/Footer";
import FavoriteBrandsSection from "@/components/blocks/favorites/brands/FavoriteBrandsSection";
import BrandsSearch from "@/components/blocks/favorites/brands/BrandsSearch";
import AllBrandsList from "@/components/blocks/favorites/brands/AllBrandsList";
import styles from "./page.module.css";

import { getBrandLogoCandidates } from "@/lib/format/brand-image";

interface ApiBrand {
  id?: number | string;
  name?: string;
  logo?: string;
}

interface BrandUi {
  id: number | string | undefined;
  name: string;
  image: string;
  imageFallbacks: string[];
  isFavorite: boolean;
}

export default function BrandsPage(): React.JSX.Element {
  const [searchQuery, setSearchQuery] = useState<string>("");

  const brandsData: ApiBrand[] = [];
  const favoriteItemIds = EMPTY_SET;
  const toggleFavorite = (_id: number | string): void => {};

  const allBrands = useMemo((): BrandUi[] => {
    const rows = Array.isArray(brandsData) ? brandsData : [];
    return rows
      .map((b) => {
        const id = b?.id;
        const name = b?.name ?? "";
        const candidates = getBrandLogoCandidates(b);
        const image = candidates[0] || "";
        const imageFallbacks = candidates.slice(1);
        const isFavorite = favoriteItemIds.has(id as number | string);
        return {
          id,
          name,
          image,
          imageFallbacks,
          isFavorite,
        };
      })
      .filter((b) => b.id != null);
  }, [brandsData, favoriteItemIds]);

  const favoriteBrands = useMemo(
    () => allBrands.filter((b) => b.isFavorite),
    [allBrands],
  );

  const handleToggleFavorite = (id: number | string): void => toggleFavorite(id);

  const filteredBrands = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return allBrands;
    return allBrands.filter((brand) =>
      String(brand?.name || "")
        .toLowerCase()
        .includes(q),
    );
  }, [allBrands, searchQuery]);

  return (
    <div className={styles.pageMain}>
      <h3 className={styles.pageTitle}>Бренды</h3>
      <div className={styles.page}>
        <main className={styles.content}>
          {favoriteBrands.length > 0 ? (
            <FavoriteBrandsSection brands={favoriteBrands} />
          ) : null}

          <section className={styles.allCard}>
            <h2 className={styles.sectionTitle}>Все</h2>

            <div className={styles.searchWrap}>
              <BrandsSearch
                value={searchQuery}
                onChange={setSearchQuery}
                placeholder="Найти бренд"
              />
            </div>

            <AllBrandsList
              brands={filteredBrands}
              onToggleFavorite={handleToggleFavorite}
            />
          </section>
        </main>
      </div>
      <Footer />
    </div>
  );
}
