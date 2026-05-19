'use client';

import Link from 'next/link';

import { i18n } from '@/shared/lib/utils';

export function AttributeTemplateRow({ template, onEdit, onDelete, onClone }) {
  return (
    <tr className="border-app-border border-b last:border-b-0">
      <td className="px-4 py-3">
        <div className="flex flex-col gap-0.5">
          <Link
            href={`/admin/settings/attribute-templates/${template.id}`}
            className="text-app-text-dark hover:text-app-text text-sm font-medium underline-offset-2 hover:underline"
          >
            {i18n(template.nameI18N, template.code)}
          </Link>
          <p className="text-app-muted font-mono text-xs">{template.code}</p>
        </div>
      </td>
      <td className="text-app-muted px-4 py-3 text-sm">
        Порядок: {template.sortOrder}
      </td>
      <td className="px-4 py-3 text-right">
        <div className="inline-flex flex-wrap justify-end gap-2">
          <button
            type="button"
            onClick={() => onClone?.(template)}
            className="border-app-border text-app-text-dark hover:bg-app-card rounded-md border px-3 py-1 text-xs font-medium"
          >
            Клонировать
          </button>
          <button
            type="button"
            onClick={() => onEdit?.(template)}
            className="border-app-border text-app-text-dark hover:bg-app-card rounded-md border px-3 py-1 text-xs font-medium"
          >
            Редактировать
          </button>
          <button
            type="button"
            onClick={() => onDelete?.(template)}
            className="rounded-md border border-red-200 px-3 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
          >
            Удалить
          </button>
        </div>
      </td>
    </tr>
  );
}
