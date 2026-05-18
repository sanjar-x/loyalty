'use client';

import { useMemo } from 'react';
import Link from 'next/link';
import Image from 'next/image';

import Footer from '@/widgets/Footer';
import Header from '@/widgets/Header';
import SearchBar from '@/features/search';
import SubcategoryList from '@/entities/category/ui/SubcategoryList';
import CategoryBreadcrumbs from '@/entities/category/ui/CategoryBreadcrumbs';
import { useGetCategoryTreeQuery } from '@/entities/category';
import { findByFullSlug, joinPathSegments } from '@/entities/category/lib/mapCategoryTree';

import styles from './page.module.css';

/**
 * Client-rendered category sub-page — JSON request/response only, no SSR.
 * The category tree is fetched via RTK Query (`/api/v1/catalog/categories/tree`),
 * cached for 30 minutes (api.js: keepUnusedDataFor 1800).
 */
export default function CategoryPage({ segments }) {
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
