'use client';

import { i18n } from '@/lib/utils';
import { StatusBadge } from '../shared/StatusBadge';

const SCOPE_LABELS = {
  global: 'Global',
  supplier: 'Supplier',
  category: 'Category',
  range: 'Range',
  product_input: 'Product input',
  sku_input: 'SKU input',
};

const TYPE_LABELS = {
  decimal: 'Число',
  integer: 'Целое',
  percent: 'Процент',
};

export function VariablesTable({ variables, onEdit, onDelete }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[720px] text-sm">
        <thead>
          <tr className="border-b border-app-border text-left text-xs font-medium text-app-muted">
            <th className="px-3 py-2.5">Код</th>
            <th className="px-3 py-2.5">Название</th>
            <th className="px-3 py-2.5">Scope</th>
            <th className="px-3 py-2.5">Тип</th>
            <th className="px-3 py-2.5">Ед. изм.</th>
            <th className="px-3 py-2.5">По умолчанию</th>
            <th className="px-3 py-2.5">Флаги</th>
            <th className="px-3 py-2.5 text-right">Действия</th>
          </tr>
        </thead>
        <tbody>
          {variables.map((v) => (
            <tr key={v.variableId} className="border-b border-[#f4f3f1] transition-colors hover:bg-[#fafafa]">
              <td className="px-3 py-2.5">
                <code className="rounded bg-[#f4f3f1] px-1.5 py-0.5 text-xs font-mono">
                  {v.code}
                </code>
              </td>
              <td className="px-3 py-2.5 text-app-text">{i18n(v.name, v.code)}</td>
              <td className="px-3 py-2.5">
                <span className="rounded-md bg-[#f0f0f0] px-2 py-0.5 text-xs font-medium text-app-muted">
                  {SCOPE_LABELS[v.scope] ?? v.scope}
                </span>
              </td>
              <td className="px-3 py-2.5 text-app-muted">{TYPE_LABELS[v.dataType] ?? v.dataType}</td>
              <td className="px-3 py-2.5 font-mono text-xs text-app-muted">{v.unit}</td>
              <td className="px-3 py-2.5 font-mono text-xs">
                {v.defaultValue != null ? v.defaultValue : <span className="text-app-muted">—</span>}
              </td>
              <td className="px-3 py-2.5">
                <div className="flex items-center gap-1">
                  {v.isRequired && <StatusBadge status="active" className="!text-[10px]" />}
                  {v.isFxRate && (
                    <span className="rounded bg-blue-100 px-1.5 py-0.5 text-[10px] font-medium text-blue-700">FX</span>
                  )}
                  {v.isSystem && (
                    <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium text-gray-500">SYS</span>
                  )}
                </div>
              </td>
              <td className="px-3 py-2.5 text-right">
                <div className="flex items-center justify-end gap-1">
                  <button
                    onClick={() => onEdit(v)}
                    className="rounded-lg p-1.5 text-app-muted transition-colors hover:bg-[#f4f3f1] hover:text-app-text"
                    title="Редактировать"
                  >
                    <svg className="h-4 w-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <path d="M11.5 1.5l3 3-9 9H2.5v-3l9-9z" />
                    </svg>
                  </button>
                  <button
                    onClick={() => onDelete(v)}
                    className="rounded-lg p-1.5 text-app-muted transition-colors hover:bg-red-50 hover:text-red-500"
                    title="Удалить"
                  >
                    <svg className="h-4 w-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                      <path d="M2 4h12M5.333 4V2.667a1.333 1.333 0 011.334-1.334h2.666a1.333 1.333 0 011.334 1.334V4m2 0v9.333a1.333 1.333 0 01-1.334 1.334H4.667a1.333 1.333 0 01-1.334-1.334V4h9.334z" />
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
