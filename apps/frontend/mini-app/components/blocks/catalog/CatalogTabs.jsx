'use client';

import styles from './CatalogTabs.module.css';

export default function CatalogTabs({ activeTab, onTabChange }) {
  const indicatorWidth = activeTab === 'catalog' ? 82 : 69;

  return (
    <div className={styles.root}>
      <div className={styles.row}>
        <button onClick={() => onTabChange('catalog')} type="button" className={styles.tab}>
          Каталог
        </button>
        <button onClick={() => onTabChange('brands')} type="button" className={styles.tab}>
          Бренды
        </button>
      </div>
      <div className={styles.line} />
      <div
        className={styles.indicatorWrap}
        style={{
          transform: activeTab === 'catalog' ? 'translateX(0%)' : 'translateX(100%)',
        }}
        aria-hidden="true"
      >
        <div className={styles.indicatorBar} style={{ width: indicatorWidth }} />
      </div>
    </div>
  );
}
