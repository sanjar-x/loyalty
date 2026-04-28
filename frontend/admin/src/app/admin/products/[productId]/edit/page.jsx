'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { getProduct, listProductMedia } from '@/services/products';
import { i18n } from '@/lib/utils';
import ProductDetailsForm from '../../add/details/ProductDetailsForm';
import styles from '../../add/details/page.module.css';

function BackArrowIcon() {
  return (
    <svg
      width="30"
      height="30"
      viewBox="0 0 30 30"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M11.9621 6.4751C12.1996 6.4751 12.4371 6.5626 12.6246 6.7501C12.9871 7.1126 12.9871 7.7126 12.6246 8.0751L5.69961 15.0001L12.6246 21.9251C12.9871 22.2876 12.9871 22.8876 12.6246 23.2501C12.2621 23.6126 11.6621 23.6126 11.2996 23.2501L3.71211 15.6626C3.34961 15.3001 3.34961 14.7001 3.71211 14.3376L11.2996 6.7501C11.4871 6.5626 11.7246 6.4751 11.9621 6.4751Z"
        fill="black"
      />
      <path
        d="M4.5875 14.0625L25.625 14.0625C26.1375 14.0625 26.5625 14.4875 26.5625 15C26.5625 15.5125 26.1375 15.9375 25.625 15.9375L4.5875 15.9375C4.075 15.9375 3.65 15.5125 3.65 15C3.65 14.4875 4.075 14.0625 4.5875 14.0625Z"
        fill="black"
      />
    </svg>
  );
}

export default function EditProductPage() {
  const { productId } = useParams();
  const router = useRouter();
  const [product, setProduct] = useState(null);
  const [media, setMedia] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [prod, mediaRes] = await Promise.all([
        getProduct(productId),
        listProductMedia(productId),
      ]);
      setProduct(prod);
      setMedia(mediaRes?.items ?? []);
    } catch (err) {
      setError(err.message ?? 'Не удалось загрузить данные продукта');
    } finally {
      setLoading(false);
    }
  }, [productId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return (
      <section className={styles.page}>
        <div className={styles.header}>
          <Link
            href={`/admin/products/${productId}`}
            className={styles.backButton}
            aria-label="Назад к товару"
          >
            <BackArrowIcon />
          </Link>
          <h1 className={styles.title}>Загрузка...</h1>
        </div>
      </section>
    );
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
            <BackArrowIcon />
          </Link>
          <h1 className={styles.title}>Ошибка</h1>
        </div>
        <div style={{ padding: 24, textAlign: 'center' }}>
          <p className="mb-3 text-sm text-red-600">
            {error || 'Продукт не найден'}
          </p>
          <button
            type="button"
            onClick={loadData}
            className="text-sm font-medium text-[#22252b] underline hover:no-underline"
          >
            Попробовать снова
          </button>
        </div>
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
          <BackArrowIcon />
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
        productId={productId}
      />
    </section>
  );
}
