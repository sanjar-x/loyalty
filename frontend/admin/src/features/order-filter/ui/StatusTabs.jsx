import { STATUS_LABELS } from '@/entities/order';
import { cn } from '@/shared/lib/utils';

const allStatuses = [
  'placed',
  'in_transit',
  'pickup_point',
  'canceled',
  'received',
];

export function StatusTabs({ activeStatus, counts, onChange }) {
  return (
    <div className="flex items-end gap-10 overflow-x-auto border-b border-[#d9d9db] px-0.5 pb-0">
      {allStatuses.map((status) => (
        <button
          key={status}
          type="button"
          onClick={() => onChange(status)}
          className={cn(
            'shrink-0 border-b-[3px] border-transparent pb-2.5 text-[20px] leading-5 font-medium tracking-normal whitespace-nowrap text-[#000000] transition-colors',
            'hover:text-[#000000]',
            activeStatus === status && 'border-[#000000] text-[#000000]',
          )}
        >
          {STATUS_LABELS[status]}
          <span className="ml-2 text-base leading-5 font-medium text-[#7e7e7e]">
            {counts[status] ?? 0}
          </span>
        </button>
      ))}
    </div>
  );
}
