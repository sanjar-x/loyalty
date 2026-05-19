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

/**
 * `publishGate` (CAT-012) — when set with `blocked: true`, the
 * `published` transition button is disabled and the `reason` is rendered
 * inline next to the bar so the user understands why publish isn't
 * available yet (typically: pricing recompute pending or failed).
 */
export function StatusTransitionBar({
  status,
  loading,
  onTransition,
  publishGate,
}) {
  const transitions = PRODUCT_STATUS_TRANSITIONS[status];
  if (!transitions || transitions.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="bg-app-card text-app-muted rounded-full px-3 py-1 text-xs font-medium">
        {PRODUCT_STATUS_LABELS[status] ?? status}
      </span>
      <span className="text-app-border">→</span>
      {transitions.map(({ target, label }) => {
        const gated = target === 'published' && publishGate?.blocked;
        const tooltip = gated ? publishGate.reason : undefined;
        return (
          <button
            key={target}
            type="button"
            disabled={loading || gated}
            onClick={() => onTransition(target)}
            title={tooltip}
            aria-disabled={loading || gated || undefined}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${buttonStyle(target)}`}
          >
            {label}
          </button>
        );
      })}
      {publishGate?.blocked && publishGate.reason && (
        <span
          role="status"
          className="text-app-muted text-xs"
          aria-live="polite"
        >
          {publishGate.reason}
        </span>
      )}
    </div>
  );
}
