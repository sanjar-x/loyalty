'use client';

import { cn } from '@/shared/lib/utils';
import { StatusBadge } from '../shared/StatusBadge';
import { formatDateTime } from '@/shared/lib/utils';

export function VersionsList({
  versions,
  draft,
  selectedId,
  onSelect,
  onSelectDraft,
}) {
  return (
    <div
      className="border-app-border flex flex-col gap-1 overflow-y-auto rounded-xl border bg-[#fafafa] p-2"
      style={{ maxHeight: '500px' }}
    >
      {draft && (
        <button
          onClick={onSelectDraft}
          className={cn(
            'flex flex-col gap-1 rounded-lg px-3 py-2 text-left transition-colors',
            selectedId === draft.versionId
              ? 'ring-app-border bg-white shadow-sm ring-1'
              : 'hover:bg-white/60',
          )}
        >
          <div className="flex items-center gap-2">
            <span className="text-app-text text-sm font-medium">Черновик</span>
            <StatusBadge status="draft" />
          </div>
          <span className="text-app-muted text-xs">v{draft.versionNumber}</span>
        </button>
      )}
      {versions.map((v) => (
        <button
          key={v.versionId}
          onClick={() => onSelect(v)}
          className={cn(
            'flex flex-col gap-1 rounded-lg px-3 py-2 text-left transition-colors',
            selectedId === v.versionId
              ? 'ring-app-border bg-white shadow-sm ring-1'
              : 'hover:bg-white/60',
          )}
        >
          <div className="flex items-center gap-2">
            <span className="text-app-text text-sm font-medium">
              v{v.versionNumber}
            </span>
            <StatusBadge status={v.status} />
          </div>
          {v.publishedAt && (
            <span className="text-app-muted text-xs">
              {formatDateTime(v.publishedAt)}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}
