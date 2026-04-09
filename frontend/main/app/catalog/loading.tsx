"use client";

import SearchBar from "@/components/blocks/search/SearchBar";
import Footer from "@/components/layout/Footer";
import Header from "@/components/layout/Header";
import CatalogTabs from "@/components/blocks/catalog/CatalogTabs";

import styles from "./page.module.css";

export default function Loading(): React.JSX.Element {
  return (
    <div className={styles.root}>
      <Header title="Поиск" />

      <div className={styles.tabsWrap}>
        <CatalogTabs activeTab="catalog" onTabChange={() => {}} />
      </div>

      <div className={styles.searchWrap}>
        <SearchBar />
      </div>

      <main className={styles.main}>
        <div className={styles.categories} aria-busy="true">
          {Array.from({ length: 3 }).map((_, idx) => (
            <div key={idx} className={styles.card} aria-hidden="true">
              <div className={styles.skeletonTitle} />
              <div className={styles.skeletonImage} />
            </div>
          ))}
        </div>
      </main>

      <Footer />
    </div>
  );
}
