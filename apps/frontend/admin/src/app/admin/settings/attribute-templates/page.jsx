'use client';

import { useState } from 'react';

import {
  AttributeTemplateRow,
  useAttributeTemplates,
  useDeleteAttributeTemplate,
} from '@/entities/attribute-template';
import {
  CloneTemplateModal,
  TemplateFormModal,
} from '@/features/attribute-template-form';

import { i18n } from '@/shared/lib/utils';

export default function AttributeTemplatesAdminPage() {
  const [createOpen, setCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState(null);
  const [cloneTarget, setCloneTarget] = useState(null);

  const { data, isPending, error } = useAttributeTemplates({ limit: 200 });
  const deleteMutation = useDeleteAttributeTemplate();
  const items = data?.items ?? [];

  function handleDelete(template) {
    if (
      !confirm(
        `Удалить шаблон «${i18n(template.nameI18N, template.code)}»? Если шаблон применён к категории, backend вернёт 422.`,
      )
    ) {
      return;
    }
    deleteMutation.mutate(template.id);
  }

  return (
    <div>
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h2 className="text-app-text text-xl font-semibold">
            Шаблоны атрибутов
          </h2>
          <p className="text-app-muted text-sm">
            Группируйте атрибуты по типам товаров и применяйте к категориям.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setCreateOpen(true)}
          className="bg-app-text rounded-lg px-4 py-2 text-sm font-medium text-white"
        >
          + Создать шаблон
        </button>
      </div>

      {error ? (
        <div className="rounded-xl bg-red-50 px-4 py-6 text-center text-sm text-red-700">
          {error.message ?? 'Не удалось загрузить шаблоны'}
        </div>
      ) : isPending ? (
        <div className="border-app-border rounded-xl border p-6">
          <div className="bg-app-card h-6 w-1/3 animate-pulse rounded" />
          <div className="mt-4 space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="bg-app-card h-12 w-full animate-pulse rounded"
              />
            ))}
          </div>
        </div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-12 text-center">
          <p className="text-app-muted text-sm">Шаблонов ещё нет</p>
          <button
            type="button"
            onClick={() => setCreateOpen(true)}
            className="text-app-text text-sm font-medium underline hover:no-underline"
          >
            Создать первый
          </button>
        </div>
      ) : (
        <div className="border-app-border overflow-hidden rounded-xl border">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-app-border bg-app-card border-b">
                <th className="text-app-muted px-4 py-3 font-medium">Шаблон</th>
                <th className="text-app-muted px-4 py-3 font-medium">
                  Порядок
                </th>
                <th className="text-app-muted px-4 py-3 text-right font-medium">
                  Действия
                </th>
              </tr>
            </thead>
            <tbody>
              {items.map((template) => (
                <AttributeTemplateRow
                  key={template.id}
                  template={template}
                  onEdit={setEditTarget}
                  onDelete={handleDelete}
                  onClone={setCloneTarget}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      <TemplateFormModal
        open={createOpen}
        mode="create"
        onClose={() => setCreateOpen(false)}
      />
      <TemplateFormModal
        open={Boolean(editTarget)}
        mode="edit"
        template={editTarget}
        onClose={() => setEditTarget(null)}
      />
      <CloneTemplateModal
        open={Boolean(cloneTarget)}
        source={cloneTarget}
        onClose={() => setCloneTarget(null)}
      />
    </div>
  );
}
