import { cn } from '@/shared/lib/utils';

function SkeletonLine({ className }) {
  return (
    <div
      className={cn('bg-app-border-soft animate-pulse rounded-lg', className)}
    />
  );
}

export function LoadingSkeleton({ rows = 5, columns = 4 }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex gap-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <SkeletonLine key={i} className="h-9 w-24" />
        ))}
      </div>
      <div className="mt-2 flex flex-col gap-2">
        {Array.from({ length: rows }).map((_, row) => (
          <div key={row} className="flex gap-4 rounded-xl bg-white px-4 py-3">
            {Array.from({ length: columns }).map((_, col) => (
              <SkeletonLine
                key={col}
                className={cn('h-5', col === 0 ? 'w-32' : 'w-20')}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
