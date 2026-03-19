'use client';

import { cn } from '@/lib/utils';
import { DateRangePicker } from '@/components/admin/DateRangePicker';
import { Metric } from '@/components/ui/Metric';
import styles from './products.module.css';

export function ProductMetrics({ metrics, dateRange, hasRange, onDateRangeChange }) {
  return (
    <div className={styles.metricsGrid}>
      {/* TODO: change percentages are placeholders — calculate from real historical data when available */}
      <Metric title="Сегодня" value={metrics.today} change={0} />
      <Metric title="Неделя" value={metrics.week} change={0} />
      <Metric title="Месяц" value={metrics.month} change={0} />

      <div>
        {/* TODO: range metric value is a placeholder — calculate from real data for the selected period */}
        <p className={styles.metricValue}>—</p>
        <div className="flex items-center gap-1 text-[#7e7e7e] text-base font-medium leading-5">
          <DateRangePicker
            value={dateRange}
            onChange={onDateRangeChange}
            placeholder="Выбрать период"
          />
          {hasRange && (
            <button
              type="button"
              onClick={() => onDateRangeChange({ from: null, to: null })}
              className="border-0 bg-transparent text-[#7e7e7e] text-xl leading-none cursor-pointer p-0"
              aria-label="Очистить период"
            >
              <svg
                width="13"
                height="13"
                viewBox="0 0 13 13"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  d="M1 1L6.5 6.5M12 12L6.5 6.5M6.5 6.5L11.6071 1M6.5 6.5L1 12"
                  stroke="#2D2D2D"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
