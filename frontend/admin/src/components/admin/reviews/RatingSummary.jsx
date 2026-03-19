'use client';

import { useMemo } from 'react';
import { Star } from '@/components/ui/StarsRow';
import styles from '@/app/admin/reviews/page.module.css';

export default function RatingSummary({ reviews }) {
  const summary = useMemo(() => {
    const total = reviews.length;
    const counts = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
    let sum = 0;
    let validCount = 0;
    reviews.forEach((r) => {
      const raw = Number(r.rating);
      if (!Number.isFinite(raw) || raw < 1 || raw > 5) return;
      const rating = Math.round(raw);
      counts[rating] += 1;
      sum += rating;
      validCount += 1;
    });
    const average = validCount ? sum / validCount : 0;
    return { total, counts, average };
  }, [reviews]);

  const averageLabel = summary.average ? summary.average.toFixed(1) : '0.0';

  return (
    <div className={styles.summary}>
      <div className={styles.summaryLeft}>
        <div className={styles.summaryValueRow}>
          <p className={styles.summaryValue}>{averageLabel}</p>
          <div>
            <Star filled />
          </div>
        </div>
        <p className={styles.summarySub}>
          {summary.total.toLocaleString('ru-RU')} отзывов
        </p>
      </div>

      <div className={styles.summaryList}>
        {[5, 4, 3, 2, 1].map((stars) => {
          const count = summary.counts[stars] ?? 0;
          const ratio = summary.total ? count / summary.total : 0;
          const width = `${Math.round(ratio * 100)}%`;

          return (
            <div key={stars} className={styles.summaryRow}>
              <div className={styles.summaryStarLabel}>
                <span
                  className={styles.summaryStars}
                  aria-label={`${stars} из 5`}
                >
                  {Array.from({ length: stars }, (_, idx) => (
                    <Star key={idx} filled />
                  ))}
                </span>
              </div>
              <div className={styles.summaryBar}>
                <div className={styles.summaryBarFill} style={{ width }} />
              </div>
              <span className={styles.summaryCount}>
                {count.toLocaleString('ru-RU')}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
