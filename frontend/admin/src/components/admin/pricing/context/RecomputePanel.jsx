'use client';

import { useState } from 'react';
import { usePricingPage } from '../PricingPageProvider';
import { recomputeContext, recomputeSku } from '@/services/pricing/recompute';
import { ErrorBanner } from '../shared/ErrorBanner';

export function RecomputePanel() {
  const { contextId } = usePricingPage();
  const [skuId, setSkuId] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  async function handleRecomputeContext() {
    if (!confirm('Запустить пересчёт всех товаров этого контекста? Это асинхронная операция.')) return;
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
      <h4 className="text-xs font-medium text-app-muted">Пересчёт цен</h4>

      {error && <ErrorBanner error={error} onDismiss={() => setError(null)} />}

      {result && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-700">
          {result.type === 'context' ? (
            <span>Пересчёт контекста запущен (фоновая задача)</span>
          ) : (
            <span>
              SKU {result.data.skuId?.slice(0, 8)}… → статус: <strong>{result.data.status}</strong>
            </span>
          )}
        </div>
      )}

      <div className="flex items-center gap-3">
        <button
          onClick={handleRecomputeContext}
          disabled={loading}
          className="rounded-lg border border-app-border bg-white px-4 py-2 text-sm font-medium text-app-text transition-colors hover:bg-[#f4f3f1] disabled:opacity-50"
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
          className="h-9 flex-1 rounded-lg border border-app-border bg-white px-3 font-mono text-xs outline-none transition-colors focus:border-app-text"
        />
        <button
          onClick={handleRecomputeSku}
          disabled={loading || !skuId.trim()}
          className="shrink-0 rounded-lg bg-app-text px-3 py-2 text-xs font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          Пересчитать SKU
        </button>
      </div>
    </div>
  );
}
