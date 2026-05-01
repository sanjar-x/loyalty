import styles from './page.module.css';

export default function Loading() {
  return (
    <section className={styles.page}>
      <div className={styles.header}>
        <div className="bg-app-card h-[46px] w-[46px] animate-pulse rounded-full" />
        <div className="bg-app-card h-9 w-56 animate-pulse rounded-lg" />
      </div>

      <div className="flex flex-col gap-3 lg:grid lg:grid-cols-[minmax(0,1fr)_413px] lg:gap-6">
        <div className="min-w-0">
          <div className={styles.breadcrumbs}>
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="bg-app-card h-[46px] animate-pulse rounded-[15px]"
              />
            ))}
          </div>

          <div className="border-app-card mb-3 rounded-3xl border-[3px] bg-white px-7 py-6">
            <div className="bg-app-card mb-5 h-8 w-52 animate-pulse rounded-lg" />
            <div className="space-y-3">
              <div className="bg-app-card h-[52px] animate-pulse rounded-2xl" />
              <div className="bg-app-card h-[52px] animate-pulse rounded-2xl" />
              <div className="bg-app-card h-[52px] animate-pulse rounded-2xl" />
            </div>
          </div>

          <div className="border-app-card mb-3 rounded-3xl border-[3px] bg-white px-7 py-6">
            <div className="bg-app-card mb-5 h-8 w-40 animate-pulse rounded-lg" />
            <div className="space-y-3">
              <div className="bg-app-card h-[52px] animate-pulse rounded-2xl" />
              <div className="bg-app-card h-[52px] animate-pulse rounded-2xl" />
            </div>
          </div>

          <div className="border-app-card mb-3 rounded-3xl border-[3px] bg-white px-7 py-6">
            <div className="bg-app-card mb-5 h-8 w-36 animate-pulse rounded-lg" />
            <div className="flex gap-3">
              <div className="bg-app-card h-28 w-28 animate-pulse rounded-2xl" />
              <div className="bg-app-card h-28 w-28 animate-pulse rounded-2xl" />
            </div>
          </div>

          <div className="border-app-card mb-3 rounded-3xl border-[3px] bg-white px-7 py-6">
            <div className="bg-app-card mb-5 h-8 w-24 animate-pulse rounded-lg" />
            <div className="flex gap-3">
              <div className="bg-app-card h-[52px] flex-1 animate-pulse rounded-2xl" />
              <div className="bg-app-card h-[52px] flex-1 animate-pulse rounded-2xl" />
            </div>
          </div>
        </div>

        <aside className="min-w-0">
          <div className="border-app-card rounded-3xl border-[3px] bg-white px-7 py-6">
            <div className="bg-app-card mb-4 h-7 w-36 animate-pulse rounded-lg" />
            <div className="bg-app-card h-80 animate-pulse rounded-3xl" />
          </div>
        </aside>
      </div>
    </section>
  );
}
