'use client';

import { useMemo } from 'react';
import { DateRangePicker } from '@/components/admin/DateRangePicker';
import { formatCurrency } from '@/lib/utils';
import { calculatePeriodStats, calculatePeriodSum, isWithinRange } from '@/lib/stats';
import { Metric } from '@/components/ui/Metric';

// TODO: The DateRangePicker appears twice (once for orders, once for revenue).
// This is intentional to allow independent range display per metric group,
// but the UX may be confusing since both pickers share the same state.
// Consider unifying into a single picker or clarifying the design intent.
export function TopMetrics({ orders, range, onRangeChange }) {
  const orderToday = useMemo(() => calculatePeriodStats(orders, 'createdAt', 'day'), [orders]);
  const orderWeek = useMemo(() => calculatePeriodStats(orders, 'createdAt', 'week'), [orders]);
  const orderMonth = useMemo(() => calculatePeriodStats(orders, 'createdAt', 'month'), [orders]);

  const revenueToday = useMemo(() => calculatePeriodSum(orders, 'createdAt', 'total', 'day'), [orders]);
  const revenueWeek = useMemo(() => calculatePeriodSum(orders, 'createdAt', 'total', 'week'), [orders]);
  const revenueMonth = useMemo(() => calculatePeriodSum(orders, 'createdAt', 'total', 'month'), [orders]);

  const hasRange = Boolean(range.from && range.to);

  const selectedOrdersCount = useMemo(
    () => (hasRange ? orders.filter((order) => isWithinRange(order.createdAt, range)).length : 0),
    [orders, hasRange, range],
  );

  return (
    <section className="rounded-2xl bg-[#f4f3f1] px-5 py-4">
      <p className="mb-4 text-base font-medium leading-5 text-[#7e7e7e]">Заказы</p>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 lg:gap-x-10">
        <Metric title="Сегодня" value={orderToday.value} change={orderToday.change} />
        <Metric title="Неделя" value={orderWeek.value} change={orderWeek.change} />
        <Metric title="Месяц" value={orderMonth.value} change={orderMonth.change} />

        <div className="min-w-0">
          <p className="text-[26px] font-bold leading-8 tracking-[-0.42px] text-[#3d3c3a]">{selectedOrdersCount}</p>
          <div className="mt-0.5 flex items-center gap-1 text-base font-medium leading-5 text-[#7e7e7e]">
            <DateRangePicker value={range} onChange={onRangeChange} />
            {hasRange && (
              <button
                type="button"
                onClick={() => onRangeChange({ from: null, to: null })}
                className="shrink-0 text-xl leading-none text-[#7e7e7e] transition-colors hover:text-[#2d2d2d]"
                aria-label="Очистить период"
              >
                ×
              </button>
            )}
          </div>
        </div>
      </div>

      <p className="mb-4 mt-4 text-base font-medium leading-5 text-[#7e7e7e]">Выручка</p>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 lg:gap-x-10">
        <Metric title="Сегодня" value={revenueToday.value} change={revenueToday.change} formatValue={formatCurrency} />
        <Metric title="Неделя" value={revenueWeek.value} change={revenueWeek.change} formatValue={formatCurrency} />
        <Metric title="Месяц" value={revenueMonth.value} change={revenueMonth.change} formatValue={formatCurrency} />
        <div className="min-w-0">
          <p className="text-[26px] font-bold leading-8 tracking-[-0.42px] text-[#3d3c3a]">0</p>
          <div className="mt-0.5">
            <DateRangePicker value={range} onChange={onRangeChange} forcePlaceholder />
          </div>
        </div>
      </div>
    </section>
  );
}
