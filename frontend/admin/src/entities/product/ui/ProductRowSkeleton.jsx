'use client';

import styles from './products.module.css';

export function ProductRowSkeleton() {
  return (
    <div className={styles.skeletonCard}>
      <div className={styles.skeletonLine} style={{ width: '66%' }} />
      <div className={styles.skeletonBlock} />
      <div className={styles.skeletonLine} style={{ width: 160 }} />
    </div>
  );
}
