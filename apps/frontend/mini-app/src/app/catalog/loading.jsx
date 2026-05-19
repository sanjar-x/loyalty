'use client';

import { SearchBar } from '@/features/search';
import Footer from '@/widgets/Footer';
import Header from '@/widgets/Header';
import { CatalogTabs } from '@/entities/category';

import styles from './page.module.css';

export default function Loading() {
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
