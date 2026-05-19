'use client';

import { cn } from '@/shared/lib/utils';

export function FxStaleBadge({ globalValues, variables }) {
  if (!globalValues?.values || !variables) return null;

  const fxVars = variables.filter((v) => v.isFxRate);
  if (fxVars.length === 0) return null;

  const missingFx = [];
  for (const fxVar of fxVars) {
    const gv = globalValues.values.find((v) => v.variableCode === fxVar.code);
    if (!gv || gv.value == null) {
      missingFx.push(fxVar.code);
    }
  }

  if (missingFx.length === 0) return null;

  return (
    <div
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium',
        'bg-red-100 text-red-700',
      )}
      title={`Не задано: ${missingFx.join(', ')}`}
    >
      <svg className="h-3 w-3" viewBox="0 0 12 12" fill="currentColor">
        <path d="M6 1a5 5 0 100 10A5 5 0 006 1zm-.5 2.5a.5.5 0 011 0v2.793l1.354 1.353a.5.5 0 01-.708.708l-1.5-1.5A.5.5 0 015.5 6.5v-3z" />
      </svg>
      FX не задан ({missingFx.length})
    </div>
  );
}
