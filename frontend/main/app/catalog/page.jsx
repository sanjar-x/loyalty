"use client";
import Link from "next/link";
import Image from "next/image";
import SearchBar from "@/components/blocks/search/SearchBar";
import { useState } from "react";

import Footer from "@/components/layout/Footer";
import Header from "@/components/layout/Header";
import CatalogTabs from "@/components/blocks/catalog/CatalogTabs";
import BrandsList from "@/components/blocks/catalog/BrandsList";

import styles from "./page.module.css";

export default function CatalogPage() {
  const categoriesData = [];
  const isCategoriesLoading = false;

  const normalize = (v) =>
    String(v ?? "")
      .trim()
      .toLowerCase()
      .replace(/ё/g, "е")
      .replace(/[\s_-]+/g, "");

  const categoryUiByName = {
    [normalize("Одежда")]: {
      imageSrc: "/icons/catalog/catalog-icon-1.svg",
      altText: "Одежда",
    },
    [normalize("Обувь")]: {
      imageSrc: "/icons/catalog/catalog-icon-2.svg",
      altText: "Обувь",
    },
    [normalize("Аксессуры")]: {
      imageSrc: "/icons/catalog/catalog-icon-3.svg",
      altText: "Аксессуары",
    },
    [normalize("Аксессуары")]: {
      imageSrc: "/icons/catalog/catalog-icon-3.svg",
      altText: "Аксессуары",
    },
  };

  const categories = (Array.isArray(categoriesData) ? categoriesData : []).map(
    (c) => {
      const name = c?.name ?? "";
      const ui = categoryUiByName[normalize(name)] || {
        imageSrc: "/icons/catalog/catalog-icon-1.svg",
        altText: name || "Категория",
      };

      return {
        id: c?.id,
        name,
        title: String(name).toLowerCase(),
        ...ui,
      };
    },
  );

  const [activeTab, setActiveTab] = useState("catalog");

  return (
    <div className={styles.root}>
      <Header title="Поиск" />

      <div className={styles.tabsWrap}>
        <CatalogTabs activeTab={activeTab} onTabChange={setActiveTab} />
      </div>
      <div className={styles.searchWrap}>
        <SearchBar />
      </div>
      <main className={styles.main}>
        {activeTab === "catalog" ? (
          <div className={styles.categories}>
            {isCategoriesLoading
              ? Array.from({ length: 3 }).map((_, idx) => (
                  <div key={idx} className={styles.card} aria-hidden="true">
                    <div className={styles.skeletonTitle} />
                    <div className={styles.skeletonImage} />
                  </div>
                ))
              : categories.map((category) => (
                  <Link
                    key={category.id ?? category.name}
                    href={`/catalog/${encodeURIComponent(String(category.name ?? ""))}`}
                  >
                    <div className={styles.card}>
                      <h3 className={styles.cardTitle}>{category.title}</h3>
                      <div className={styles.cardImageWrap}>
                        <Image
                          src={category.imageSrc}
                          alt={category.altText}
                          width={239}
                          height={239}
                          className={styles.cardImage}
                        />
                      </div>
                    </div>
                  </Link>
                ))}
          </div>
        ) : (
          <BrandsList />
        )}
      </main>
      <Footer />
    </div>
  );
}
