'use client';

import { Badge } from '@/shared/ui/Badge';
import { cn, i18n } from '@/shared/lib/utils';

/**
 * Read-only row for attribute values. Activate/deactivate/edit/delete
 * actions are wired from the parent so the entity slice doesn't import
 * mutation hooks (those live in `api/mutations.js` for consumers).
 */
export function AttributeValueRow({ value, onEdit, onToggleActive, onDelete }) {
  const swatchHex =
    typeof value.metaData === 'object' && value.metaData?.hex
      ? String(value.metaData.hex)
      : null;

  return (
    <tr
      className={cn(
        'border-app-border border-b last:border-b-0',
        !value.isActive && 'bg-app-card/40',
      )}
    >
      <td className="px-4 py-3">
        <div className="flex items-center gap-3">
          {swatchHex ? (
            <span
              aria-hidden="true"
              className="border-app-border block h-6 w-6 rounded-full border"
              style={{ backgroundColor: swatchHex }}
            />
          ) : null}
          <div className="flex flex-col gap-0.5">
            <p className="text-app-text-dark text-sm font-medium">
              {i18n(value.valueI18N, value.code)}
            </p>
            <p className="text-app-muted font-mono text-xs">
              {value.code} · {value.slug}
            </p>
          </div>
        </div>
      </td>
      <td className="px-4 py-3 text-sm">
        {value.valueGroup ? (
          <Badge variant="muted">{value.valueGroup}</Badge>
        ) : (
          <span className="text-app-muted">—</span>
        )}
      </td>
      <td className="text-app-muted px-4 py-3 text-sm">
        Порядок: {value.sortOrder}
      </td>
      <td className="px-4 py-3">
        {value.isActive ? (
          <Badge variant="default">Активно</Badge>
        ) : (
          <Badge variant="dark">Деактивировано</Badge>
        )}
      </td>
      <td className="px-4 py-3 text-right">
        <div className="inline-flex flex-wrap justify-end gap-2">
          <button
            type="button"
            onClick={() => onEdit?.(value)}
            className="border-app-border text-app-text-dark hover:bg-app-card rounded-md border px-3 py-1 text-xs font-medium"
          >
            Редактировать
          </button>
          <button
            type="button"
            onClick={() => onToggleActive?.(value)}
            className="border-app-border text-app-text-dark hover:bg-app-card rounded-md border px-3 py-1 text-xs font-medium"
          >
            {value.isActive ? 'Деактивировать' : 'Активировать'}
          </button>
          <button
            type="button"
            onClick={() => onDelete?.(value)}
            className="rounded-md border border-red-200 px-3 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
          >
            Удалить
          </button>
        </div>
      </td>
    </tr>
  );
}
