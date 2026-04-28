'use client';

import { cn } from '@/lib/utils';
import { StatusBadge } from '../shared/StatusBadge';
import { formatDateTime } from '@/lib/utils';

export function VersionsList({ versions, draft, selectedId, onSelect, onSelectDraft }) {
  return (
    <div className="flex flex-col gap-1 overflow-y-auto rounded-xl border border-app-border bg-[#fafafa] p-2" style={{ maxHeight: '500px' }}>
      {draft && (
        <button
          onClick={onSelectDraft}
          className={cn(
            'flex flex-col gap-1 rounded-lg px-3 py-2 text-left transition-colors',
            selectedId === draft.versionId
              ? 'bg-white shadow-sm ring-1 ring-app-border'
              : 'hover:bg-white/60',
          )}
        >
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-app-text">Черновик</span>
            <StatusBadge status="draft" />
          </div>
          <span className="text-xs text-app-muted">v{draft.versionNumber}</span>
        </button>
      )}
      {versions.map((v) => (
        <button
          key={v.versionId}
          onClick={() => onSelect(v)}
          className={cn(
            'flex flex-col gap-1 rounded-lg px-3 py-2 text-left transition-colors',
            selectedId === v.versionId
              ? 'bg-white shadow-sm ring-1 ring-app-border'
              : 'hover:bg-white/60',
          )}
        >
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-app-text">v{v.versionNumber}</span>
            <StatusBadge status={v.status} />
          </div>
          {v.publishedAt && (
            <span className="text-xs text-app-muted">{formatDateTime(v.publishedAt)}</span>
          )}
        </button>
      ))}
    </div>
  );
}
