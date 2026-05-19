import { cn } from '@/shared/lib/utils';

export function Metric({ title, value, change, formatValue }) {
  const sign = change > 0 ? '+' : '';
  const displayValue = formatValue
    ? formatValue(value)
    : value.toLocaleString('ru-RU');

  return (
    <div>
      <div className="flex items-end gap-2 leading-none">
        <p className="m-0 overflow-hidden text-[26px] leading-8 font-bold tracking-[-0.42px] text-ellipsis whitespace-nowrap text-black">
          {displayValue}
        </p>
        <span
          className={cn(
            'pb-[2px] text-base leading-8 font-medium tracking-[-0.42px]',
            change >= 0 ? 'text-[#429700]' : 'text-[#aa2d2d]',
          )}
        >
          {sign}
          {Math.abs(change)}%
        </span>
      </div>
      <p className="m-0 mt-[2px] text-base leading-5 font-medium text-[#7e7e7e]">
        {title}
      </p>
    </div>
  );
}
