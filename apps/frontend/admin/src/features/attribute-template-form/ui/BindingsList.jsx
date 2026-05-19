'use client';

import { useEffect, useState } from 'react';

import {
  REQUIREMENT_LEVELS,
  REQUIREMENT_LEVEL_LABELS,
} from '@/entities/attribute';
import {
  useTemplateBindings,
  useUnbindAttribute,
  useUpdateBinding,
} from '@/entities/attribute-template';

import { cn, i18n } from '@/shared/lib/utils';

import { useBindingsReorder } from '../model/useBindingsReorder';

const REQUIREMENT_TONE = {
  required: 'bg-red-50 text-red-700',
  recommended: 'bg-amber-50 text-amber-800',
  optional: 'bg-app-card text-app-muted',
};

/**
 * DnD-reorderable list of template bindings.
 *
 * Drag handle on each row, native HTML5 drag/drop API (kept dependency
 * footprint zero — same approach the rest of the admin uses for
 * media reorder). Optimistic local state stays in sync with the
 * server thanks to `useBindingsReorder` rollback-on-error.
 *
 * Keyboard fallback: Alt+ArrowUp / Alt+ArrowDown to move the focused
 * row, mirroring `useImageReorder`'s contract so screen-reader users
 * can rearrange without a pointer.
 */
export function BindingsList({ templateId, onAddBinding }) {
  const { data, isPending, error } = useTemplateBindings(templateId);
  const [local, setLocal] = useState([]);
  const [dragId, setDragId] = useState(null);
  // Audit 9.1 — sr-only announcer that mirrors the visible reorder
  // outcome ("«X» перемещён на позицию N из M") so SR users hear what
  // happened after Alt+↑/↓ or DnD. Mirrors the equivalent announcer in
  // <ImagesSection>; pre-fix this list silently moved rows.
  const [announce, setAnnounce] = useState('');
  const updateMutation = useUpdateBinding(templateId);
  const unbindMutation = useUnbindAttribute(templateId);
  const {
    reorder,
    error: reorderError,
    clearError,
  } = useBindingsReorder({
    templateId,
    onLocalReorder: setLocal,
  });

  // Seed / re-sync the local state any time the server snapshot
  // identity changes — DnD reorder mutates `local` directly, so we
  // can't read from `data?.items` straight in render.
  useEffect(() => {
    if (data?.items) {
      const sorted = [...data.items].sort((a, b) => a.sortOrder - b.sortOrder);
      setLocal(sorted);
    }
  }, [data]);

  function handleDragStart(event, id) {
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', id);
    setDragId(id);
  }

  function handleDragOver(event) {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }

  function announceMove(binding, targetIdx) {
    const name = i18n(binding.attributeNameI18N, binding.attributeCode);
    setAnnounce(
      `«${name}» перемещён на позицию ${targetIdx + 1} из ${local.length}`,
    );
  }

  function handleDrop(event, targetId) {
    event.preventDefault();
    const sourceId = dragId ?? event.dataTransfer.getData('text/plain');
    setDragId(null);
    if (!sourceId || sourceId === targetId) return;
    const fromIdx = local.findIndex((b) => b.id === sourceId);
    const toIdx = local.findIndex((b) => b.id === targetId);
    if (fromIdx < 0 || toIdx < 0) return;
    const next = local.slice();
    const [moved] = next.splice(fromIdx, 1);
    next.splice(toIdx, 0, moved);
    reorder(local, next);
    announceMove(moved, toIdx);
  }

  function handleKeyboardMove(event, idx) {
    if (!event.altKey) return;
    let target = null;
    if (event.key === 'ArrowUp' && idx > 0) target = idx - 1;
    if (event.key === 'ArrowDown' && idx < local.length - 1) target = idx + 1;
    if (target === null) return;
    event.preventDefault();
    const next = local.slice();
    const [moved] = next.splice(idx, 1);
    next.splice(target, 0, moved);
    reorder(local, next);
    announceMove(moved, target);
  }

  function handleRequirementChange(binding, requirementLevel) {
    updateMutation.mutate({
      bindingId: binding.id,
      payload: { requirementLevel },
    });
  }

  function handleUnbind(binding) {
    if (
      !confirm(
        `Отвязать «${i18n(binding.attributeNameI18N, binding.attributeCode)}» от шаблона?`,
      )
    ) {
      return;
    }
    unbindMutation.mutate(binding.id);
  }

  return (
    <section aria-label="Привязанные атрибуты" className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-app-text-dark text-base font-semibold">
          Привязанные атрибуты
        </h3>
        <button
          type="button"
          onClick={onAddBinding}
          className="bg-app-text rounded-lg px-3 py-1.5 text-sm font-medium text-white"
        >
          + Привязать атрибут
        </button>
      </div>

      {error ? (
        <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
          {error.message ?? 'Не удалось загрузить привязки'}
        </div>
      ) : isPending ? (
        <p className="text-app-muted text-sm">Загружаем…</p>
      ) : local.length === 0 ? (
        <p className="text-app-muted text-sm">
          К шаблону ещё не привязан ни один атрибут.
        </p>
      ) : (
        <>
          {/* Audit 9.2 — visually-hidden instructions tied to the list
              description so SR users hear how to drive the keyboard
              fallback. The visible drag handle stays a decorative span
              (its `title` is unreliable across SR engines). */}
          <p id="bindings-keyboard-hint" className="sr-only">
            Используйте клавиши Alt со стрелкой вверх или вниз, чтобы
            переместить элемент с клавиатуры.
          </p>
          <ul
            className="border-app-border divide-app-border divide-y rounded-xl border"
            aria-label="Список привязок"
            aria-describedby="bindings-keyboard-hint"
          >
            {local.map((binding, idx) => (
              <li
                key={binding.id}
                draggable
                onDragStart={(event) => handleDragStart(event, binding.id)}
                onDragOver={handleDragOver}
                onDrop={(event) => handleDrop(event, binding.id)}
                onKeyDown={(event) => handleKeyboardMove(event, idx)}
                tabIndex={0}
                className={cn(
                  'flex items-center gap-3 px-3 py-2 text-sm transition-colors',
                  dragId === binding.id && 'bg-app-card opacity-70',
                  'focus:outline-app-text-dark focus:outline focus:outline-2',
                )}
              >
                <span
                  aria-hidden="true"
                  className="text-app-muted cursor-grab select-none"
                  title="Перетащить (Alt+↑/↓ для клавиатуры)"
                >
                  ⋮⋮
                </span>
                <div className="flex flex-col gap-0.5">
                  <span className="text-app-text-dark font-medium">
                    {i18n(binding.attributeNameI18N, binding.attributeCode)}
                  </span>
                  <span className="text-app-muted font-mono text-xs">
                    {binding.attributeCode} · {binding.attributeLevel}
                  </span>
                </div>
                <span
                  className={cn(
                    'ml-auto rounded-full px-2 py-0.5 text-xs font-medium',
                    REQUIREMENT_TONE[binding.requirementLevel] ??
                      REQUIREMENT_TONE.optional,
                  )}
                >
                  {REQUIREMENT_LEVEL_LABELS[binding.requirementLevel] ??
                    binding.requirementLevel}
                </span>
                <select
                  aria-label="Уровень требования"
                  value={binding.requirementLevel}
                  onChange={(event) =>
                    handleRequirementChange(binding, event.target.value)
                  }
                  className="border-app-border focus:border-app-text-dark rounded-md border bg-white px-2 py-1 text-xs outline-none"
                >
                  {REQUIREMENT_LEVELS.map((level) => (
                    <option key={level} value={level}>
                      {REQUIREMENT_LEVEL_LABELS[level] ?? level}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={() => handleUnbind(binding)}
                  className="rounded-md border border-red-200 px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
                >
                  Отвязать
                </button>
              </li>
            ))}
          </ul>
        </>
      )}

      <p role="status" aria-live="polite" className="sr-only">
        {announce}
      </p>

      {reorderError && (
        <div
          role="alert"
          className="flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700"
        >
          <span>
            Не удалось сохранить порядок:{' '}
            {reorderError.message ?? 'неизвестная ошибка'}
          </span>
          <button
            type="button"
            onClick={clearError}
            className="font-medium underline"
          >
            Скрыть
          </button>
        </div>
      )}
    </section>
  );
}
