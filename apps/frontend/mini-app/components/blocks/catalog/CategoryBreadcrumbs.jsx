import Link from 'next/link';
import styles from './CategoryBreadcrumbs.module.css';

/**
 * Renders the ancestor chain for the active category page.
 * `trail` is an array of mapped category nodes from root → current.
 * The current (last) node is rendered as plain text.
 */
export default function CategoryBreadcrumbs({ trail }) {
  const items = Array.isArray(trail) ? trail : [];
  if (!items.length) return null;

  return (
    <nav className={styles.root} aria-label="Хлебные крошки">
      <Link href="/catalog" className={styles.crumb}>
        Каталог
      </Link>
      {items.map((node, idx) => {
        const isLast = idx === items.length - 1;
        const name = (node?.name || node?.slug || '').toString();
        return (
          <span key={node?.id ?? idx} className={styles.crumbWrap}>
            <span className={styles.separator} aria-hidden="true">
              /
            </span>
            {isLast ? (
              <span className={styles.current} aria-current="page">
                {name}
              </span>
            ) : (
              <Link href={`/catalog/${node.fullSlug}`} className={styles.crumb}>
                {name}
              </Link>
            )}
          </span>
        );
      })}
    </nav>
  );
}
