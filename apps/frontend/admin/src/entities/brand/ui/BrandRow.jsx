'use client';

import { cn } from '@/shared/lib/utils';

/**
 * Row in the admin brands table. Read-only — actions are wired by the
 * page layer so the entity stays free of feature-layer mutations.
 */
export function BrandRow({ brand, onEdit, onDelete }) {
  return (
    <tr className="border-app-border border-b last:border-b-0">
      <td className="px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="bg-app-card flex h-10 w-10 items-center justify-center overflow-hidden rounded-md">
            {brand.logoUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={brand.logoUrl}
                alt={`Логотип ${brand.name}`}
                className="h-full w-full object-contain"
              />
            ) : (
              <span className="text-app-muted text-[10px]">нет</span>
            )}
          </div>
          <div>
            <p className="text-app-text-dark text-sm font-medium">
              {brand.name}
            </p>
            <p className="text-app-muted font-mono text-xs">{brand.slug}</p>
          </div>
        </div>
      </td>
      <td className="px-4 py-3 text-right">
        <div className="inline-flex gap-2">
          <button
            type="button"
            onClick={() => onEdit?.(brand)}
            className={cn(
              'border-app-border text-app-text-dark hover:bg-app-card rounded-md border px-3 py-1 text-xs font-medium',
            )}
          >
            Редактировать
          </button>
          <button
            type="button"
            onClick={() => onDelete?.(brand)}
            className="rounded-md border border-red-200 px-3 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
          >
            Удалить
          </button>
        </div>
      </td>
    </tr>
  );
}
