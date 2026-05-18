'use client';

import { useMemo, useState } from 'react';

import Footer from '@/widgets/Footer';
import Header from '@/widgets/Header';
import SearchBar from '@/features/search';
import CatalogTabs from '@/entities/category';
import BrandsList from '@/entities/brand';
import CategoryRootCard from '@/entities/category/ui/CategoryRootCard';
import { useGetCategoryTreeQuery } from '@/entities/category';

import styles from './page.module.css';

/**
 * Client-side catalog shell — fetches the category tree via RTK Query
 * (JSON request/response), so no SSR fetch. Gatekeeping is handled by
 * `AuthGate`, so once this component mounts we trust that a token is
 * present in the cookie.
 */
export default function CatalogPage() {
  const [activeTab, setActiveTab] = useState('catalog');
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
            placeholder={activeTab === 'brands' ? 'Найти бренд' : 'Поиск'}
            readOnly
            navigateOnFocusTo="/?search=1"
          />
        </div>
      </div>
      <main className={styles.main}>{activeTab === 'catalog' ? catalogSlot : <BrandsList />}</main>
      <Footer />
    </div>
  );
}
