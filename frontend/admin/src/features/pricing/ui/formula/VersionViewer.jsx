'use client';

import { StatusBadge } from '../shared/StatusBadge';
import { formatDateTime } from '@/shared/lib/utils';

function formatBinding(binding) {
  const label = binding.label || binding.name || '?';
  const name = binding.name || '?';
  const tag = binding.component_tag || binding.componentTag || 'intermediate';
  const expr = binding.expr ? JSON.stringify(binding.expr, null, 2) : '…';
  return { label, name, tag, expr };
}

export function VersionViewer({ version }) {
  if (!version) {
    return (
      <div className="border-app-border text-app-muted flex items-center justify-center rounded-xl border border-dashed p-12 text-sm">
        Выберите версию для просмотра
      </div>
    );
  }

  const bindings = version.ast?.bindings ?? [];

  return (
    <div className="border-app-border flex flex-col gap-3 rounded-xl border bg-white p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-app-text text-lg font-semibold">
            v{version.versionNumber}
          </span>
          <StatusBadge status={version.status} />
        </div>
        <div className="text-app-muted flex items-center gap-3 text-xs">
          {version.publishedAt && (
            <span>Опубликовано: {formatDateTime(version.publishedAt)}</span>
          )}
          {version.createdAt && (
            <span>Создано: {formatDateTime(version.createdAt)}</span>
          )}
        </div>
      </div>

      {bindings.length === 0 ? (
        <div className="text-app-muted rounded-lg bg-[#fafafa] p-4 text-sm">
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
                  {label !== name && (
                    <span className="text-gray-600"> ({name})</span>
                  )}
                  <span className="text-gray-500"> = </span>
                  <span className="text-gray-300">{expr}</span>
                  <span className="ml-4 text-gray-600">[{tag}]</span>
                </div>
              );
            })}
          </pre>
        </div>
      )}

      {version.ast?.version && (
        <span className="text-app-muted text-xs">
          AST version: {version.ast.version}
        </span>
      )}
    </div>
  );
}
