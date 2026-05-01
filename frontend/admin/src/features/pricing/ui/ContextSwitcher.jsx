'use client';

import { cn, i18n } from '@/shared/lib/utils';
import { usePricingPage } from '@/features/pricing/model/PricingPageProvider';

export function ContextSwitcher() {
  const { contexts, contextId, setContextId } = usePricingPage();

  if (contexts.length === 0) return null;

  return (
    <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
      {contexts.map((ctx) => {
        const active = ctx.contextId === contextId;
        return (
          <button
            key={ctx.contextId}
            onClick={() => setContextId(ctx.contextId)}
            className={cn(
              'shrink-0 rounded-lg px-4 py-2 text-sm font-medium transition-colors',
              active
                ? 'bg-app-text text-white'
                : 'bg-app-card text-app-text hover:bg-[#eae9e6]',
              ctx.isFrozen && !active && 'ring-1 ring-red-300',
            )}
          >
            {i18n(ctx.name, ctx.code)}
            {ctx.isFrozen && (
              <span className="ml-1.5 text-xs opacity-70">❄</span>
            )}
          </button>
        );
      })}
    </div>
  );
}
