'use client';

import {
  PRODUCT_STATUS_TRANSITIONS,
  PRODUCT_STATUS_LABELS,
} from '@/entities/product';

function buttonStyle(target) {
  if (target === 'published')
    return 'bg-green-600 text-white hover:bg-green-700';
  if (target === 'archived')
    return 'bg-amber-100 text-amber-800 border border-amber-300 hover:bg-amber-200';
  if (target === 'draft')
    return 'border border-app-border bg-white text-app-text hover:bg-app-card';
  return 'bg-app-text text-white hover:opacity-90';
}

export function StatusTransitionBar({ status, loading, onTransition }) {
  const transitions = PRODUCT_STATUS_TRANSITIONS[status];
  if (!transitions || transitions.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="bg-app-card text-app-muted rounded-full px-3 py-1 text-xs font-medium">
        {PRODUCT_STATUS_LABELS[status] ?? status}
      </span>
      <span className="text-app-border">→</span>
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
