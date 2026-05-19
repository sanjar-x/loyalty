'use client';

import { useEffect, useMemo, useState } from 'react';

import {
  useCreateAttributeGroup,
  useUpdateAttributeGroup,
} from '@/entities/attribute-group';

import { Modal } from '@/shared/ui/Modal';
import { buildI18nPayload, cn } from '@/shared/lib/utils';

const CODE_RE = /^[a-z0-9_-]+$/;

function makeInitialState(group) {
  if (group) {
    return {
      code: group.code,
      nameRu: group.nameI18N?.ru ?? '',
      nameEn: group.nameI18N?.en ?? '',
      sortOrder: group.sortOrder ?? 0,
    };
  }
  return { code: '', nameRu: '', nameEn: '', sortOrder: 0 };
}

export function AttributeGroupFormModal({
  open,
  mode = 'create',
  group,
  onClose,
}) {
  const isEdit = mode === 'edit' && group;
  const [state, setState] = useState(() => makeInitialState(group));
  const [error, setError] = useState(null);

  const createMutation = useCreateAttributeGroup();
  const updateMutation = useUpdateAttributeGroup(group?.id);
  const mutation = isEdit ? updateMutation : createMutation;

  useEffect(() => {
    if (open) {
      setState(makeInitialState(group));
      setError(null);
      mutation.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, group?.id]);

  const codeError = !state.code
    ? 'Код обязателен'
    : !CODE_RE.test(state.code)
      ? 'Только нижний регистр, цифры, дефис, подчёркивание'
      : null;
  const nameError = state.nameRu.trim() ? null : 'Введите название';

  const isValid = useMemo(() => {
    if (isEdit) return Boolean(state.nameRu.trim());
    return !codeError && !nameError;
  }, [codeError, nameError, state.nameRu, isEdit]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!isValid || mutation.isPending) return;
    setError(null);

    const payload = {
      nameI18N: buildI18nPayload(state.nameRu, state.nameEn),
      sortOrder: state.sortOrder,
    };
    if (!isEdit) payload.code = state.code;

    try {
      if (isEdit) {
        await updateMutation.mutateAsync(payload);
      } else {
        await createMutation.mutateAsync(payload);
      }
      onClose?.();
    } catch (err) {
      setError(err?.message ?? 'Не удалось сохранить группу');
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="md"
      title={isEdit ? 'Редактировать группу' : 'Создать группу'}
    >
      <form onSubmit={handleSubmit} className="mt-4 space-y-4">
        <Field
          label="Код"
          value={state.code}
          disabled={isEdit}
          onChange={(v) => setState((s) => ({ ...s, code: v }))}
          placeholder="physical"
          error={!isEdit ? codeError : null}
          mono
        />
        <Field
          label="Название (ru)"
          value={state.nameRu}
          onChange={(v) => setState((s) => ({ ...s, nameRu: v }))}
          placeholder="Физические характеристики"
          error={nameError}
          required
        />
        <Field
          label="Название (en)"
          value={state.nameEn}
          onChange={(v) => setState((s) => ({ ...s, nameEn: v }))}
          placeholder="Physical characteristics"
        />
        <label className="flex flex-col gap-1 text-sm">
          <span className="text-app-text-dark text-xs font-medium">
            Порядок
          </span>
          <input
            type="number"
            min={0}
            value={state.sortOrder}
            onChange={(event) => {
              const next = Number.parseInt(event.target.value, 10);
              if (Number.isFinite(next)) {
                setState((s) => ({ ...s, sortOrder: next }));
              }
            }}
            className="border-app-border focus:border-app-text-dark rounded-lg border px-3 py-2 text-sm outline-none"
          />
        </label>

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
            disabled={!isValid || mutation.isPending}
            className="bg-app-text rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {mutation.isPending
              ? 'Сохраняем…'
              : isEdit
                ? 'Сохранить'
                : 'Создать'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  error,
  required,
  disabled,
  mono,
}) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-app-text-dark text-xs font-medium">
        {label}
        {required && <span className="text-app-danger ml-1">*</span>}
      </span>
      <input
        type="text"
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className={cn(
          'border-app-border focus:border-app-text-dark rounded-lg border px-3 py-2 text-sm transition-colors outline-none',
          mono && 'font-mono',
          error && 'border-app-danger',
          disabled && 'bg-app-card cursor-not-allowed opacity-70',
        )}
      />
      {error && <span className="text-app-danger text-xs">{error}</span>}
    </label>
  );
}
