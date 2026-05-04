"use client";

import { useMemo, useState } from "react";

import Footer from "@/components/layout/Footer";
import Header from "@/components/layout/Header";
import SearchBar from "@/components/blocks/search/SearchBar";
import CatalogTabs from "@/components/blocks/catalog/CatalogTabs";
import BrandsList from "@/components/blocks/catalog/BrandsList";
import CategoryRootCard from "@/components/blocks/catalog/CategoryRootCard";
import { useGetCategoryTreeQuery } from "@/lib/store/api";

import styles from "./page.module.css";

/**
 * Client-side catalog shell — kategoriya daraxtini RTK Query orqali
 * (JSON request/response) oladi, ya'ni SSR fetch yo'q. Gatekeeping
 * `AuthGate` tarafidan, shuning uchun bu komponent mount bo'lishi bilan
 * cookie'da token bor deb ishonamiz.
 */
export default function CatalogPageClient() {
  const [activeTab, setActiveTab] = useState("catalog");
  const { data, isLoading, isError } = useGetCategoryTreeQuery();

  const tree = useMemo(() => (Array.isArray(data) ? data : []), [data]);

  const catalogSlot = (
    <div className={styles.categories}>
      {isLoading ? (
        <div className={styles.empty}>Загрузка…</div>
      ) : isError ? (
        <div className={styles.empty}>Категории временно недоступны</div>
      ) : tree.length === 0 ? (
        <div className={styles.empty}>Категории временно недоступны</div>
      ) : (
        tree.map((node) => <CategoryRootCard key={node.id} node={node} />)
      )}
    </div>
  );

  return (
    <div className={styles.root}>
      <Header title="Поиск" />
      <div className={styles.stickyBar}>
        <div className={styles.tabsWrap}>
          <CatalogTabs activeTab={activeTab} onTabChange={setActiveTab} />
        </div>
        <div className={styles.searchWrap}>
          <SearchBar
            placeholder={activeTab === "brands" ? "Найти бренд" : "Поиск"}
            readOnly
            navigateOnFocusTo="/?search=1"
          />
        </div>
      </div>
      <main className={styles.main}>
        {activeTab === "catalog" ? catalogSlot : <BrandsList />}
      </main>
      <Footer />
    </div>
  );
}
