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

  // Senior-UX note: the breadcrumb used to be a thick white card with two
  // 46px pill rows + chevron-right glyphs — read as «clickable dropdowns»
  // even though the path is read-only context. Inlined into the page
  // header as a single muted line under the H1 so it costs ~20px of
  // vertical real estate instead of ~140px.
  const crumbLabels =
    ancestors.length > 0
      ? ancestors.map((node) => categoryLabel(node))
      : [leafLabel];

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
        <div className={styles.headerText}>
          <h1 className={styles.title}>Добавление товара</h1>
          <nav className={styles.crumbs} aria-label="Категория товара">
            {crumbLabels.map((label, idx) => (
              <span key={label + idx} className={styles.crumbsItem}>
                {idx > 0 && (
                  <span className={styles.crumbsSeparator} aria-hidden="true">
                    /
                  </span>
                )}
                <span>{label}</span>
              </span>
            ))}
          </nav>
        </div>
      </div>

      <ProductDetailsForm
        leafLabel={leafLabel}
        categoryId={leafCategoryId}
        breadcrumbs={null}
      />
    </section>
  );
}
