'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';

import { useAttributeTemplate } from '@/entities/attribute-template';
import {
  AddBindingModal,
  AssignToCategoryModal,
  BindingsList,
  CloneTemplateModal,
  TemplateFormModal,
} from '@/features/attribute-template-form';

import { i18n } from '@/shared/lib/utils';

export default function AttributeTemplateDetailPage() {
  const { templateId } = useParams();
  const { data: template, isPending, error } = useAttributeTemplate(templateId);

  const [editOpen, setEditOpen] = useState(false);
  const [cloneOpen, setCloneOpen] = useState(false);
  const [assignOpen, setAssignOpen] = useState(false);
  const [bindOpen, setBindOpen] = useState(false);

  if (isPending && !template) {
    return <div className="text-app-muted px-4 py-10 text-sm">Загрузка…</div>;
  }
  if (error || !template) {
    return (
      <div className="rounded-xl bg-red-50 px-4 py-6 text-sm text-red-700">
        {error?.message ?? 'Шаблон не найден'}
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div>
        <Link
          href="/admin/settings/attribute-templates"
          className="text-app-muted hover:text-app-text-dark text-sm"
        >
          ← Все шаблоны
        </Link>
        <div className="mt-1 flex flex-wrap items-baseline justify-between gap-3">
          <div>
            <h2 className="text-app-text text-xl font-semibold">
              {i18n(template.nameI18N, template.code)}
            </h2>
            <p className="text-app-muted font-mono text-xs">{template.code}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setEditOpen(true)}
              className="border-app-border text-app-text-dark hover:bg-app-card rounded-md border px-3 py-1.5 text-sm font-medium"
            >
              Редактировать
            </button>
            <button
              type="button"
              onClick={() => setCloneOpen(true)}
              className="border-app-border text-app-text-dark hover:bg-app-card rounded-md border px-3 py-1.5 text-sm font-medium"
            >
              Клонировать
            </button>
            <button
              type="button"
              onClick={() => setAssignOpen(true)}
              className="bg-app-text rounded-md px-3 py-1.5 text-sm font-medium text-white"
            >
              Назначить категориям
            </button>
          </div>
        </div>
        {template.descriptionI18N && i18n(template.descriptionI18N) && (
          <p className="text-app-muted mt-2 text-sm">
            {i18n(template.descriptionI18N)}
          </p>
        )}
      </div>

      <BindingsList
        templateId={template.id}
        onAddBinding={() => setBindOpen(true)}
      />

      <TemplateFormModal
        open={editOpen}
        mode="edit"
        template={template}
        onClose={() => setEditOpen(false)}
      />
      <CloneTemplateModal
        open={cloneOpen}
        source={template}
        onClose={() => setCloneOpen(false)}
      />
      <AssignToCategoryModal
        open={assignOpen}
        template={template}
        onClose={() => setAssignOpen(false)}
      />
      <AddBindingModal
        open={bindOpen}
        templateId={template.id}
        onClose={() => setBindOpen(false)}
      />
    </div>
  );
}
