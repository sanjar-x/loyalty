import styles from './page.module.css';

export default function AddProductLoading() {
  return (
    <section className={styles.page}>
      <div className={styles.header}>
        <div className="bg-app-card h-[46px] w-[46px] animate-pulse rounded-full" />
        <div className="bg-app-card h-9 w-64 animate-pulse rounded-lg" />
      </div>

      <div className={styles.columns}>
        {[3, 10].map((count, col) => (
          <div key={col} className={styles.column}>
            <div className={styles.columnList}>
              {Array.from({ length: count }).map((_, i) => (
                <div key={i} className={styles.itemSkeleton} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
