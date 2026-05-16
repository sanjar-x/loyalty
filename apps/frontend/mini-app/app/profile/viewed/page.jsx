'use client';
import Header from '@/components/layout/Header';
import Footer from '@/components/layout/Footer';
import ProductSection from '@/components/blocks/product/ProductSection';
import { useMemo, useState } from 'react';
import styles from './page.module.css';

export default function ViewedPage() {
  // Backend'da view-history endpoint'i yo'q (Spec §11). Modul tayyor bo'lganda
  // RTKQ'ga `useViewedProductsQuery`'ni qo'shib shu yerga ulash kifoya.
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
