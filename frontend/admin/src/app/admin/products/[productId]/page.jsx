'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import {
  changeProductStatus,
  CompletenessPanel,
  PRODUCT_STATUS_LABELS,
  productKeys,
  useProduct,
  useProductCompleteness,
} from '@/entities/product';
import { StatusTransitionBar } from '@/features/product-status-change';
import { i18n } from '@/shared/lib/utils';
import styles from './page.module.css';

export default function ProductDetailPage() {
  const { productId } = useParams();
  const queryClient = useQueryClient();
  const [transitionError, setTransitionError] = useState(null);

  const {
    data: product,
    isPending: productLoading,
    error: productError,
    refetch: refetchProduct,
  } = useProduct(productId);

  const { data: completeness } = useProductCompleteness(productId);

  const transitionMutation = useMutation({
    mutationFn: (targetStatus) => changeProductStatus(productId, targetStatus),
    onSuccess: () => {
      // Prefix-invalidate the detail key (propagates to nested completeness
      // and media), plus the list and FSM tab counts. The refetch lands
      // before the user can react, so we don't bother with an optimistic
      // setQueryData merge — it would just be overwritten anyway.
      queryClient.invalidateQueries({
        queryKey: productKeys.detail(productId),
      });
      queryClient.invalidateQueries({ queryKey: productKeys.lists() });
      queryClient.invalidateQueries({ queryKey: productKeys.counts() });
    },
    onError: (err) =>
      setTransitionError(err.message ?? 'Не удалось изменить статус'),
  });

  if (productLoading && !product) {
    return (
      <div className={styles.loadingState}>
        <p className="text-app-muted text-sm">Загрузка...</p>
      </div>
    );
  }

  if (productError && !product) {
    return (
      <div className={styles.errorState}>
        <p className="mb-3 text-sm text-red-600">
          {productError.message ?? 'Не удалось загрузить продукт'}
        </p>
        <button
          type="button"
          onClick={() => refetchProduct()}
          className="text-app-text text-sm font-medium underline hover:no-underline"
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
        <p className="text-app-muted text-sm">{product.slug}</p>
      </div>

      <div className={styles.transitionSection}>
        <StatusTransitionBar
          status={product.status}
          loading={transitionMutation.isPending}
          onTransition={(targetStatus) => {
            setTransitionError(null);
            transitionMutation.mutate(targetStatus);
          }}
        />
      </div>

      {transitionError && (
        <div className={styles.errorBanner}>
          <span>{transitionError}</span>
          <button
            type="button"
            onClick={() => setTransitionError(null)}
            className="ml-2 font-medium underline"
          >
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
              <span className={styles.infoValue}>
                {i18n(product.descriptionI18N)}
              </span>
            </div>
          )}
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Бренд</span>
            <span className={styles.infoValue}>{product.brandId}</span>
          </div>
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Категория</span>
            <span className={styles.infoValue}>
              {product.primaryCategoryId}
            </span>
          </div>
          {product.countryOfOrigin && (
            <div className={styles.infoRow}>
              <span className={styles.infoLabel}>Страна</span>
              <span className={styles.infoValue}>
                {product.countryOfOrigin}
              </span>
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
