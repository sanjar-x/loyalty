import styles from '../page.module.css';

export default function Loading() {
  return (
    <section className={styles.page}>
      {/* Header */}
      <div className={styles.header}>
        <div className="h-[46px] w-[46px] rounded-full bg-app-card animate-pulse" />
        <div className="h-9 w-56 rounded-lg bg-app-card animate-pulse" />
      </div>

      <div className={styles.layout}>
        {/* Main column */}
        <div className={styles.mainColumn}>
          {/* Breadcrumbs skeleton */}
          <div className={styles.breadcrumbs}>
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-[46px] rounded-[15px] bg-app-card animate-pulse"
              />
            ))}
          </div>

          {/* "Основные данные" card */}
          <div className={styles.card}>
            <div className="h-8 w-52 rounded-lg bg-app-card animate-pulse mb-5" />
            <div className="space-y-3">
              <div className="h-[52px] rounded-2xl bg-app-card animate-pulse" />
              <div className="h-[52px] rounded-2xl bg-app-card animate-pulse" />
              <div className="h-[52px] rounded-2xl bg-app-card animate-pulse" />
            </div>
          </div>

          {/* Attributes card */}
          <div className={styles.card} style={{ marginTop: 12 }}>
            <div className="h-8 w-40 rounded-lg bg-app-card animate-pulse mb-5" />
            <div className="space-y-3">
              <div className="h-[52px] rounded-2xl bg-app-card animate-pulse" />
              <div className="h-[52px] rounded-2xl bg-app-card animate-pulse" />
            </div>
          </div>

          {/* Images card */}
          <div className={styles.card} style={{ marginTop: 12 }}>
            <div className="h-8 w-36 rounded-lg bg-app-card animate-pulse mb-5" />
            <div className="flex gap-3">
              <div className="h-28 w-28 rounded-2xl bg-app-card animate-pulse" />
              <div className="h-28 w-28 rounded-2xl bg-app-card animate-pulse" />
            </div>
          </div>

          {/* Price card */}
          <div className={styles.card} style={{ marginTop: 12 }}>
            <div className="h-8 w-24 rounded-lg bg-app-card animate-pulse mb-5" />
            <div className="flex gap-3">
              <div className="h-[52px] flex-1 rounded-2xl bg-app-card animate-pulse" />
              <div className="h-[52px] flex-1 rounded-2xl bg-app-card animate-pulse" />
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <aside className={styles.sidebar}>
          <div className={styles.previewCard}>
            <div className="h-7 w-36 rounded-lg bg-app-card animate-pulse mb-4" />
            <div className="h-80 rounded-3xl bg-app-card animate-pulse" />
          </div>
        </aside>
      </div>
    </section>
  );
}
