'use client';

import { cn } from '@/shared/lib/ui-utils';

import styles from './page.module.css';

/** Sprint 6: extracted from app/cart/page.jsx. */
export default function CartSkeleton({ count = 3 }) {
  const n = Math.max(1, Math.trunc(Number(count) || 3));
  return (
    <div className={styles.p0} aria-busy="true" aria-live="polite">
      <div className={styles.spaceY3} aria-hidden="true">
        {Array.from({ length: n }).map((_, idx) => (
          <div key={idx} className={styles.c15}>
            <div className={cn(styles.c16, styles.tw6)}>
              <div className={cn(styles.c17, styles.tw7)}>
                <div className={styles.skelImg} />
              </div>

              <div className={cn(styles.c19, styles.skelBody)}>
                <div className={styles.skelLineLg} />
                <div className={styles.skelLineSm} />
                <div className={styles.skelLineXs} />
                <div className={styles.skelPrice} />
                <div className={styles.skelLineSm} />
                <div className={styles.skelRow}>
                  <div className={styles.skelIcons} />
                  <div className={styles.skelQty} />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className={styles.c37} aria-hidden="true">
        <div className={styles.skelSummaryLineLg} />
        <div className={styles.skelSummaryLineSm} />
        <div className={styles.skelSummaryLineSm} />
      </div>
    </div>
  );
}
