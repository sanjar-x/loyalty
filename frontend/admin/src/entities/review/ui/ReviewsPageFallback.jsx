'use client';

import { cn } from '@/shared/lib/utils';
import styles from './styles/reviews.module.css';

function ReviewCardSkeleton() {
  return (
    <div className={styles.skeletonCard} aria-hidden="true">
      <div className={styles.skeletonCardGrid}>
        {/* Column 1 — Product */}
        <div className={styles.skeletonCol}>
          <div className={styles.skeletonRow}>
            <div
              className={styles.skelBox}
              style={{ height: 56, width: 56, borderRadius: 999 }}
            />
            <div className={styles.skeletonCol}>
              <div
                className={styles.skelBox}
                style={{ height: 14, width: 120, borderRadius: 8 }}
              />
              <div
                className={styles.skelBox}
                style={{ height: 14, width: 72, borderRadius: 8 }}
              />
            </div>
          </div>

          <div className={styles.skeletonRow}>
            <div
              className={styles.skelBox}
              style={{ height: 76, width: 76, borderRadius: 12 }}
            />
            <div className={styles.skeletonCol}>
              <div
                className={styles.skelBox}
                style={{ height: 14, width: '90%', borderRadius: 8 }}
              />
              <div
                className={styles.skelBox}
                style={{ height: 14, width: 140, borderRadius: 8 }}
              />
            </div>
          </div>
        </div>

        {/* Column 2 — Review */}
        <div className={styles.skeletonCol}>
          <div className={styles.skeletonRow}>
            <div
              className={styles.skelBox}
              style={{ height: 38, width: 38, borderRadius: 999 }}
            />
            <div
              className={styles.skelBox}
              style={{ height: 16, width: 96, borderRadius: 8 }}
            />
          </div>
          <div className={styles.skeletonRow}>
            <div
              className={styles.skelBox}
              style={{ height: 14, width: 96, borderRadius: 8 }}
            />
            <div
              className={styles.skelBox}
              style={{ height: 14, width: 8, borderRadius: 8 }}
            />
            <div
              className={styles.skelBox}
              style={{ height: 14, width: 120, borderRadius: 8 }}
            />
          </div>

          <div className={styles.skeletonText}>
            <div
              className={styles.skelBox}
              style={{ height: 14, width: '92%', borderRadius: 8 }}
            />
            <div
              className={styles.skelBox}
              style={{ height: 14, width: '86%', borderRadius: 8 }}
            />
            <div
              className={styles.skelBox}
              style={{ height: 14, width: '78%', borderRadius: 8 }}
            />
          </div>
        </div>

        {/* Column 3 — Order */}
        <div className={styles.skeletonCol}>
          <div
            className={styles.skelBox}
            style={{ height: 14, width: 140, borderRadius: 8 }}
          />
          <div
            className={styles.skelBox}
            style={{ height: 14, width: 120, borderRadius: 8 }}
          />
          <div
            className={styles.skelBox}
            style={{ height: 34, width: 128, borderRadius: 999 }}
          />
        </div>

        {/* Column 4 — Actions */}
        <div className={styles.skeletonActions}>
          <div className={styles.skeletonRow}>
            <div
              className={styles.skelBox}
              style={{ height: 44, width: 132, borderRadius: 999 }}
            />
            <div
              className={styles.skelBox}
              style={{ height: 44, width: 44, borderRadius: 14 }}
            />
          </div>
          <div
            className={styles.skelBox}
            style={{ height: 44, width: 44, borderRadius: 14 }}
          />
        </div>
      </div>
    </div>
  );
}

export default function ReviewsPageFallback() {
  return (
    <section className={styles.page}>
      <div className={styles.header}>
        <div>
          <div
            className={cn(styles.skelBox)}
            style={{ height: 44, width: 160 }}
          />
          <div className={styles.filters}>
            <div
              className={cn(styles.skelBox)}
              style={{ height: 34, width: 128, borderRadius: 999 }}
            />
            <div
              className={cn(styles.skelBox)}
              style={{ height: 34, width: 160, borderRadius: 999 }}
            />
            <div
              className={cn(styles.skelBox)}
              style={{ height: 34, width: 112, borderRadius: 999 }}
            />
            <div
              className={cn(styles.skelBox)}
              style={{ height: 34, width: 34, borderRadius: 999 }}
            />
          </div>
        </div>
        <div
          className={cn(styles.skelBox, styles.summarySkeleton)}
          style={{ height: 96, width: 420, borderRadius: 12 }}
        />
      </div>

      <div className={styles.list} aria-hidden="true">
        <ReviewCardSkeleton />
        <ReviewCardSkeleton />
        <ReviewCardSkeleton />
      </div>

      <div className={styles.pagination} aria-hidden="true">
        {Array.from({ length: 7 }, (_, idx) => (
          <div
            key={idx}
            className={styles.skelBox}
            style={{ height: 36, width: 36, borderRadius: 12 }}
          />
        ))}
      </div>
    </section>
  );
}
