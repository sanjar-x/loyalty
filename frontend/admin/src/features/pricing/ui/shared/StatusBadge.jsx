import { cn } from '@/shared/lib/utils';

const VARIANTS = {
  active: 'bg-emerald-100 text-emerald-700',
  frozen: 'bg-red-100 text-red-700',
  deactivated: 'bg-gray-100 text-gray-500',
  draft: 'bg-amber-100 text-amber-700',
  published: 'bg-emerald-100 text-emerald-700',
  archived: 'bg-gray-100 text-gray-500',
};

const LABELS = {
  active: 'Активен',
  frozen: 'Заморожен',
  deactivated: 'Деактивирован',
  draft: 'Черновик',
  published: 'Опубликовано',
  archived: 'Архив',
};

export function StatusBadge({ status, className }) {
  const variant = VARIANTS[status] || VARIANTS.deactivated;
  const label = LABELS[status] || status;

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        variant,
        className,
      )}
    >
      {label}
    </span>
  );
}
