'use client';

import { useCallback, useEffect, useState } from 'react';
import { usePricingPage } from '../PricingPageProvider';
import {
  listVersions,
  getDraft,
  saveDraft,
  deleteDraft,
  publishDraft,
  rollbackVersion,
} from '@/services/pricing/formulas';
import { listVariables } from '@/services/pricing/variables';
import { VersionsList } from './VersionsList';
import { VersionViewer } from './VersionViewer';
import { FormulaEditor } from './FormulaEditor';
import { SandboxPanel } from './SandboxPanel';
import { DraftBanner } from './DraftBanner';
import { EmptyState } from '../shared/EmptyState';
import { ErrorBanner } from '../shared/ErrorBanner';
import { LoadingSkeleton } from '../shared/LoadingSkeleton';
import { astToBindings, bindingsToAst } from './astUtils';

const DEFAULT_BINDINGS = [
  { name: 'final_price', component_tag: 'final_price', expr: { const: '0' } },
];

export function FormulaTab() {
  const { contextId } = usePricingPage();

  const [versions, setVersions] = useState([]);
  const [draft, setDraft] = useState(null);
  const [variables, setVariables] = useState([]);
  const [selectedVersion, setSelectedVersion] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  const [mode, setMode] = useState('view');
  const [editorBindings, setEditorBindings] = useState([]);
  const [draftVersionLock, setDraftVersionLock] = useState(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  const fetchData = useCallback(async () => {
    if (!contextId) return;
    setLoading(true);
    setError(null);
    try {
      const [versionsData, draftData, varsData] = await Promise.all([
        listVersions(contextId),
        getDraft(contextId).catch(() => null),
        listVariables(),
      ]);
      const items = versionsData.items ?? [];
      setVersions(items);
      setDraft(draftData);
      setVariables(varsData.items ?? []);

      const published = items.find((v) => v.status === 'published');
      setSelectedVersion(published ?? items[0] ?? null);

      if (draftData) {
        setEditorBindings(astToBindings(draftData.ast));
        setDraftVersionLock(draftData.versionLock);
      }
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [contextId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  function handleStartEditing() {
    if (draft) {
      setEditorBindings(astToBindings(draft.ast));
      setDraftVersionLock(draft.versionLock);
    } else {
      const published = versions.find((v) => v.status === 'published');
      if (published) {
        setEditorBindings(astToBindings(published.ast));
      } else {
        setEditorBindings([...DEFAULT_BINDINGS]);
      }
      setDraftVersionLock(null);
    }
    setMode('edit');
    setHasUnsavedChanges(false);
  }

  function handleBindingsChange(newBindings) {
    setEditorBindings(newBindings);
    setHasUnsavedChanges(true);
  }

  async function handleSaveDraft() {
    setSaving(true);
    setError(null);
    try {
      const ast = bindingsToAst(editorBindings);
      const result = await saveDraft(contextId, {
        ast,
        expectedVersionLock: draftVersionLock,
      });
      setDraftVersionLock(result.versionLock);
      setHasUnsavedChanges(false);
      await fetchData();
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  }

  async function handleDiscardDraft() {
    if (!confirm('Удалить черновик? Все несохранённые изменения будут потеряны.')) return;
    setSaving(true);
    setError(null);
    try {
      await deleteDraft(contextId);
      setMode('view');
      setHasUnsavedChanges(false);
      await fetchData();
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  }

  async function handlePublish() {
    if (!confirm('Опубликовать текущий черновик? Это запустит массовый пересчёт цен.')) return;
    setSaving(true);
    setError(null);
    try {
      await publishDraft(contextId);
      setMode('view');
      setHasUnsavedChanges(false);
      await fetchData();
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  }

  async function handleRollback(versionId) {
    if (!confirm('Откатить к этой версии? Текущая опубликованная версия будет архивирована.')) return;
    setSaving(true);
    setError(null);
    try {
      await rollbackVersion(contextId, versionId);
      await fetchData();
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <LoadingSkeleton rows={4} columns={2} />;
  if (error && versions.length === 0 && !draft) return <ErrorBanner error={error} />;

  if (versions.length === 0 && !draft && mode !== 'edit') {
    return (
      <EmptyState
        title="Нет версий формулы"
        description="Создайте первый черновик формулы для этого контекста."
        action={{ label: 'Создать черновик', onClick: handleStartEditing }}
      />
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {error && <ErrorBanner error={error} onDismiss={() => setError(null)} />}

      {mode === 'view' && draft && <DraftBanner draft={draft} />}

      <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
        <div className="flex flex-col gap-4">
          {mode === 'edit' ? (
            <>
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-app-text">
                  Редактор формулы {draft ? `(черновик v${draft.versionNumber})` : '(новый черновик)'}
                </h3>
                <div className="flex items-center gap-2">
                  {hasUnsavedChanges && (
                    <span className="text-xs text-amber-600">Есть несохранённые изменения</span>
                  )}
                </div>
              </div>

              <div className="rounded-xl border border-app-border bg-white p-3">
                <FormulaEditor
                  bindings={editorBindings}
                  onChange={handleBindingsChange}
                  variables={variables}
                />
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleSaveDraft}
                  disabled={saving}
                  className="rounded-lg bg-app-text px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                >
                  {saving ? 'Сохранение…' : 'Сохранить черновик'}
                </button>
                {draft && (
                  <button
                    onClick={handlePublish}
                    disabled={saving || hasUnsavedChanges}
                    className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                    title={hasUnsavedChanges ? 'Сначала сохраните черновик' : ''}
                  >
                    Опубликовать
                  </button>
                )}
                {draft && (
                  <button
                    onClick={handleDiscardDraft}
                    disabled={saving}
                    className="rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-600 transition-colors hover:bg-red-50 disabled:opacity-50"
                  >
                    Удалить черновик
                  </button>
                )}
                <button
                  onClick={() => {
                    setMode('view');
                    setHasUnsavedChanges(false);
                  }}
                  className="rounded-lg px-4 py-2 text-sm font-medium text-app-muted transition-colors hover:text-app-text"
                >
                  Закрыть редактор
                </button>
              </div>
            </>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-app-text">Версии формулы</h3>
                <button
                  onClick={handleStartEditing}
                  className="rounded-lg bg-app-text px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90"
                >
                  {draft ? 'Редактировать черновик' : 'Создать черновик'}
                </button>
              </div>

              <div className="grid grid-cols-[220px_minmax(0,1fr)] gap-4">
                <VersionsList
                  versions={versions}
                  draft={draft}
                  selectedId={selectedVersion?.versionId ?? draft?.versionId}
                  onSelect={(v) => setSelectedVersion(v)}
                  onSelectDraft={() => setSelectedVersion(draft)}
                />
                <div className="flex flex-col gap-3">
                  <VersionViewer version={selectedVersion ?? draft} />
                  {selectedVersion?.status === 'archived' && (
                    <button
                      onClick={() => handleRollback(selectedVersion.versionId)}
                      disabled={saving}
                      className="self-start rounded-lg border border-amber-300 px-3 py-1.5 text-xs font-medium text-amber-700 transition-colors hover:bg-amber-50 disabled:opacity-50"
                    >
                      Откатить к этой версии
                    </button>
                  )}
                </div>
              </div>
            </>
          )}
        </div>

        <SandboxPanel />
      </div>
    </div>
  );
}
