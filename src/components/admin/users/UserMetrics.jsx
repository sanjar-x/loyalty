'use client';

import { useMemo, useState } from 'react';
import { DateRangePicker } from '@/components/admin/DateRangePicker';
import { calculatePeriodStats, isWithinRange } from '@/lib/stats';
import styles from '@/app/admin/users/page.module.css';

const initialRange = { from: null, to: null };

export function Metric({ title, value, change }) {
  const sign = change > 0 ? '+' : '';

  return (
    <div className="min-w-0">
      <div className={styles.metricValueRow}>
        <p className={styles.metricValue}>{value.toLocaleString('ru-RU')}</p>
        <span
          className={`${styles.metricChange} ${
            change >= 0
              ? styles.metricChangePositive
              : styles.metricChangeNegative
          }`}
        >
          {sign}
          {Math.abs(change)}%
        </span>
      </div>
      <p className={styles.metricTitle}>{title}</p>
    </div>
  );
}

export function UserMetrics({ users }) {
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

        <div className="min-w-0">
          <p className={styles.metricValue}>
            {selectedUsersCount.toLocaleString('ru-RU')}
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

        <div className="min-w-0">
          <p className={styles.metricValue}>
            {users.length.toLocaleString('ru-RU')}
          </p>
          <p className={styles.metricTitle}>Все время</p>
        </div>
      </div>
    </section>
  );
}
