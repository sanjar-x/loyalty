'use client';

import { useEffect, useMemo, useState } from 'react';

import {
  ATTRIBUTE_CREATE_DEFAULTS,
  ATTRIBUTE_DATA_TYPES,
  ATTRIBUTE_LEVELS,
  ATTRIBUTE_UI_TYPES,
  DATA_TYPE_LABELS,
  LEVEL_LABELS,
  UI_TYPE_LABELS,
  useCreateAttribute,
  useUpdateAttribute,
} from '@/entities/attribute';
import { useAttributeGroups } from '@/entities/attribute-group';

import { Modal } from '@/shared/ui/Modal';
import { buildI18nPayload, cn, i18n } from '@/shared/lib/utils';

const CODE_RE = /^[a-z0-9_]+$/;
const SLUG_RE = /^[a-z0-9-]+$/;

function makeInitialState(attribute) {
  if (attribute) {
    return {
      code: attribute.code,
      slug: attribute.slug,
      nameRu: attribute.nameI18N?.ru ?? '',
      nameEn: attribute.nameI18N?.en ?? '',
      descriptionRu: attribute.descriptionI18N?.ru ?? '',
      descriptionEn: attribute.descriptionI18N?.en ?? '',
      dataType: attribute.dataType,
      uiType: attribute.uiType,
      level: attribute.level,
      isDictionary: attribute.isDictionary ?? true,
      groupId: attribute.groupId ?? '',
      isFilterable: attribute.isFilterable,
      isSearchable: attribute.isSearchable,
      searchWeight: attribute.searchWeight ?? 5,
      isComparable: attribute.isComparable,
      isVisibleOnCard: attribute.isVisibleOnCard,
    };
  }
  return {
    code: '',
    slug: '',
    nameRu: '',
    nameEn: '',
    descriptionRu: '',
    descriptionEn: '',
    ...ATTRIBUTE_CREATE_DEFAULTS,
    groupId: '',
  };
}

/**
 * Create/edit modal for an attribute.
 *
 * Fields immutable on PATCH (`code`, `slug`, `dataType`, `isDictionary`)
 * are still rendered in edit mode but disabled — the admin can read
 * them for context without being able to drift the catalog accidentally.
 */
export function AttributeFormModal({
  open,
  mode = 'create',
  attribute,
  onClose,
}) {
  const isEdit = mode === 'edit' && attribute;
  const [state, setState] = useState(() => makeInitialState(attribute));
  const [error, setError] = useState(null);

  const groupsQuery = useAttributeGroups({ limit: 200 });
  const createMutation = useCreateAttribute();
  const updateMutation = useUpdateAttribute(attribute?.id);
  const mutation = isEdit ? updateMutation : createMutation;

  useEffect(() => {
    if (open) {
      setState(makeInitialState(attribute));
      setError(null);
      mutation.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, attribute?.id]);

  const groups = groupsQuery.data?.items ?? [];

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
  const nameError = state.nameRu.trim() ? null : 'Введите название';

  const isValid = useMemo(() => {
    if (isEdit) return Boolean(state.nameRu.trim());
    return !codeError && !slugError && !nameError;
  }, [codeError, slugError, nameError, state.nameRu, isEdit]);

  function setField(field, value) {
    setState((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    if (!isValid || mutation.isPending) return;
    setError(null);

    const payload = {
      nameI18N: buildI18nPayload(state.nameRu, state.nameEn),
      ...(state.descriptionRu
        ? {
            descriptionI18N: buildI18nPayload(
              state.descriptionRu,
              state.descriptionEn,
            ),
          }
        : {}),
      uiType: state.uiType,
      groupId: state.groupId || null,
      level: state.level,
      isFilterable: state.isFilterable,
      isSearchable: state.isSearchable,
      searchWeight: state.searchWeight,
      isComparable: state.isComparable,
      isVisibleOnCard: state.isVisibleOnCard,
    };

    if (!isEdit) {
      payload.code = state.code;
      payload.slug = state.slug;
      payload.dataType = state.dataType;
      payload.isDictionary = state.isDictionary;
    }

    try {
      if (isEdit) {
        await updateMutation.mutateAsync(payload);
      } else {
        await createMutation.mutateAsync(payload);
      }
      onClose?.();
    } catch (err) {
      setError(err?.message ?? 'Не удалось сохранить атрибут');
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="lg"
      title={isEdit ? 'Редактировать атрибут' : 'Создать атрибут'}
    >
      <form onSubmit={handleSubmit} className="mt-4 space-y-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <FieldText
            label="Код"
            value={state.code}
            disabled={isEdit}
            onChange={(v) => setField('code', v)}
            placeholder="color"
            error={!isEdit ? codeError : null}
            mono
          />
          <FieldText
            label="Slug"
            value={state.slug}
            disabled={isEdit}
            onChange={(v) => setField('slug', v)}
            placeholder="color"
            error={!isEdit ? slugError : null}
            mono
          />
          <FieldText
            label="Название (ru)"
            value={state.nameRu}
            onChange={(v) => setField('nameRu', v)}
            placeholder="Цвет"
            error={nameError}
            required
          />
          <FieldText
            label="Название (en)"
            value={state.nameEn}
            onChange={(v) => setField('nameEn', v)}
            placeholder="Color"
          />
          <FieldText
            label="Описание (ru)"
            value={state.descriptionRu}
            onChange={(v) => setField('descriptionRu', v)}
            placeholder="Опционально"
          />
          <FieldText
            label="Описание (en)"
            value={state.descriptionEn}
            onChange={(v) => setField('descriptionEn', v)}
            placeholder="Optional"
          />
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <FieldSelect
            label="Тип данных"
            disabled={isEdit}
            value={state.dataType}
            onChange={(v) => setField('dataType', v)}
            options={ATTRIBUTE_DATA_TYPES.map((t) => ({
              value: t,
              label: DATA_TYPE_LABELS[t] ?? t,
            }))}
          />
          <FieldSelect
            label="UI"
            value={state.uiType}
            onChange={(v) => setField('uiType', v)}
            options={ATTRIBUTE_UI_TYPES.map((t) => ({
              value: t,
              label: UI_TYPE_LABELS[t] ?? t,
            }))}
          />
          <FieldSelect
            label="Уровень"
            value={state.level}
            onChange={(v) => setField('level', v)}
            options={ATTRIBUTE_LEVELS.map((l) => ({
              value: l,
              label: LEVEL_LABELS[l] ?? l,
            }))}
          />
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <FieldSelect
            label="Группа"
            value={state.groupId ?? ''}
            onChange={(v) => setField('groupId', v)}
            options={[
              { value: '', label: '— Без группы —' },
              ...groups.map((g) => ({
                value: g.id,
                label: i18n(g.nameI18N, g.code),
              })),
            ]}
          />
          <FieldNumber
            label="Вес поиска (1–10)"
            value={state.searchWeight}
            onChange={(v) => setField('searchWeight', v)}
            min={1}
            max={10}
          />
        </div>

        <fieldset className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          <FieldCheckbox
            label="Справочник"
            disabled={isEdit}
            checked={state.isDictionary}
            onChange={(v) => setField('isDictionary', v)}
          />
          <FieldCheckbox
            label="Фильтр в каталоге"
            checked={state.isFilterable}
            onChange={(v) => setField('isFilterable', v)}
          />
          <FieldCheckbox
            label="Поиск"
            checked={state.isSearchable}
            onChange={(v) => setField('isSearchable', v)}
          />
          <FieldCheckbox
            label="Сравнение"
            checked={state.isComparable}
            onChange={(v) => setField('isComparable', v)}
          />
          <FieldCheckbox
            label="На карточке"
            checked={state.isVisibleOnCard}
            onChange={(v) => setField('isVisibleOnCard', v)}
          />
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

function FieldText({
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

function FieldSelect({ label, value, onChange, options, disabled }) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-app-text-dark text-xs font-medium">{label}</span>
      <select
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        className={cn(
          'border-app-border focus:border-app-text-dark rounded-lg border bg-white px-3 py-2 text-sm outline-none',
          disabled && 'bg-app-card cursor-not-allowed opacity-70',
        )}
      >
        {options.map((opt) => (
          <option key={String(opt.value)} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function FieldNumber({ label, value, onChange, min, max }) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-app-text-dark text-xs font-medium">{label}</span>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        onChange={(event) => {
          const next = Number.parseInt(event.target.value, 10);
          if (Number.isFinite(next)) onChange(next);
        }}
        className="border-app-border focus:border-app-text-dark rounded-lg border px-3 py-2 text-sm transition-colors outline-none"
      />
    </label>
  );
}

function FieldCheckbox({ label, checked, onChange, disabled }) {
  return (
    <label
      className={cn(
        'border-app-border flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm',
        disabled && 'cursor-not-allowed opacity-60',
      )}
    >
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
      />
      <span>{label}</span>
    </label>
  );
}
