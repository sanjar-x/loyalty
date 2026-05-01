import { REASON_FILTER_LABELS, REASON_FILTERS } from '@/entities/order';
import { cn } from '@/shared/lib/utils';

export function ReasonFilters({ reasonFilter, reasonCounts, onReasonChange }) {
  return (
    <div className="my-4 flex flex-wrap items-center gap-3">
      <button
        type="button"
        onClick={() => onReasonChange('all')}
        className={cn(
          'inline-flex h-[40px] items-center rounded-[50px] px-5 text-[16px] leading-5 font-medium',
          reasonFilter === 'all'
            ? 'bg-app-text-dark text-white'
            : 'bg-app-card text-[#000000]',
        )}
      >
        Все
      </button>

      {REASON_FILTERS.map((key) => (
        <button
          key={key}
          type="button"
          onClick={() => onReasonChange(key)}
          className={cn(
            'inline-flex h-[40px] items-center gap-1 rounded-[50px] px-5 text-[16px] leading-5 font-medium',
            reasonFilter === key
              ? 'bg-app-text-dark text-white'
              : 'bg-app-card text-[#000000]',
          )}
        >
          <span>{REASON_FILTER_LABELS[key]}</span>
          <span
            className={cn(
              reasonFilter === key ? 'text-[#c7c7c7]' : 'text-[#8b8b8b]',
            )}
          >
            {reasonCounts[key]}
          </span>
        </button>
      ))}
    </div>
  );
}
