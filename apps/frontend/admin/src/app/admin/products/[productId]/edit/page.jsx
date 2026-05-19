'use client';

import { useParams } from 'next/navigation';
import Link from 'next/link';
import {
  ProductEditSkeleton,
  useProduct,
  useProductMedia,
} from '@/entities/product';
import { ProductDetailsForm } from '@/features/product-form';
import { ApiErrorState } from '@/shared/ui/ApiErrorState';
import { i18n } from '@/shared/lib/utils';
import ArrowLeftIcon from '@/assets/icons/arrow-left.svg';
import styles from './page.module.css';

export default function EditProductPage() {
  const { productId } = useParams();

  const {
    data: product,
    isPending: productLoading,
    error: productError,
    refetch: refetchProduct,
  } = useProduct(productId);

  const {
    data: mediaResponse,
    isPending: mediaLoading,
    error: mediaError,
    refetch: refetchMedia,
  } = useProductMedia(productId);

  const loading = productLoading || mediaLoading;
  const error = productError || mediaError;
  const media = mediaResponse?.items ?? [];

  if (loading && !product) {
    return <ProductEditSkeleton />;
  }

  if (error || !product) {
    return (
      <section className={styles.page}>
        <div className={styles.header}>
          <Link
            href={`/admin/products/${productId}`}
            className={styles.backButton}
            aria-label="Назад к товару"
          >
            <ArrowLeftIcon aria-hidden="true" />
          </Link>
          <h1 className={styles.title}>Ошибка</h1>
        </div>
        <ApiErrorState
          error={error ?? { status: 404 }}
          onRetry={() => {
            refetchProduct();
            refetchMedia();
          }}
          homeHref="/admin/products"
          homeLabel="К списку товаров"
        />
      </section>
    );
  }

  const categoryId = product.primaryCategoryId;
  const leafLabel = i18n(product.titleI18N) || 'Продукт';

  return (
    <section className={styles.page}>
      <div className={styles.header}>
        <Link
          href={`/admin/products/${productId}`}
          className={styles.backButton}
          aria-label="Назад к товару"
        >
          <ArrowLeftIcon aria-hidden="true" />
        </Link>
        <h1 className={styles.title}>Редактирование товара</h1>
      </div>

      <ProductDetailsForm
        key={productId}
        leafLabel={leafLabel}
        categoryId={categoryId}
        breadcrumbs={null}
        mode="edit"
        initialProduct={product}
        initialMedia={media}
      />
    </section>
  );
}
