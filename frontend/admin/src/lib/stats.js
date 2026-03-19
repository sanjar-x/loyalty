import dayjs from '@/lib/dayjs';

export function calculatePeriodStats(items, dateField, scope) {
  const now = dayjs();
  const start = now.startOf(scope);
  const end = now.endOf(scope);
  const prevStart = start.subtract(1, scope);
  const prevEnd = end.subtract(1, scope);

  const currentCount = items.filter((item) => {
    const date = dayjs(item[dateField]);
    return date.isSameOrAfter(start) && date.isSameOrBefore(end);
  }).length;

  const previousCount = items.filter((item) => {
    const date = dayjs(item[dateField]);
    return date.isSameOrAfter(prevStart) && date.isSameOrBefore(prevEnd);
  }).length;

  const change =
    previousCount === 0
      ? currentCount > 0
        ? 100
        : 0
      : ((currentCount - previousCount) / previousCount) * 100;

  return { value: currentCount, change: Math.round(change) };
}

export function calculatePeriodSum(items, dateField, valueField, scope) {
  const now = dayjs();
  const start = now.startOf(scope);
  const end = now.endOf(scope);
  const prevStart = start.subtract(1, scope);
  const prevEnd = end.subtract(1, scope);

  const currentSum = items
    .filter((item) => {
      const date = dayjs(item[dateField]);
      return date.isSameOrAfter(start) && date.isSameOrBefore(end);
    })
    .reduce((acc, item) => acc + item[valueField], 0);

  const previousSum = items
    .filter((item) => {
      const date = dayjs(item[dateField]);
      return date.isSameOrAfter(prevStart) && date.isSameOrBefore(prevEnd);
    })
    .reduce((acc, item) => acc + item[valueField], 0);

  const change =
    previousSum === 0
      ? currentSum > 0
        ? 100
        : 0
      : ((currentSum - previousSum) / previousSum) * 100;

  return { value: currentSum, change: Math.round(change) };
}

export function isWithinRange(dateValue, range) {
  if (!range.from || !range.to) return false;
  const date = dayjs(dateValue);
  return (
    date.isSameOrAfter(range.from.startOf('day')) &&
    date.isSameOrBefore(range.to.endOf('day'))
  );
}
