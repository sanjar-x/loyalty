import Link from 'next/link';
import {
  categoryLabel,
  fetchCategoryTreeServer,
} from '@/entities/category/server';
import { ProductDetailsForm } from '@/features/product-form';
import styles from './page.module.css';

// Inline SVG: this file is a Server Component, and the @svgr/webpack loader
// only kicks in for client modules. Keep these chevrons inline rather than
// switching to a client wrapper just for two icons.
function ChevronGlyph() {
  return (
    <svg
      width="9"
      height="16"
      viewBox="0 0 9 16"
      fill="none"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M.277 15.724c-.37-.367-.37-.963 0-1.331L6.713 8 .277 1.607c-.37-.368-.37-.964 0-1.331.37-.368.97-.368 1.34 0l7.106 7.058c.37.368.37.964 0 1.331l-7.106 7.058c-.37.368-.97.368-1.34 0Z"
        fill="currentColor"
      />
    </svg>
  );
}

function ArrowLeftGlyph() {
  return (
    <svg
      width="30"
      height="30"
      viewBox="0 0 30 30"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M11.96 6.475c.238 0 .475.088.663.275.362.363.362.963 0 1.325L5.7 15l6.925 6.925c.362.363.362.963 0 1.325-.363.363-.963.363-1.325 0L3.712 15.663a.937.937 0 0 1 0-1.325L11.3 6.75a.927.927 0 0 1 .662-.275Z"
        fill="currentColor"
      />
      <path
        d="M4.587 14.063H25.625c.513 0 .938.425.938.937 0 .513-.425.938-.938.938H4.588a.937.937 0 0 1-.938-.938c0-.512.425-.937.937-.937Z"
        fill="currentColor"
      />
    </svg>
  );
}

function Crumb({ label }) {
  return (
    <div className={styles.crumb}>
      <span className={styles.crumbLabel}>{label}</span>
      <span className={styles.crumbChevron}>
        <ChevronGlyph />
      </span>
    </div>
  );
}

function findByFullSlug(tree, fullSlug, path = []) {
  for (const node of tree) {
    const nodeSlug = node.fullSlug || node.slug || '';
    if (nodeSlug === fullSlug) return [...path, node];
    if (node.children?.length) {
      const found = findByFullSlug(node.children, fullSlug, [...path, node]);
      if (found) return found;
    }
  }
  return null;
}

export default async function AddProductDetailsPage({ params }) {
  const resolvedParams = await params;
  const slugSegments = resolvedParams?.slug ?? [];
  const fullSlug = slugSegments.join('/');

  const tree = await fetchCategoryTreeServer();
  const ancestors = findByFullSlug(tree, fullSlug) ?? [];
  const leaf = ancestors.at(-1) ?? null;
  const leafLabel = categoryLabel(leaf);
  const leafCategoryId = leaf?.id ?? null;

  return (
    <section className={styles.page}>
      <div className={styles.header}>
        <Link
          href="/admin/products/add"
          className={styles.backButton}
          aria-label="Назад к выбору категории"
        >
          <ArrowLeftGlyph />
        </Link>
        <h1 className={styles.title}>Добавление товара</h1>
      </div>

      <ProductDetailsForm
        leafLabel={leafLabel}
        categoryId={leafCategoryId}
        breadcrumbs={
          <div className={styles.breadcrumbs}>
            {ancestors.map((node) => (
              <Crumb key={node.id} label={categoryLabel(node)} />
            ))}
            {ancestors.length === 0 && <Crumb label={leafLabel} />}
          </div>
        }
      />
    </section>
  );
}
