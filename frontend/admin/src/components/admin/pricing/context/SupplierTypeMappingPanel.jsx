'use client';

import { useCallback, useEffect, useState } from 'react';
import { listMappings, upsertMapping, deleteMapping } from '@/services/pricing/supplierTypeMapping';
import { usePricingPage } from '../PricingPageProvider';
import { ErrorBanner } from '../shared/ErrorBanner';
import { LoadingSkeleton } from '../shared/LoadingSkeleton';
import { i18n } from '@/lib/utils';

export function SupplierTypeMappingPanel() {
  const { contexts } = usePricingPage();
  const [mappings, setMappings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editingType, setEditingType] = useState(null);
  const [editContextId, setEditContextId] = useState('');
  const [saving, setSaving] = useState(false);

  const fetchMappings = useCallback(async () => {
    setError(null);
    try {
      const data = await listMappings();
      setMappings(data.items ?? []);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMappings();
  }, [fetchMappings]);

  async function handleSave(supplierType) {
    if (!editContextId) return;
    setSaving(true);
    setError(null);
    try {
      await upsertMapping(supplierType, { contextId: editContextId });
      setEditingType(null);
      setEditContextId('');
      await fetchMappings();
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(supplierType) {
    if (!confirm(`Удалить маппинг для «${supplierType}»?`)) return;
    setSaving(true);
    setError(null);
    try {
      await deleteMapping(supplierType);
      await fetchMappings();
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <LoadingSkeleton rows={2} columns={3} />;

  return (
    <div className="flex flex-col gap-3">
      <h4 className="text-xs font-medium text-app-muted">
        Маппинг SupplierType → Context
      </h4>

      {error && <ErrorBanner error={error} onDismiss={() => setError(null)} />}

      {mappings.length === 0 ? (
        <p className="rounded-lg bg-[#fafafa] p-3 text-sm text-app-muted">
          Маппинги не настроены.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-app-border text-left text-xs font-medium text-app-muted">
                <th className="px-3 py-2">Тип поставщика</th>
                <th className="px-3 py-2">Контекст</th>
                <th className="px-3 py-2 text-right">Действия</th>
              </tr>
            </thead>
            <tbody>
              {mappings.map((m) => {
                const ctx = contexts.find((c) => c.contextId === m.contextId);
                const isEditing = editingType === m.supplierType;

                return (
                  <tr key={m.supplierType} className="border-b border-[#f4f3f1]">
                    <td className="px-3 py-2">
                      <code className="rounded bg-[#f4f3f1] px-1.5 py-0.5 text-xs font-mono">
                        {m.supplierType}
                      </code>
                    </td>
                    <td className="px-3 py-2">
                      {isEditing ? (
                        <select
                          value={editContextId}
                          onChange={(e) => setEditContextId(e.target.value)}
                          className="h-8 rounded border border-app-border bg-white px-2 text-sm outline-none focus:border-app-text"
                        >
                          <option value="">Выберите контекст</option>
                          {contexts.map((c) => (
                            <option key={c.contextId} value={c.contextId}>
                              {i18n(c.name, c.code)}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <span className="text-app-text">
                          {ctx ? i18n(ctx.name, ctx.code) : m.contextId.slice(0, 8) + '…'}
                        </span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {isEditing ? (
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => handleSave(m.supplierType)}
                            disabled={saving || !editContextId}
                            className="rounded px-2 py-1 text-xs font-medium text-emerald-600 hover:bg-emerald-50 disabled:opacity-50"
                          >
                            Сохранить
                          </button>
                          <button
                            onClick={() => { setEditingType(null); setEditContextId(''); }}
                            className="rounded px-2 py-1 text-xs text-app-muted hover:text-app-text"
                          >
                            Отмена
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => {
                              setEditingType(m.supplierType);
                              setEditContextId(m.contextId);
                            }}
                            className="rounded px-2 py-1 text-xs font-medium text-app-muted hover:text-app-text"
                          >
                            Изменить
                          </button>
                          <button
                            onClick={() => handleDelete(m.supplierType)}
                            disabled={saving}
                            className="rounded px-2 py-1 text-xs text-red-400 hover:text-red-600 disabled:opacity-50"
                          >
                            Удалить
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
