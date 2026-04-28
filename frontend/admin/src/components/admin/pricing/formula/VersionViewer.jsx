'use client';

import { StatusBadge } from '../shared/StatusBadge';
import { formatDateTime } from '@/lib/utils';

function formatBinding(binding) {
  const label = binding.label || binding.name || '?';
  const name = binding.name || '?';
  const tag = binding.component_tag || binding.componentTag || 'intermediate';
  const expr = binding.expr
    ? JSON.stringify(binding.expr, null, 2)
    : '…';
  return { label, name, tag, expr };
}

export function VersionViewer({ version }) {
  if (!version) {
    return (
      <div className="flex items-center justify-center rounded-xl border border-dashed border-app-border p-12 text-sm text-app-muted">
        Выберите версию для просмотра
      </div>
    );
  }

  const bindings = version.ast?.bindings ?? [];

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-app-border bg-white p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold text-app-text">
            v{version.versionNumber}
          </span>
          <StatusBadge status={version.status} />
        </div>
        <div className="flex items-center gap-3 text-xs text-app-muted">
          {version.publishedAt && (
            <span>Опубликовано: {formatDateTime(version.publishedAt)}</span>
          )}
          {version.createdAt && (
            <span>Создано: {formatDateTime(version.createdAt)}</span>
          )}
        </div>
      </div>

      {bindings.length === 0 ? (
        <div className="rounded-lg bg-[#fafafa] p-4 text-sm text-app-muted">
          Формула пуста
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg bg-[#1e1e2e] p-4">
          <pre className="text-sm leading-6">
            {bindings.map((b, i) => {
              const { label, name, tag, expr } = formatBinding(b);
              return (
                <div key={i}>
                  <span className="text-emerald-400">{label}</span>
                  {label !== name && <span className="text-gray-600"> ({name})</span>}
                  <span className="text-gray-500"> = </span>
                  <span className="text-gray-300">{expr}</span>
                  <span className="ml-4 text-gray-600">
                    [{tag}]
                  </span>
                </div>
              );
            })}
          </pre>
        </div>
      )}

      {version.ast?.version && (
        <span className="text-xs text-app-muted">AST version: {version.ast.version}</span>
      )}
    </div>
  );
}
