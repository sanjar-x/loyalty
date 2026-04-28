'use client';

import { useCallback, useEffect, useState } from 'react';
import { usePricingPage } from '../PricingPageProvider';
import { getGlobalValues, setGlobalValue as setGlobalValueApi, freezeContext, unfreezeContext } from '@/services/pricing/contexts';
import { i18n } from '@/lib/utils';
import { ErrorBanner } from '../shared/ErrorBanner';
import { LoadingSkeleton } from '../shared/LoadingSkeleton';
import { DecimalField } from '../shared/DecimalField';
import { SupplierTypeMappingPanel } from './SupplierTypeMappingPanel';
import { RecomputePanel } from './RecomputePanel';

export function ContextSettingsTab() {
  const { currentContext, contextId, refetchContexts } = usePricingPage();
  const [globalValues, setGlobalValuesState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editingCode, setEditingCode] = useState(null);
  const [editValue, setEditValue] = useState('');
  const [saving, setSaving] = useState(false);
  const [freezeReason, setFreezeReason] = useState('');
  const [showFreezeInput, setShowFreezeInput] = useState(false);

  const fetchValues = useCallback(async () => {
    if (!contextId) return;
    setError(null);
    try {
      const data = await getGlobalValues(contextId);
      setGlobalValuesState(data);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [contextId]);

  useEffect(() => {
    fetchValues();
  }, [fetchValues]);

  async function handleSaveValue(variableCode) {
    if (!globalValues) return;
    setSaving(true);
    setError(null);
    try {
      await setGlobalValueApi(contextId, variableCode, {
        value: editValue,
        versionLock: globalValues.versionLock,
      });
      setEditingCode(null);
      setEditValue('');
      setLoading(true);
      await fetchValues();
      await refetchContexts();
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  }

  async function handleFreeze() {
    if (!freezeReason.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await freezeContext(contextId, { reason: freezeReason });
      setShowFreezeInput(false);
      setFreezeReason('');
      await refetchContexts();
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  }

  async function handleUnfreeze() {
    setSaving(true);
    setError(null);
    try {
      await unfreezeContext(contextId);
      await refetchContexts();
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  }

  if (!currentContext) return null;

  const ctx = currentContext;

  return (
    <div className="flex flex-col gap-6">
      {error && <ErrorBanner error={error} onDismiss={() => setError(null)} />}

      <section className="flex flex-col gap-3">
        <h3 className="text-sm font-semibold text-app-text">Параметры контекста</h3>
        <div className="grid grid-cols-2 gap-3 rounded-xl bg-[#fafafa] p-4 text-sm md:grid-cols-3">
          <InfoItem label="Код" value={ctx.code} mono />
          <InfoItem label="Округление" value={`${ctx.roundingMode}, шаг ${ctx.roundingStep}`} />
          <InfoItem label="Margin floor" value={ctx.marginFloorPct ? `${(Number(ctx.marginFloorPct) * 100).toFixed(1)}%` : '—'} />
          <InfoItem label="Timeout" value={`${ctx.evaluationTimeoutMs} мс`} />
          <InfoItem label="Simulation threshold" value={String(ctx.simulationThreshold ?? 0)} />
          <InfoItem label="Approval" value={ctx.approvalRequiredOnPublish ? 'Да' : 'Нет'} />
        </div>
      </section>

      <section className="flex flex-col gap-3">
        <h3 className="text-sm font-semibold text-app-text">Управление</h3>
        <div className="flex items-center gap-3">
          {ctx.isFrozen ? (
            <button
              onClick={handleUnfreeze}
              disabled={saving}
              className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              Разморозить
            </button>
          ) : showFreezeInput ? (
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={freezeReason}
                onChange={(e) => setFreezeReason(e.target.value)}
                placeholder="Причина заморозки..."
                className="h-9 w-64 rounded-lg border border-red-300 bg-white px-3 text-sm outline-none focus:ring-1 focus:ring-red-400"
                maxLength={1024}
              />
              <button
                onClick={handleFreeze}
                disabled={saving || !freezeReason.trim()}
                className="rounded-lg bg-red-600 px-3 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
              >
                Подтвердить
              </button>
              <button
                onClick={() => { setShowFreezeInput(false); setFreezeReason(''); }}
                className="text-sm text-app-muted hover:text-app-text"
              >
                Отмена
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowFreezeInput(true)}
              className="rounded-lg border border-red-300 bg-white px-4 py-2 text-sm font-medium text-red-600 transition-colors hover:bg-red-50"
            >
              Заморозить контекст
            </button>
          )}
        </div>
      </section>

      <section className="flex flex-col gap-3">
        <h3 className="text-sm font-semibold text-app-text">Глобальные значения переменных</h3>
        {loading ? (
          <LoadingSkeleton rows={3} columns={3} />
        ) : !globalValues || globalValues.values.length === 0 ? (
          <p className="rounded-xl bg-[#fafafa] p-4 text-sm text-app-muted">
            Нет переменных scope=global для этого контекста.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-app-border text-left text-xs font-medium text-app-muted">
                  <th className="px-3 py-2">Код переменной</th>
                  <th className="px-3 py-2">Название</th>
                  <th className="px-3 py-2">Значение</th>
                  <th className="px-3 py-2 text-right">Действие</th>
                </tr>
              </thead>
              <tbody>
                {globalValues.values.map((v) => (
                  <tr key={v.variableCode} className="border-b border-[#f4f3f1]">
                    <td className="px-3 py-2">
                      <code className="rounded bg-[#f4f3f1] px-1.5 py-0.5 text-xs font-mono">{v.variableCode}</code>
                    </td>
                    <td className="px-3 py-2 text-app-text">{i18n(v.variableName)}</td>
                    <td className="px-3 py-2">
                      {editingCode === v.variableCode ? (
                        <DecimalField
                          value={editValue}
                          onChange={setEditValue}
                          placeholder="0.00"
                          className="w-32"
                        />
                      ) : (
                        <span className="font-mono text-xs">{v.value ?? '—'}</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {editingCode === v.variableCode ? (
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => handleSaveValue(v.variableCode)}
                            disabled={saving}
                            className="rounded px-2 py-1 text-xs font-medium text-emerald-600 hover:bg-emerald-50 disabled:opacity-50"
                          >
                            Сохранить
                          </button>
                          <button
                            onClick={() => { setEditingCode(null); setEditValue(''); }}
                            className="rounded px-2 py-1 text-xs text-app-muted hover:text-app-text"
                          >
                            Отмена
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => { setEditingCode(v.variableCode); setEditValue(v.value ?? ''); }}
                          className="rounded px-2 py-1 text-xs font-medium text-app-muted hover:text-app-text"
                        >
                          Изменить
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="flex flex-col gap-3 border-t border-app-border pt-5">
        <h3 className="text-sm font-semibold text-app-text">Маппинг типов поставщиков</h3>
        <SupplierTypeMappingPanel />
      </section>

      <section className="flex flex-col gap-3 border-t border-app-border pt-5">
        <h3 className="text-sm font-semibold text-app-text">Операции</h3>
        <RecomputePanel />
      </section>
    </div>
  );
}

function InfoItem({ label, value, mono }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs text-app-muted">{label}</span>
      <span className={`text-sm text-app-text ${mono ? 'font-mono' : ''}`}>{value}</span>
    </div>
  );
}
