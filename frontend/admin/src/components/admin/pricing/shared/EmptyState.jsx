import { cn } from '@/lib/utils';

export function EmptyState({ title, description, action, className }) {
  return (
    <div className={cn('flex flex-col items-center gap-3 py-16 text-center', className)}>
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#f4f3f1]">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#878b93" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 5v14M5 12h14" />
        </svg>
      </div>
      <p className="text-base font-semibold text-app-text">{title}</p>
      {description && (
        <p className="max-w-sm text-sm text-app-muted">{description}</p>
      )}
      {action && (
        <button
          onClick={action.onClick}
          className="mt-1 rounded-lg bg-app-text px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
