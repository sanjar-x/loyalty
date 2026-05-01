'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { previewPrice } from '@/features/pricing/api/formulas';
import { usePricingPage } from '@/features/pricing/model/PricingPageProvider';
import { formatCurrency } from '@/shared/lib/utils';

const COMPONENT_LABELS = {
  cogs: 'Себестоимость (COGS)',
  shipping: 'Доставка',
  commission: 'Комиссия',
  tax: 'Налог',
  margin: 'Маржа',
  final_price: 'Итоговая цена',
};

export function SandboxPanel() {
  const { contextId } = usePricingPage();
  const [productId, setProductId] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [supplierId, setSupplierId] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [elapsed, setElapsed] = useState(null);
  const debounceRef = useRef(null);

  const canPreview = productId && categoryId && contextId;

  const runPreview = useCallback(async () => {
    if (!canPreview) return;
    setLoading(true);
    setError(null);
    const start = performance.now();

    try {
      const data = await previewPrice({
        productId,
        categoryId,
        contextId,
        supplierId: supplierId || undefined,
      });
      setResult(data);
      setElapsed(Math.round(performance.now() - start));
    } catch (err) {
      setError(err?.data?.error?.message || err.message || 'Ошибка расчёта');
      setResult(null);
    } finally {
      setLoading(false);
    }
  }, [productId, categoryId, contextId, supplierId, canPreview]);

  useEffect(() => {
    if (!canPreview) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(runPreview, 500);
    return () => clearTimeout(debounceRef.current);
  }, [productId, categoryId, supplierId, contextId, canPreview, runPreview]);

  const components = result?.components || {};
  const taggedComponents = Object.entries(components)
    .filter(([key]) => key !== 'final_price')
    .map(([key, val]) => ({
      key,
      label: COMPONENT_LABELS[key] || key,
      value: val,
    }));

  return (
    <div className="border-app-border flex flex-col gap-4 rounded-xl border bg-[#fafafa] p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-app-text text-sm font-semibold">Sandbox</h3>
        {elapsed != null && (
          <span className="text-app-muted text-[11px]">{elapsed} мс</span>
        )}
      </div>

      <div className="flex flex-col gap-2">
        <SandboxField
          label="Product ID"
          value={productId}
          onChange={setProductId}
          placeholder="UUID продукта"
        />
        <SandboxField
          label="Category ID"
          value={categoryId}
          onChange={setCategoryId}
          placeholder="UUID категории"
        />
        <SandboxField
          label="Supplier ID"
          value={supplierId}
          onChange={setSupplierId}
          placeholder="UUID поставщика (опционально)"
        />
      </div>

      {!canPreview && (
        <p className="text-app-muted text-xs">
          Заполните Product ID и Category ID для расчёта
        </p>
      )}

      {loading && (
        <div className="text-app-muted flex items-center gap-2 text-xs">
          <span className="border-app-muted inline-block h-3 w-3 animate-spin rounded-full border-2 border-t-transparent" />
          Расчёт…
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600">
          {error}
        </div>
      )}

      {result && !loading && (
        <div className="flex flex-col gap-3">
          <div className="rounded-xl bg-white p-3 shadow-sm">
            <div className="flex items-baseline justify-between">
              <span className="text-app-muted text-xs font-medium">Итого</span>
              <span className="text-app-text text-2xl font-bold">
                {formatCurrency(result.finalPrice)}
              </span>
            </div>
            <div className="text-app-muted mt-1 flex items-center gap-2 text-[11px]">
              <span>v{result.formulaVersionNumber}</span>
              <span>·</span>
              <span>Формула {result.formulaVersionId?.slice(0, 8)}</span>
            </div>
          </div>

          {taggedComponents.length > 0 && (
            <div className="flex flex-col gap-1">
              <span className="text-app-muted text-[11px] font-medium">
                Декомпозиция
              </span>
              <div className="flex flex-col gap-0.5">
                {taggedComponents.map(({ key, label, value }) => {
                  const finalPrice = Number(result.finalPrice) || 1;
                  const numValue = Number(value) || 0;
                  const pct = ((numValue / finalPrice) * 100).toFixed(1);
                  return (
                    <div
                      key={key}
                      className="flex items-center justify-between rounded-lg bg-white px-3 py-1.5"
                    >
                      <span className="text-app-text text-xs">{label}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-app-text text-xs font-medium">
                          {formatCurrency(value)}
                        </span>
                        <span className="text-app-muted w-10 text-right text-[10px]">
                          {pct}%
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {result.finalPrice && components.margin && (
            <div className="rounded-lg bg-emerald-50 px-3 py-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-emerald-700">
                  Маржа
                </span>
                <span className="text-sm font-bold text-emerald-700">
                  {(() => {
                    const m = Number(components.margin);
                    const d = Number(result.finalPrice) - m;
                    return d > 0 ? ((m / d) * 100).toFixed(1) + '%' : '—';
                  })()}
                </span>
              </div>
            </div>
          )}
        </div>
      )}

      {canPreview && (
        <button
          onClick={runPreview}
          disabled={loading}
          className="bg-app-text rounded-lg px-3 py-2 text-xs font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          Пересчитать
        </button>
      )}
    </div>
  );
}

function SandboxField({ label, value, onChange, placeholder }) {
  return (
    <div className="flex flex-col gap-0.5">
      <label className="text-app-muted text-[11px] font-medium">{label}</label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="border-app-border text-app-text focus:border-app-text h-8 rounded-md border bg-white px-2 font-mono text-xs transition-colors outline-none"
      />
    </div>
  );
}
