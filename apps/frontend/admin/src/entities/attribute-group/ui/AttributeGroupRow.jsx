'use client';

import { i18n } from '@/shared/lib/utils';

export function AttributeGroupRow({ group, onEdit, onDelete }) {
  return (
    <tr className="border-app-border border-b last:border-b-0">
      <td className="px-4 py-3">
        <div className="flex flex-col gap-0.5">
          <p className="text-app-text-dark text-sm font-medium">
            {i18n(group.nameI18N, group.code)}
          </p>
          <p className="text-app-muted font-mono text-xs">{group.code}</p>
        </div>
      </td>
      <td className="text-app-muted px-4 py-3 text-sm">
        Порядок: {group.sortOrder}
      </td>
      <td className="px-4 py-3 text-right">
        <div className="inline-flex gap-2">
          <button
            type="button"
            onClick={() => onEdit?.(group)}
            className="border-app-border text-app-text-dark hover:bg-app-card rounded-md border px-3 py-1 text-xs font-medium"
          >
            Редактировать
          </button>
          <button
            type="button"
            onClick={() => onDelete?.(group)}
            className="rounded-md border border-red-200 px-3 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
          >
            Удалить
          </button>
        </div>
      </td>
    </tr>
  );
}
