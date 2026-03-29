'use client';

import { PRODUCT_STATUS_TRANSITIONS, PRODUCT_STATUS_LABELS } from '@/lib/constants';

function buttonStyle(target) {
  if (target === 'published') return 'bg-green-600 text-white hover:bg-green-700';
  if (target === 'archived') return 'bg-amber-100 text-amber-800 border border-amber-300 hover:bg-amber-200';
  if (target === 'draft') return 'border border-[#dfdfe2] bg-white text-[#22252b] hover:bg-[#f4f3f1]';
  return 'bg-[#22252b] text-white hover:opacity-90';
}

export function StatusTransitionBar({ status, loading, onTransition }) {
  const transitions = PRODUCT_STATUS_TRANSITIONS[status];
  if (!transitions || transitions.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="rounded-full bg-[#f4f3f1] px-3 py-1 text-xs font-medium text-[#878b93]">
        {PRODUCT_STATUS_LABELS[status] ?? status}
      </span>
      <span className="text-[#dfdfe2]">→</span>
      {transitions.map(({ target, label }) => (
        <button
          key={target}
          type="button"
          disabled={loading}
          onClick={() => onTransition(target)}
          className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-50 ${buttonStyle(target)}`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
