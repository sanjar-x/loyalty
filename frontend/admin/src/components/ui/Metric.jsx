import { cn } from '@/lib/utils';

export function Metric({ title, value, change, formatValue }) {
  const sign = change > 0 ? '+' : '';
  const displayValue = formatValue
    ? formatValue(value)
    : value.toLocaleString('ru-RU');

  return (
    <div>
      <div className="flex items-end gap-2 leading-none">
        <p className="m-0 text-[26px] font-bold leading-8 tracking-[-0.42px] text-black overflow-hidden text-ellipsis whitespace-nowrap">
          {displayValue}
        </p>
        <span
          className={cn(
            'pb-[2px] text-base font-medium leading-8 tracking-[-0.42px]',
            change >= 0 ? 'text-[#429700]' : 'text-[#aa2d2d]',
          )}
        >
          {sign}
          {Math.abs(change)}%
        </span>
      </div>
      <p className="mt-[2px] m-0 text-base font-medium leading-5 text-[#7e7e7e]">
        {title}
      </p>
    </div>
  );
}
