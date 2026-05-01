'use client';

import { useState } from 'react';
import { usePricingPage } from '@/features/pricing/model/PricingPageProvider';
import {
  recomputeContext,
  recomputeSku,
} from '@/features/pricing/api/recompute';
import { ErrorBanner } from '../shared/ErrorBanner';

export function RecomputePanel() {
  const { contextId } = usePricingPage();
  const [skuId, setSkuId] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  async function handleRecomputeContext() {
    if (
      !confirm(
        'Запустить пересчёт всех товаров этого контекста? Это асинхронная операция.',
      )
    )
      return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await recomputeContext(contextId);
      setResult({ type: 'context', data });
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }

  async function handleRecomputeSku() {
    if (!skuId.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await recomputeSku(skuId.trim());
      setResult({ type: 'sku', data });
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <h4 className="text-app-muted text-xs font-medium">Пересчёт цен</h4>

      {error && <ErrorBanner error={error} onDismiss={() => setError(null)} />}

      {result && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-700">
          {result.type === 'context' ? (
            <span>Пересчёт контекста запущен (фоновая задача)</span>
          ) : (
            <span>
              SKU {result.data.skuId?.slice(0, 8)}… → статус:{' '}
              <strong>{result.data.status}</strong>
            </span>
          )}
        </div>
      )}

      <div className="flex items-center gap-3">
        <button
          onClick={handleRecomputeContext}
          disabled={loading}
          className="border-app-border text-app-text hover:bg-app-card rounded-lg border bg-white px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50"
        >
          {loading ? 'Запуск…' : 'Пересчитать весь контекст'}
        </button>
      </div>

      <div className="flex items-center gap-2">
        <input
          type="text"
          value={skuId}
          onChange={(e) => setSkuId(e.target.value)}
          placeholder="UUID конкретного SKU"
          className="border-app-border focus:border-app-text h-9 flex-1 rounded-lg border bg-white px-3 font-mono text-xs transition-colors outline-none"
        />
        <button
          onClick={handleRecomputeSku}
          disabled={loading || !skuId.trim()}
          className="bg-app-text shrink-0 rounded-lg px-3 py-2 text-xs font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          Пересчитать SKU
        </button>
      </div>
    </div>
  );
}
