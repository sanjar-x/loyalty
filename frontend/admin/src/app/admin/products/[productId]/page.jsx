'use client';

import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { getProduct, getProductCompleteness, changeProductStatus } from '@/services/products';
import { PRODUCT_STATUS_LABELS } from '@/lib/constants';
import { i18n } from '@/lib/utils';
import { CompletenessPanel } from '@/components/admin/products/CompletenessPanel';
import { StatusTransitionBar } from '@/components/admin/products/StatusTransitionBar';
import styles from './page.module.css';

export default function ProductDetailPage() {
  const { productId } = useParams();
  const [product, setProduct] = useState(null);
  const [completeness, setCompleteness] = useState(null);
  const [loading, setLoading] = useState(true);
  const [transitioning, setTransitioning] = useState(false);
  const [error, setError] = useState(null);

  const loadProduct = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [prod, comp] = await Promise.all([
        getProduct(productId),
        getProductCompleteness(productId),
      ]);
      setProduct(prod);
      setCompleteness(comp);
    } catch (err) {
      setError(err.message ?? 'Не удалось загрузить продукт');
    } finally {
      setLoading(false);
    }
  }, [productId]);

  useEffect(() => {
    loadProduct();
  }, [loadProduct]);

  const handleTransition = useCallback(async (targetStatus) => {
    if (!product) return;
    setTransitioning(true);
    setError(null);
    try {
      const updated = await changeProductStatus(product.id, targetStatus);
      setProduct(updated);
      const comp = await getProductCompleteness(product.id);
      setCompleteness(comp);
    } catch (err) {
      setError(err.message ?? 'Не удалось изменить статус');
    } finally {
      setTransitioning(false);
    }
  }, [product]);

  if (loading && !product) {
    return (
      <div className={styles.loadingState}>
        <p className="text-sm text-[#878b93]">Загрузка...</p>
      </div>
    );
  }

  if (error && !product) {
    return (
      <div className={styles.errorState}>
        <p className="mb-3 text-sm text-red-600">{error}</p>
        <button
          type="button"
          onClick={loadProduct}
          className="text-sm font-medium text-[#22252b] underline hover:no-underline"
        >
          Попробовать снова
        </button>
      </div>
    );
  }

  if (!product) return null;

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <Link href="/admin/products" className={styles.backLink}>
          ← Товары
        </Link>
        <div className={styles.titleRow}>
          <h1 className={styles.title}>{i18n(product.titleI18N)}</h1>
          <span className={styles.statusBadge}>
            {PRODUCT_STATUS_LABELS[product.status] ?? product.status}
          </span>
          <span className={styles.versionTag}>v{product.version}</span>
          <Link
            href={`/admin/products/${productId}/edit`}
            className={styles.editButton}
          >
            Редактировать
          </Link>
        </div>
        <p className="text-sm text-[#878b93]">{product.slug}</p>
      </div>

      <div className={styles.transitionSection}>
        <StatusTransitionBar
          status={product.status}
          loading={transitioning}
          onTransition={handleTransition}
        />
      </div>

      {error && (
        <div className={styles.errorBanner}>
          <span>{error}</span>
          <button type="button" onClick={() => setError(null)} className="ml-2 font-medium underline">
            Скрыть
          </button>
        </div>
      )}

      <div className={styles.content}>
        <div className={styles.mainCard}>
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Название</span>
            <span className={styles.infoValue}>{i18n(product.titleI18N)}</span>
          </div>
          {product.descriptionI18N && (
            <div className={styles.infoRow}>
              <span className={styles.infoLabel}>Описание</span>
              <span className={styles.infoValue}>{i18n(product.descriptionI18N)}</span>
            </div>
          )}
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Бренд</span>
            <span className={styles.infoValue}>{product.brandId}</span>
          </div>
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Категория</span>
            <span className={styles.infoValue}>{product.primaryCategoryId}</span>
          </div>
          {product.countryOfOrigin && (
            <div className={styles.infoRow}>
              <span className={styles.infoLabel}>Страна</span>
              <span className={styles.infoValue}>{product.countryOfOrigin}</span>
            </div>
          )}
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Статус</span>
            <span className={styles.infoValue}>
              {PRODUCT_STATUS_LABELS[product.status] ?? product.status}
            </span>
          </div>
        </div>

        <div className={styles.sidebar}>
          <CompletenessPanel completeness={completeness} />
        </div>
      </div>
    </div>
  );
}
