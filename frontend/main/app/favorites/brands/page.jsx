"use client";
import React, { useMemo, useState } from "react";
import Footer from "@/components/layout/Footer";
import FavoriteBrandsSection from "@/components/blocks/favorites/brands/FavoriteBrandsSection";
import BrandsSearch from "@/components/blocks/favorites/brands/BrandsSearch";
import AllBrandsList from "@/components/blocks/favorites/brands/AllBrandsList";
import styles from "./page.module.css";

import { useGetBrandsQuery } from "@/lib/store/api";
import { useItemFavorites } from "@/lib/hooks/useItemFavorites";
import {
  buildBackendAssetUrl,
  buildBrandLogoUrl,
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

export default function BrandsPage() {
  const [searchQuery, setSearchQuery] = useState("");

  const { data: brandsData } = useGetBrandsQuery();
  const { favoriteItemIds, toggleFavorite } = useItemFavorites("brand");

  const allBrands = useMemo(() => {
    const rows = Array.isArray(brandsData) ? brandsData : [];
    return rows
      .map((b) => {
        const id = b?.id;
        const name = b?.name ?? "";
        const candidates = getBrandLogoCandidates(b);
        const image = candidates[0] || "";
        const imageFallbacks = candidates.slice(1);
        const isFavorite = favoriteItemIds.has(id);
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

  const handleToggleFavorite = (id) => toggleFavorite(id);

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
