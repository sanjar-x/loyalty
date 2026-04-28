'use client';

import { useCallback, useEffect, useState } from 'react';
import { i18n } from '@/lib/utils';
import { StatusBadge } from './shared/StatusBadge';
import { FxStaleBadge } from './shared/FxStaleBadge';
import { usePricingPage } from './PricingPageProvider';
import { getGlobalValues } from '@/services/pricing/contexts';
import { listVariables } from '@/services/pricing/variables';

function contextStatus(ctx) {
  if (!ctx) return 'deactivated';
  if (ctx.isFrozen) return 'frozen';
  if (!ctx.isActive) return 'deactivated';
  return 'active';
}

export function ContextHeader() {
  const { currentContext, contextId } = usePricingPage();
  const [globalValues, setGlobalValues] = useState(null);
  const [fxVariables, setFxVariables] = useState([]);

  const fetchFxData = useCallback(async () => {
    if (!contextId) return;
    try {
      const [gv, vars] = await Promise.all([
        getGlobalValues(contextId),
        listVariables({ isFxRate: true }),
      ]);
      setGlobalValues(gv);
      setFxVariables(vars.items ?? []);
    } catch {}
  }, [contextId]);

  useEffect(() => {
    fetchFxData();
  }, [fetchFxData]);

  if (!currentContext) return null;

  const ctx = currentContext;
  const status = contextStatus(ctx);

  return (
    <div className="flex items-center justify-between gap-4">
      <div className="flex items-center gap-3">
        <h2 className="text-xl font-semibold text-app-text">
          {i18n(ctx.name, ctx.code)}
        </h2>
        <StatusBadge status={status} />
        <FxStaleBadge globalValues={globalValues} variables={fxVariables} />
        {ctx.isFrozen && ctx.freezeReason && (
          <span className="text-xs text-app-muted" title={ctx.freezeReason}>
            — {ctx.freezeReason.length > 60
              ? ctx.freezeReason.slice(0, 60) + '…'
              : ctx.freezeReason}
          </span>
        )}
      </div>
      <div className="flex items-center gap-2 text-xs text-app-muted">
        <span>Код: <code className="font-mono">{ctx.code}</code></span>
        {ctx.marginFloorPct != null && (
          <span>· Margin floor: {(Number(ctx.marginFloorPct) * 100).toFixed(1)}%</span>
        )}
        {ctx.activeFormulaVersionId && (
          <span>· Формула: v{ctx.activeFormulaVersionId.slice(0, 8)}</span>
        )}
      </div>
    </div>
  );
}
