import Link from 'next/link';
import Image from 'next/image';
import styles from './SubcategoryList.module.css';

/**
 * Renders a vertical list of child category rows with dividers.
 * Each row links to either the next drill-down page (if node has children)
 * or directly to the PLP filtered by that category id.
 */
export default function SubcategoryList({ nodes }) {
  const list = Array.isArray(nodes) ? nodes : [];
  if (!list.length) return null;

  return (
    <div className={styles.list}>
      <div className={`${styles.divider} ${styles.dividerTop}`} />
      <div className={styles.items}>
        {list.map((node, idx) => {
          const hasChildren = Array.isArray(node?.children) && node.children.length > 0;
          const href = hasChildren
            ? `/catalog/${node.fullSlug}`
            : `/?category_id=${encodeURIComponent(node.id)}`;
          const title = (node.name || node.slug || '').toString();

          return (
            <div key={node.id ?? idx}>
              <Link href={href} className={styles.itemRow} prefetch={false}>
                <span className={styles.subcategory}>{title}</span>
                <div className={styles.chevron} aria-hidden="true">
                  <Image src="/icons/global/arrowBlack.svg" alt="" width={7} height={11} />
                </div>
              </Link>
              {idx < list.length - 1 && <div className={styles.divider} />}
            </div>
          );
        })}
      </div>
    </div>
  );
}
