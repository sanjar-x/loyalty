import Link from 'next/link';
import Image from 'next/image';
import { getCategoryIconBySlug } from '@/entities/category/lib/categoryIcons';
import styles from './CategoryRootCard.module.css';

export default function CategoryRootCard({ node }) {
  if (!node) return null;
  const href = `/catalog/${node.fullSlug}`;
  const iconSrc = getCategoryIconBySlug(node.slug);
  const title = (node.name || node.slug || '').toString();

  return (
    <Link href={href} className={styles.cardLink} aria-label={title}>
      <div className={styles.card}>
        <h3 className={styles.cardTitle}>{title.toLowerCase()}</h3>
        <div className={styles.cardImageWrap}>
          <Image
            src={iconSrc}
            alt=""
            width={239}
            height={239}
            className={styles.cardImage}
            priority={node.level === 0 && node.sortOrder < 3}
          />
        </div>
      </div>
    </Link>
  );
}
