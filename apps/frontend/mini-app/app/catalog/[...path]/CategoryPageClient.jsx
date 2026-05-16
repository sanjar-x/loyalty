'use client';

import { useMemo } from 'react';
import Link from 'next/link';
import Image from 'next/image';

import Footer from '@/components/layout/Footer';
import Header from '@/components/layout/Header';
import SearchBar from '@/components/blocks/search/SearchBar';
import SubcategoryList from '@/components/blocks/catalog/SubcategoryList';
import CategoryBreadcrumbs from '@/components/blocks/catalog/CategoryBreadcrumbs';
import { useGetCategoryTreeQuery } from '@/lib/store/api';
import { findByFullSlug, joinPathSegments } from '@/lib/adapters/mapCategoryTree';

import styles from './page.module.css';

/**
 * Client-rendered category sub-page — faqat JSON request/response, SSR yo'q.
 * Kategoriya daraxti RTK Query (`/api/v1/catalog/categories/tree`) dan
 * olinadi, cache 30 daqiqa (api.js: keepUnusedDataFor 1800).
 */
export default function CategoryPageClient({ segments }) {
  const fullSlug = useMemo(
    () => joinPathSegments(Array.isArray(segments) ? segments : []),
    [segments]
  );

  const { data, isLoading, isError } = useGetCategoryTreeQuery();
  const tree = useMemo(() => (Array.isArray(data) ? data : []), [data]);
  const hit = useMemo(
    () => (tree.length ? findByFullSlug(tree, fullSlug) : null),
    [tree, fullSlug]
  );

  if (isLoading) {
    return (
      <div className={styles.root}>
        <Header title="Каталог" />
        <main className={styles.main}>
          <div className={styles.leafHint}>
            <p className={styles.leafText}>Загрузка…</p>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  if (isError || !hit) {
    return (
      <div className={styles.root}>
        <Header title="Каталог" />
        <main className={styles.main}>
          <div className={styles.leafHint}>
            <p className={styles.leafText}>Категория не найдена.</p>
            <Link href="/catalog" className={styles.leafCta} prefetch={false}>
              В каталог
            </Link>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  const { node, trail } = hit;
  const children = Array.isArray(node.children) ? node.children : [];
  const plpHref = `/?category_id=${encodeURIComponent(node.id)}`;

  return (
    <div className={styles.root}>
      <Header title="Каталог" />

      <div className={styles.searchWrap}>
        <SearchBar readOnly navigateOnFocusTo="/?search=1" />
      </div>

      <main className={styles.main}>
        <div className={styles.sectionHeader}>
          <div className={styles.headerRow}>
            <h1 className={styles.title}>{node.name}</h1>
            <Link
              href={plpHref}
              className={styles.allBtn}
              prefetch={false}
              aria-label={`Все товары категории ${node.name}`}
            >
              <span className={styles.allText}>все</span>
              <div className={styles.allIconWrap}>
                <Image src="/icons/global/Wrap.svg" alt="" width={20} height={18} />
              </div>
            </Link>
          </div>
        </div>

        <div className={styles.listOuter}>
          {children.length > 0 ? (
            <SubcategoryList nodes={children} />
          ) : (
            <div className={styles.leafHint}>
              <p className={styles.leafText}>Нет подкатегорий — откройте список товаров.</p>
              <Link href={plpHref} className={styles.leafCta} prefetch={false}>
                Смотреть товары
              </Link>
            </div>
          )}
        </div>
      </main>

      <Footer />
    </div>
  );
}
