import { formatDateTime } from '@/shared/lib/utils';

export function DraftBanner({ draft }) {
  if (!draft) return null;

  return (
    <div className="flex items-center gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-2.5">
      <span className="text-sm font-medium text-amber-700">
        Есть неопубликованный черновик (v{draft.versionNumber})
      </span>
      {draft.updatedAt && (
        <span className="text-xs text-amber-600">
          Изменён: {formatDateTime(draft.updatedAt)}
        </span>
      )}
    </div>
  );
}
