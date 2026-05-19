'use client';

import { useMemo, useState } from 'react';

import { calculatePeriodStats, isWithinRange } from '@/shared/lib/stats';
import { DateRangePicker } from '@/shared/ui/DateRangePicker';

import styles from './styles/customers.module.css';

const initialRange = { from: null, to: null };

function formatNumber(value) {
  return Number(value || 0).toLocaleString('ru-RU');
}

function formatChange(change) {
  const sign = change > 0 ? '+' : change < 0 ? '−' : '';
  return `${sign}${Math.abs(change)}%`;
}

export function Metric({ title, value, change }) {
  const className =
    change > 0
      ? styles.metricChangePositive
      : change < 0
        ? styles.metricChangeNegative
        : styles.metricChangeNeutral;

  return (
    <div className={styles.metric}>
      <div className={styles.metricValueRow}>
        <p className={styles.metricValue}>{formatNumber(value)}</p>
        {change !== undefined && change !== null && (
          <span className={`${styles.metricChange} ${className}`}>
            {formatChange(change)}
          </span>
        )}
      </div>
      <p className={styles.metricTitle}>{title}</p>
    </div>
  );
}

/**
 * Horizontal stats card mirroring the Figma «Пользователи» strip.
 *
 * `users` is the current page slice from `/admin/customers` — today/week/month
 * are computed locally against that slice, while `total` ('Все время') comes
 * from the response envelope and is authoritative across the dataset.
 */
export function CustomerMetrics({ users = [], total = 0 }) {
  const [range, setRange] = useState(initialRange);

  const userToday = useMemo(
    () => calculatePeriodStats(users, 'createdAt', 'day'),
    [users],
  );
  const userWeek = useMemo(
    () => calculatePeriodStats(users, 'createdAt', 'week'),
    [users],
  );
  const userMonth = useMemo(
    () => calculatePeriodStats(users, 'createdAt', 'month'),
    [users],
  );

  const hasRange = Boolean(range.from && range.to);
  const selectedUsersCount = useMemo(() => {
    if (!hasRange) return 0;
    return users.filter((user) => isWithinRange(user.createdAt, range)).length;
  }, [users, hasRange, range]);

  return (
    <section className={styles.metricsCard}>
      <p className={styles.cardLabel}>Пользователи</p>

      <div className={styles.metricsGrid}>
        <Metric
          title="Сегодня"
          value={userToday.value}
          change={userToday.change}
        />
        <Metric
          title="Неделя"
          value={userWeek.value}
          change={userWeek.change}
        />
        <Metric
          title="Месяц"
          value={userMonth.value}
          change={userMonth.change}
        />

        <div className={styles.metric}>
          <p className={styles.metricValue}>
            {formatNumber(selectedUsersCount)}
          </p>
          <div className={styles.rangeRow}>
            <DateRangePicker value={range} onChange={setRange} />
            {hasRange && (
              <button
                type="button"
                onClick={() => setRange(initialRange)}
                className={styles.rangeClear}
                aria-label="Очистить период"
              >
                ×
              </button>
            )}
          </div>
        </div>

        <div className={styles.metric}>
          <p className={styles.metricValue}>{formatNumber(total)}</p>
          <p className={styles.metricTitle}>Все время</p>
        </div>
      </div>
    </section>
  );
}
