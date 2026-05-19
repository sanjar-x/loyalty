'use client';

import { useEffect, useMemo, useState } from 'react';

import {
  REQUIREMENT_LEVELS,
  REQUIREMENT_LEVEL_LABELS,
  useAttributes,
} from '@/entities/attribute';
import {
  useBindAttribute,
  useTemplateBindings,
} from '@/entities/attribute-template';

import { Modal } from '@/shared/ui/Modal';
import { cn, i18n } from '@/shared/lib/utils';

export function AddBindingModal({ open, templateId, onClose }) {
  const [attributeId, setAttributeId] = useState('');
  const [requirementLevel, setRequirementLevel] = useState('optional');
  const [error, setError] = useState(null);

  const attributesQuery = useAttributes({ limit: 200 });
  const bindingsQuery = useTemplateBindings(templateId);
  const mutation = useBindAttribute(templateId);

  useEffect(() => {
    if (open) {
      setAttributeId('');
      setRequirementLevel('optional');
      setError(null);
      mutation.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, templateId]);

  // Filter out already-bound attributes — backend would 422 on
  // duplicate, but it's nicer to hide them upfront.
  const candidates = useMemo(() => {
    const all = attributesQuery.data?.items ?? [];
    const boundIds = new Set(
      (bindingsQuery.data?.items ?? []).map((b) => b.attributeId),
    );
    return all.filter((attr) => !boundIds.has(attr.id));
  }, [attributesQuery.data, bindingsQuery.data]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!attributeId || mutation.isPending) return;
    setError(null);
    try {
      await mutation.mutateAsync({
        attributeId,
        sortOrder: bindingsQuery.data?.items?.length ?? 0,
        requirementLevel,
      });
      onClose?.();
    } catch (err) {
      setError(err?.message ?? 'Не удалось привязать атрибут');
    }
  }

  return (
    <Modal open={open} onClose={onClose} size="md" title="Привязать атрибут">
      <form onSubmit={handleSubmit} className="mt-4 space-y-4">
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-app-text-dark text-xs font-medium">
            Атрибут
          </span>
          <select
            value={attributeId}
            onChange={(event) => setAttributeId(event.target.value)}
            disabled={attributesQuery.isPending && !attributesQuery.data}
            className="border-app-border focus:border-app-text-dark rounded-lg border bg-white px-3 py-2 text-sm outline-none"
          >
            <option value="">— Выберите атрибут —</option>
            {candidates.map((attr) => (
              <option key={attr.id} value={attr.id}>
                {i18n(attr.nameI18N, attr.code)} · {attr.code}
              </option>
            ))}
          </select>
          {!attributesQuery.isPending && candidates.length === 0 && (
            <span className="text-app-muted text-xs">
              Все доступные атрибуты уже привязаны.
            </span>
          )}
        </label>

        <fieldset className="space-y-2">
          <legend className="text-app-text-dark text-xs font-medium">
            Уровень требования
          </legend>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            {REQUIREMENT_LEVELS.map((level) => {
              const checked = requirementLevel === level;
              return (
                <label
                  key={level}
                  className={cn(
                    'border-app-border flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm',
                    checked && 'border-app-text-dark bg-app-card',
                  )}
                >
                  <input
                    type="radio"
                    name="requirementLevel"
                    value={level}
                    checked={checked}
                    onChange={() => setRequirementLevel(level)}
                  />
                  <span>{REQUIREMENT_LEVEL_LABELS[level] ?? level}</span>
                </label>
              );
            })}
          </div>
        </fieldset>

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
            disabled={!attributeId || mutation.isPending}
            className="bg-app-text rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {mutation.isPending ? 'Привязываем…' : 'Привязать'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
