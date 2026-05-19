'use client';

import { useEffect, useMemo, useState } from 'react';

import {
  useCreateAttributeValue,
  useUpdateAttributeValue,
} from '@/entities/attribute-value';

import { Modal } from '@/shared/ui/Modal';
import { buildI18nPayload, cn } from '@/shared/lib/utils';

const CODE_RE = /^[a-z0-9_]+$/;
const SLUG_RE = /^[a-z0-9-]+$/;

function makeInitialState(value) {
  if (value) {
    return {
      code: value.code,
      slug: value.slug,
      nameRu: value.valueI18N?.ru ?? '',
      nameEn: value.valueI18N?.en ?? '',
      searchAliases: (value.searchAliases ?? []).join(', '),
      hex:
        typeof value.metaData === 'object' && value.metaData?.hex
          ? value.metaData.hex
          : '',
      valueGroup: value.valueGroup ?? '',
      sortOrder: value.sortOrder ?? 0,
    };
  }
  return {
    code: '',
    slug: '',
    nameRu: '',
    nameEn: '',
    searchAliases: '',
    hex: '',
    valueGroup: '',
    sortOrder: 0,
  };
}

export function AttributeValueFormModal({
  open,
  mode = 'create',
  attributeId,
  value,
  onClose,
}) {
  const isEdit = mode === 'edit' && value;
  const [state, setState] = useState(() => makeInitialState(value));
  const [error, setError] = useState(null);

  const createMutation = useCreateAttributeValue(attributeId);
  const updateMutation = useUpdateAttributeValue(attributeId);
  const mutation = isEdit ? updateMutation : createMutation;

  useEffect(() => {
    if (open) {
      setState(makeInitialState(value));
      setError(null);
      mutation.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, value?.id]);

  const codeError = !state.code
    ? 'Код обязателен'
    : !CODE_RE.test(state.code)
      ? 'Только нижний регистр, цифры и подчёркивание'
      : null;
  const slugError = !state.slug
    ? 'Slug обязателен'
    : !SLUG_RE.test(state.slug)
      ? 'Только нижний регистр, цифры и дефис'
      : null;
  const nameError = state.nameRu.trim() ? null : 'Введите значение';

  const isValid = useMemo(() => {
    if (isEdit) return Boolean(state.nameRu.trim());
    return !codeError && !slugError && !nameError;
  }, [codeError, slugError, nameError, state.nameRu, isEdit]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!isValid || mutation.isPending) return;
    setError(null);

    const aliases = state.searchAliases
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
    const metaData = state.hex ? { hex: state.hex.trim() } : {};

    const basePayload = {
      valueI18N: buildI18nPayload(state.nameRu, state.nameEn),
      searchAliases: aliases,
      metaData,
      valueGroup: state.valueGroup || null,
      sortOrder: state.sortOrder,
    };

    try {
      if (isEdit) {
        await updateMutation.mutateAsync({
          valueId: value.id,
          payload: basePayload,
        });
      } else {
        await createMutation.mutateAsync({
          ...basePayload,
          code: state.code,
          slug: state.slug,
        });
      }
      onClose?.();
    } catch (err) {
      setError(err?.message ?? 'Не удалось сохранить значение');
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="md"
      title={isEdit ? 'Редактировать значение' : 'Создать значение'}
    >
      <form onSubmit={handleSubmit} className="mt-4 space-y-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field
            label="Код"
            value={state.code}
            disabled={isEdit}
            onChange={(v) => setState((s) => ({ ...s, code: v }))}
            placeholder="red"
            error={!isEdit ? codeError : null}
            mono
          />
          <Field
            label="Slug"
            value={state.slug}
            disabled={isEdit}
            onChange={(v) => setState((s) => ({ ...s, slug: v }))}
            placeholder="red"
            error={!isEdit ? slugError : null}
            mono
          />
          <Field
            label="Значение (ru)"
            value={state.nameRu}
            onChange={(v) => setState((s) => ({ ...s, nameRu: v }))}
            placeholder="Красный"
            error={nameError}
            required
          />
          <Field
            label="Значение (en)"
            value={state.nameEn}
            onChange={(v) => setState((s) => ({ ...s, nameEn: v }))}
            placeholder="Red"
          />
          <Field
            label="Поисковые синонимы (через запятую)"
            value={state.searchAliases}
            onChange={(v) => setState((s) => ({ ...s, searchAliases: v }))}
            placeholder="scarlet, crimson"
          />
          <Field
            label="HEX (для color_swatch)"
            value={state.hex}
            onChange={(v) => setState((s) => ({ ...s, hex: v }))}
            placeholder="#FF0000"
            mono
          />
          <Field
            label="Группа значений"
            value={state.valueGroup}
            onChange={(v) => setState((s) => ({ ...s, valueGroup: v }))}
            placeholder="Warm tones"
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
        </div>

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
