'use client';

import { useEffect, useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { categoryKeys, useCategoryTree } from '@/entities/category';

import { apiClient } from '@/shared/api/clientFetch';
import { Modal } from '@/shared/ui/Modal';
import { cn, i18n } from '@/shared/lib/utils';

const ASSIGN_TRANSLATIONS = {
  ATTRIBUTE_TEMPLATE_NOT_FOUND: 'Шаблон не найден',
  CATEGORY_NOT_FOUND: 'Категория не найдена',
};

function patchCategoryTemplate(categoryId, templateId) {
  return apiClient.patch(
    `/api/categories/${categoryId}`,
    { templateId },
    { translationsByCode: ASSIGN_TRANSLATIONS },
  );
}

function flattenTree(nodes, depth = 0) {
  const out = [];
  for (const node of nodes ?? []) {
    out.push({ ...node, depth });
    if (node.children?.length) {
      out.push(...flattenTree(node.children, depth + 1));
    }
  }
  return out;
}

/**
 * Many-to-many assign of a template to one or more categories.
 *
 * Backend exposes a per-category PATCH (`/categories/{id}` with
 * `{templateId}`), so the modal fans out one PATCH per touched
 * category and aggregates the success/failure counts. The
 * pre-existing `entities/category` slice already exposes the tree
 * + cache key — we plug in here without touching that slice.
 */
export function AssignToCategoryModal({ open, template, onClose }) {
  const qc = useQueryClient();
  const treeQuery = useCategoryTree();
  const [selected, setSelected] = useState(() => new Set());
  const [error, setError] = useState(null);
  const [report, setReport] = useState(null);

  const flat = useMemo(
    () =>
      flattenTree(treeQuery.data ?? []).filter(
        (node) => !node.children?.length,
      ),
    [treeQuery.data],
  );

  // Pre-select categories already pointing at this template (best-effort —
  // backend response includes templateId per category).
  useEffect(() => {
    if (!open || !template) return;
    setSelected(
      new Set(
        flat
          .filter((node) => node.templateId === template.id)
          .map((node) => node.id),
      ),
    );
    setError(null);
    setReport(null);
  }, [open, template, flat]);

  const mutation = useMutation({
    mutationFn: async () => {
      const initial = new Set(
        flat
          .filter((node) => node.templateId === template.id)
          .map((node) => node.id),
      );
      const toAssign = [...selected].filter((id) => !initial.has(id));
      const toUnassign = [...initial].filter((id) => !selected.has(id));

      const results = await Promise.allSettled([
        ...toAssign.map((id) => patchCategoryTemplate(id, template.id)),
        ...toUnassign.map((id) => patchCategoryTemplate(id, null)),
      ]);
      return {
        succeeded: results.filter((r) => r.status === 'fulfilled').length,
        failed: results.filter((r) => r.status === 'rejected').length,
        attempted: results.length,
      };
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: categoryKeys.tree() });
    },
  });

  function toggle(categoryId) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(categoryId)) next.delete(categoryId);
      else next.add(categoryId);
      return next;
    });
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (mutation.isPending) return;
    setError(null);
    try {
      const result = await mutation.mutateAsync();
      setReport(result);
      if (result.failed === 0) onClose?.();
    } catch (err) {
      setError(err?.message ?? 'Не удалось обновить категории');
    }
  }

  if (!template) return null;

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="lg"
      title="Назначить шаблон категориям"
    >
      <form onSubmit={handleSubmit} className="mt-4 space-y-3">
        <p className="text-app-muted text-sm">
          Шаблон «{i18n(template.nameI18N, template.code)}» применяется к
          выбранным leaf-категориям. CTE backend пропагирует binding на их детей
          автоматически.
        </p>

        {treeQuery.isPending && !treeQuery.data ? (
          <p className="text-app-muted text-sm">Загружаем категории…</p>
        ) : flat.length === 0 ? (
          <p className="text-app-muted text-sm">Категории ещё не созданы.</p>
        ) : (
          // Audit 9.3 — aria-busy reflects the fan-out PATCH state so AT
          // marks the list as «работает» while up to N category mutations
          // are in-flight; pre-fix the list still looked interactive even
          // though every checkbox was disabled by the form-level button.
          <ul
            className="border-app-border divide-app-border max-h-80 divide-y overflow-auto rounded-xl border"
            aria-busy={mutation.isPending || undefined}
          >
            {flat.map((node) => {
              const checked = selected.has(node.id);
              const isOtherTemplate =
                node.templateId && node.templateId !== template.id && !checked;
              return (
                <li
                  key={node.id}
                  className={cn(
                    'flex items-center gap-2 px-3 py-2 text-sm',
                    isOtherTemplate && 'bg-app-card/40',
                  )}
                  style={{ paddingLeft: `${12 + node.depth * 16}px` }}
                >
                  <input
                    type="checkbox"
                    id={`assign-${node.id}`}
                    checked={checked}
                    onChange={() => toggle(node.id)}
                  />
                  <label htmlFor={`assign-${node.id}`} className="flex-1">
                    <span className="text-app-text-dark font-medium">
                      {i18n(node.nameI18N, node.slug)}
                    </span>
                    {isOtherTemplate && (
                      <span className="text-app-muted ml-2 text-xs">
                        — сейчас другой шаблон
                      </span>
                    )}
                  </label>
                </li>
              );
            })}
          </ul>
        )}

        {report && (
          <div
            role="status"
            className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-700"
          >
            Обновлено {report.succeeded} из {report.attempted}
            {report.failed > 0 && ` · с ошибкой: ${report.failed}`}
          </div>
        )}

        {error && (
          <div
            role="alert"
            className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700"
          >
            {error}
          </div>
        )}

        <div className="flex items-center justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={mutation.isPending}
            className="text-app-muted hover:text-app-text-dark px-3 py-2 text-sm font-medium"
          >
            Отмена
          </button>
          <button
            type="submit"
            disabled={mutation.isPending}
            className="bg-app-text rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {mutation.isPending ? 'Применяем…' : 'Применить'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
