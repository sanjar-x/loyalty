'use client';
import Header from '@/widgets/Header';
import Footer from '@/widgets/Footer';
import ProductSection from '@/entities/product';
import { useMemo, useState } from 'react';
import styles from './page.module.css';

export default function ViewedPage() {
  // Backend has no view-history endpoint yet (Spec §11). When the module is
  // ready, it's enough to add `useViewedProductsQuery` to RTKQ and wire it here.
  const [viewedProducts, setViewedProducts] = useState([]);

  const toggleViewedProduct = (id) => {
    setViewedProducts((prev) =>
      prev.map((product) =>
        product.id === id ? { ...product, isFavorite: !product.isFavorite } : product
      )
    );
  };

  const date = useMemo(() => {
    try {
      return new Intl.DateTimeFormat('ru-RU', {
        day: '2-digit',
        month: 'long',
      }).format(new Date());
    } catch {
      return '';
    }
  }, []);

  return (
    <div className={styles.pageViewed}>
      <Header title="Просмотренное"></Header>
      <main className={styles.c1}>
        <div className={styles.c2}>
          <div className={styles.c3}>
            <span suppressHydrationWarning className={styles.c4}>
              {date}
            </span>
          </div>
          {viewedProducts.length > 0 ? (
            <ProductSection
              isViewed={true}
              onToggleFavorite={toggleViewedProduct}
              products={viewedProducts}
            />
          ) : (
            <section className={styles.emptyState} role="status" aria-live="polite">
              <div className={styles.emptyTitle}>Здесь пока пусто</div>
              <div className={styles.emptyText}>Просмотренные товары будут появляться здесь</div>
            </section>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}
