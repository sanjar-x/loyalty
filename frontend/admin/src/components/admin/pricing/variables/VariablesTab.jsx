'use client';

import { useCallback, useEffect, useState } from 'react';
import { listVariables, deleteVariable } from '@/services/pricing/variables';
import { VariablesTable } from './VariablesTable';
import { VariableModal } from './VariableModal';
import { EmptyState } from '../shared/EmptyState';
import { ErrorBanner } from '../shared/ErrorBanner';
import { LoadingSkeleton } from '../shared/LoadingSkeleton';
import { cn } from '@/lib/utils';

const SCOPE_FILTERS = [
  { value: null, label: 'Все' },
  { value: 'global', label: 'Global' },
  { value: 'supplier', label: 'Supplier' },
  { value: 'category', label: 'Category' },
  { value: 'range', label: 'Range' },
  { value: 'product_input', label: 'Product input' },
  { value: 'sku_input', label: 'SKU input' },
];

export function VariablesTab() {
  const [variables, setVariables] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [scopeFilter, setScopeFilter] = useState(null);
  const [modal, setModal] = useState(null);

  const fetchVariables = useCallback(async () => {
    setError(null);
    try {
      const data = await listVariables(scopeFilter ? { scope: scopeFilter } : {});
      setVariables(data.items ?? []);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [scopeFilter]);

  useEffect(() => {
    setLoading(true);
    fetchVariables();
  }, [fetchVariables]);

  async function handleDelete(variable) {
    if (!confirm(`Удалить переменную «${variable.code}»?`)) return;
    try {
      await deleteVariable(variable.variableId);
      fetchVariables();
    } catch (err) {
      setError(err);
    }
  }

  function handleModalSuccess() {
    setModal(null);
    setLoading(true);
    fetchVariables();
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-1.5 overflow-x-auto">
          {SCOPE_FILTERS.map((f) => (
            <button
              key={f.value ?? 'all'}
              onClick={() => setScopeFilter(f.value)}
              className={cn(
                'shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors',
                scopeFilter === f.value
                  ? 'bg-app-text text-white'
                  : 'bg-[#f4f3f1] text-app-text hover:bg-[#eae9e6]',
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
        <button
          onClick={() => setModal({ mode: 'create' })}
          className="shrink-0 rounded-lg bg-app-text px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90"
        >
          + Добавить
        </button>
      </div>

      {error && <ErrorBanner error={error} onDismiss={() => setError(null)} />}

      {loading ? (
        <LoadingSkeleton rows={5} columns={6} />
      ) : variables.length === 0 ? (
        <EmptyState
          title="Нет переменных"
          description={scopeFilter ? 'Нет переменных с выбранным scope.' : 'Добавьте первую переменную для формулы ценообразования.'}
          action={!scopeFilter ? { label: '+ Добавить переменную', onClick: () => setModal({ mode: 'create' }) } : undefined}
        />
      ) : (
        <VariablesTable
          variables={variables}
          onEdit={(v) => setModal({ mode: 'edit', variable: v })}
          onDelete={handleDelete}
        />
      )}

      {modal && (
        <VariableModal
          mode={modal.mode}
          variable={modal.variable}
          onClose={() => setModal(null)}
          onSuccess={handleModalSuccess}
        />
      )}
    </div>
  );
}
