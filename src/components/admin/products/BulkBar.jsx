'use client';

import { pluralizeRu } from '@/lib/utils';
import styles from './products.module.css';

export function BulkBar({ selectedCount, onArchive }) {
  const selectedLabel = `${selectedCount.toLocaleString('ru-RU')} ${pluralizeRu(selectedCount, 'товар', 'товара', 'товаров')}`;

  return (
    <>
      <div className={styles.bulkBar}>
        <div className={styles.bulkBarInner}>
          <div className={styles.bulkBarLeft}>
            <span className={styles.bulkBarCheck} aria-hidden="true">
              ✓
            </span>
            <span className={styles.bulkBarCount}>{selectedLabel}</span>
          </div>

          <div className={styles.bulkBarRight}>
            <button
              type="button"
              onClick={onArchive}
              className={styles.bulkBarPrimary}
            >
              В архив
            </button>
          </div>
        </div>
      </div>
      <div className={styles.bulkBarSpacer} />
    </>
  );
}
