'use client';

import { useCallback, useEffect, useState } from 'react';
import { usePricingPage } from '../PricingPageProvider';
import { getCategorySettings, upsertCategorySettings, deleteCategorySettings } from '@/services/pricing/categorySettings';
import { listVariables } from '@/services/pricing/variables';
import { i18n } from '@/lib/utils';
import { ErrorBanner } from '../shared/ErrorBanner';
import { EmptyState } from '../shared/EmptyState';
import { LoadingSkeleton } from '../shared/LoadingSkeleton';
import { CategoryPricingPanel } from './CategoryPricingPanel';

export function CategoriesTab() {
  const { contextId } = usePricingPage();
  const [tree, setTree] = useState([]);
  const [variables, setVariables] = useState([]);
  const [selectedCategoryId, setSelectedCategoryId] = useState(null);
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [settingsLoading, setSettingsLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchTree = useCallback(async () => {
    try {
      const res = await fetch('/api/categories/tree', { credentials: 'include' });
      if (res.ok) {
        setTree(await res.json());
      }
    } catch {}
  }, []);

  const fetchVariables = useCallback(async () => {
    try {
      const data = await listVariables();
      setVariables(data.items ?? []);
    } catch {}
  }, []);

  useEffect(() => {
    Promise.all([fetchTree(), fetchVariables()]).finally(() => setLoading(false));
  }, [fetchTree, fetchVariables]);

  const fetchSettings = useCallback(async (catId) => {
    if (!catId || !contextId) return;
    setSettingsLoading(true);
    setError(null);
    try {
      const data = await getCategorySettings(catId, contextId);
      setSettings(data);
    } catch (err) {
      if (err.status === 404) {
        setSettings(null);
      } else {
        setError(err);
      }
    } finally {
      setSettingsLoading(false);
    }
  }, [contextId]);

  useEffect(() => {
    if (selectedCategoryId) {
      fetchSettings(selectedCategoryId);
    } else {
      setSettings(null);
    }
  }, [selectedCategoryId, fetchSettings]);

  async function handleSave(payload) {
    setError(null);
    try {
      await upsertCategorySettings(selectedCategoryId, contextId, payload);
      await fetchSettings(selectedCategoryId);
    } catch (err) {
      setError(err);
    }
  }

  async function handleDelete() {
    if (!confirm('Удалить настройки ценообразования для этой категории?')) return;
    setError(null);
    try {
      await deleteCategorySettings(selectedCategoryId, contextId);
      setSettings(null);
    } catch (err) {
      setError(err);
    }
  }

  if (loading) return <LoadingSkeleton rows={5} columns={3} />;

  if (tree.length === 0) {
    return (
      <EmptyState
        title="Нет категорий"
        description="Сначала создайте категории в разделе Настройки → Категории."
      />
    );
  }

  const categoryVars = variables.filter((v) => v.scope === 'category');
  const rangeVars = variables.filter((v) => v.scope === 'range');

  return (
    <div className="flex flex-col gap-4">
      {error && <ErrorBanner error={error} onDismiss={() => setError(null)} />}

      <div className="grid grid-cols-[260px_minmax(0,1fr)] gap-4">
        <div className="flex flex-col gap-1 overflow-y-auto rounded-xl border border-app-border bg-[#fafafa] p-2" style={{ maxHeight: '600px' }}>
          <CategoryTreeItems
            nodes={tree}
            level={0}
            selectedId={selectedCategoryId}
            onSelect={setSelectedCategoryId}
          />
        </div>

        <div>
          {!selectedCategoryId ? (
            <div className="flex items-center justify-center rounded-xl border border-dashed border-app-border p-12 text-sm text-app-muted">
              Выберите категорию слева
            </div>
          ) : settingsLoading ? (
            <LoadingSkeleton rows={3} columns={2} />
          ) : (
            <CategoryPricingPanel
              settings={settings}
              categoryVariables={categoryVars}
              rangeVariables={rangeVars}
              onSave={handleSave}
              onDelete={handleDelete}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function CategoryTreeItems({ nodes, level, selectedId, onSelect }) {
  return nodes.map((node) => (
    <div key={node.id}>
      <button
        onClick={() => onSelect(node.id)}
        className={`flex w-full items-center rounded-lg px-3 py-1.5 text-left text-sm transition-colors ${
          selectedId === node.id
            ? 'bg-white font-medium text-app-text shadow-sm ring-1 ring-app-border'
            : 'text-app-text hover:bg-white/60'
        }`}
        style={{ paddingLeft: level * 20 + 12 }}
      >
        {node.children?.length > 0 && (
          <span className="mr-1.5 text-xs text-app-muted">▸</span>
        )}
        {i18n(node.nameI18N ?? node.name, node.slug)}
      </button>
      {node.children?.length > 0 && (
        <CategoryTreeItems
          nodes={node.children}
          level={level + 1}
          selectedId={selectedId}
          onSelect={onSelect}
        />
      )}
    </div>
  ));
}
