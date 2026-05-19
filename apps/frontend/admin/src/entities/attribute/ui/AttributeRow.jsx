'use client';

import { Badge } from '@/shared/ui/Badge';
import { i18n } from '@/shared/lib/utils';

import {
  DATA_TYPE_LABELS,
  LEVEL_LABELS,
  UI_TYPE_LABELS,
} from '../lib/constants';

/**
 * Read-only row in the admin attributes table. Mutations are wired up
 * by the parent — the entity stays free of feature-layer dependencies.
 */
export function AttributeRow({ attribute, onEdit, onDelete }) {
  return (
    <tr className="border-app-border border-b last:border-b-0">
      <td className="px-4 py-3">
        <div className="flex flex-col gap-0.5">
          <p className="text-app-text-dark text-sm font-medium">
            {i18n(attribute.nameI18N, attribute.code)}
          </p>
          <p className="text-app-muted font-mono text-xs">
            {attribute.code} · {attribute.slug}
          </p>
        </div>
      </td>
      <td className="px-4 py-3">
        <div className="flex flex-wrap gap-1">
          <Badge variant="muted">
            {LEVEL_LABELS[attribute.level] ?? attribute.level}
          </Badge>
          <Badge>
            {DATA_TYPE_LABELS[attribute.dataType] ?? attribute.dataType}
          </Badge>
          <Badge variant="dark">
            {UI_TYPE_LABELS[attribute.uiType] ?? attribute.uiType}
          </Badge>
        </div>
      </td>
      <td className="px-4 py-3 text-sm">
        {/* Audit 8.1 — emoji glyphs wrapped in aria-hidden so screen
            readers read «справочник», «фильтр» etc. instead of
            announcing the visual shorthand («книги emoji справочник»). */}
        <ul className="text-app-muted flex flex-wrap gap-2">
          {attribute.isDictionary && (
            <li>
              <span aria-hidden="true">📚</span> справочник
            </li>
          )}
          {attribute.isFilterable && (
            <li>
              <span aria-hidden="true">🔎</span> фильтр
            </li>
          )}
          {attribute.isSearchable && (
            <li>
              <span aria-hidden="true">🔍</span> поиск (вес{' '}
              {attribute.searchWeight})
            </li>
          )}
          {attribute.isComparable && (
            <li>
              <span aria-hidden="true">⚖</span> сравнение
            </li>
          )}
          {attribute.isVisibleOnCard && (
            <li>
              <span aria-hidden="true">🃏</span> карточка
            </li>
          )}
        </ul>
      </td>
      <td className="px-4 py-3 text-right">
        <div className="inline-flex gap-2">
          <button
            type="button"
            onClick={() => onEdit?.(attribute)}
            className="border-app-border text-app-text-dark hover:bg-app-card rounded-md border px-3 py-1 text-xs font-medium"
          >
            Редактировать
          </button>
          <button
            type="button"
            onClick={() => onDelete?.(attribute)}
            className="rounded-md border border-red-200 px-3 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
          >
            Удалить
          </button>
        </div>
      </td>
    </tr>
  );
}
