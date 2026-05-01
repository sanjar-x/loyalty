'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  listMappings,
  upsertMapping,
  deleteMapping,
} from '@/features/pricing/api/supplierTypeMapping';
import { usePricingPage } from '@/features/pricing/model/PricingPageProvider';
import { ErrorBanner } from '../shared/ErrorBanner';
import { LoadingSkeleton } from '../shared/LoadingSkeleton';
import { i18n } from '@/shared/lib/utils';

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
      <h4 className="text-app-muted text-xs font-medium">
        Маппинг SupplierType → Context
      </h4>

      {error && <ErrorBanner error={error} onDismiss={() => setError(null)} />}

      {mappings.length === 0 ? (
        <p className="text-app-muted rounded-lg bg-[#fafafa] p-3 text-sm">
          Маппинги не настроены.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-app-border text-app-muted border-b text-left text-xs font-medium">
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
                  <tr key={m.supplierType} className="border-app-card border-b">
                    <td className="px-3 py-2">
                      <code className="bg-app-card rounded px-1.5 py-0.5 font-mono text-xs">
                        {m.supplierType}
                      </code>
                    </td>
                    <td className="px-3 py-2">
                      {isEditing ? (
                        <select
                          value={editContextId}
                          onChange={(e) => setEditContextId(e.target.value)}
                          className="border-app-border focus:border-app-text h-8 rounded border bg-white px-2 text-sm outline-none"
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
                          {ctx
                            ? i18n(ctx.name, ctx.code)
                            : m.contextId.slice(0, 8) + '…'}
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
                            onClick={() => {
                              setEditingType(null);
                              setEditContextId('');
                            }}
                            className="text-app-muted hover:text-app-text rounded px-2 py-1 text-xs"
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
                            className="text-app-muted hover:text-app-text rounded px-2 py-1 text-xs font-medium"
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
