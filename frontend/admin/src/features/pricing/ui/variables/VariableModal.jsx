'use client';

import { useState } from 'react';
import { Modal } from '@/shared/ui/Modal';
import { ErrorBanner } from '../shared/ErrorBanner';
import {
  createVariable,
  updateVariable,
} from '@/features/pricing/api/variables';
import { buildI18nPayload } from '@/shared/lib/utils';

const SCOPES = [
  { value: 'global', label: 'Глобальная' },
  { value: 'supplier', label: 'Поставщик' },
  { value: 'category', label: 'Категория' },
  { value: 'range', label: 'Диапазон' },
  { value: 'product_input', label: 'Ввод товара' },
  { value: 'sku_input', label: 'SKU' },
];

const DATA_TYPES = [
  { value: 'decimal', label: 'Число' },
  { value: 'integer', label: 'Целое число' },
  { value: 'percent', label: 'Процент' },
];

export function VariableModal({ mode, variable, onClose, onSuccess }) {
  const isEdit = mode === 'edit';

  const [code, setCode] = useState(variable?.code ?? '');
  const [nameRu, setNameRu] = useState(variable?.name?.ru ?? '');
  const [nameEn, setNameEn] = useState(variable?.name?.en ?? '');
  const [scope, setScope] = useState(variable?.scope ?? 'global');
  const [dataType, setDataType] = useState(variable?.dataType ?? 'decimal');
  const [unit, setUnit] = useState(variable?.unit ?? '');
  const [defaultValue, setDefaultValue] = useState(
    variable?.defaultValue ?? '',
  );
  const [isRequired, setIsRequired] = useState(variable?.isRequired ?? false);
  const [isFxRate, setIsFxRate] = useState(variable?.isFxRate ?? false);
  const [maxAgeDays, setMaxAgeDays] = useState(variable?.maxAgeDays ?? '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setError(null);

    try {
      if (isEdit) {
        const patch = {
          name: buildI18nPayload(nameRu, nameEn),
          is_required: isRequired,
          expected_version_lock: variable.versionLock,
        };
        if (defaultValue !== (variable.defaultValue ?? '')) {
          patch.default_value = defaultValue || null;
          patch.default_value_provided = true;
        }
        if (isFxRate && maxAgeDays !== (variable.maxAgeDays ?? '')) {
          patch.max_age_days = maxAgeDays ? Number(maxAgeDays) : null;
          patch.max_age_days_provided = true;
        }
        await updateVariable(variable.variableId, patch);
      } else {
        const payload = {
          code,
          scope,
          data_type: dataType,
          unit,
          name: buildI18nPayload(nameRu, nameEn),
          is_required: isRequired,
          is_fx_rate: isFxRate,
        };
        if (defaultValue) payload.default_value = defaultValue;
        if (isFxRate && maxAgeDays) payload.max_age_days = Number(maxAgeDays);
        await createVariable(payload);
      }
      onSuccess();
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      size="lg"
      title={isEdit ? `Редактировать: ${variable.code}` : 'Новая переменная'}
    >
      <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3">
        {error && (
          <ErrorBanner error={error} onDismiss={() => setError(null)} />
        )}

        <Field
          label="Код (snake_case)"
          value={code}
          onChange={setCode}
          disabled={isEdit}
          placeholder="purchase_price_cny"
        />
        <Field
          label="Название (RU)"
          value={nameRu}
          onChange={setNameRu}
          placeholder="Закупочная цена"
        />
        <Field
          label="Название (EN)"
          value={nameEn}
          onChange={setNameEn}
          placeholder="Purchase price"
        />

        <div className="grid grid-cols-3 gap-3">
          <SelectField
            label="Scope"
            value={scope}
            onChange={setScope}
            options={SCOPES}
            disabled={isEdit}
          />
          <SelectField
            label="Тип данных"
            value={dataType}
            onChange={setDataType}
            options={DATA_TYPES}
            disabled={isEdit}
          />
          <Field
            label="Единица"
            value={unit}
            onChange={setUnit}
            disabled={isEdit}
            placeholder="RUB"
          />
        </div>

        <Field
          label="Значение по умолчанию"
          value={defaultValue}
          onChange={setDefaultValue}
          placeholder="0.00"
        />

        <div className="flex items-center gap-4">
          <label className="text-app-text flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={isRequired}
              onChange={(e) => setIsRequired(e.target.checked)}
              className="rounded"
            />
            Обязательная
          </label>
          <label className="text-app-text flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={isFxRate}
              onChange={(e) => setIsFxRate(e.target.checked)}
              disabled={isEdit}
              className="rounded"
            />
            FX Rate
          </label>
        </div>

        {isFxRate && (
          <Field
            label="Max age (дней)"
            value={maxAgeDays}
            onChange={setMaxAgeDays}
            placeholder="7"
          />
        )}

        <div className="mt-2 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="text-app-muted hover:text-app-text rounded-lg px-4 py-2 text-sm font-medium transition-colors"
          >
            Отмена
          </button>
          <button
            type="submit"
            disabled={saving}
            className="bg-app-text rounded-lg px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {saving ? 'Сохранение…' : isEdit ? 'Сохранить' : 'Создать'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function Field({ label, value, onChange, disabled, placeholder }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-app-muted text-xs font-medium">{label}</label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        placeholder={placeholder}
        className="border-app-border text-app-text focus:border-app-text focus:ring-app-text disabled:bg-app-card disabled:text-app-muted h-10 rounded-lg border bg-white px-3 text-sm transition-colors outline-none focus:ring-1 disabled:cursor-not-allowed"
      />
    </div>
  );
}

function SelectField({ label, value, onChange, options, disabled }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-app-muted text-xs font-medium">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="border-app-border text-app-text focus:border-app-text focus:ring-app-text disabled:bg-app-card disabled:text-app-muted h-10 rounded-lg border bg-white px-3 text-sm transition-colors outline-none focus:ring-1 disabled:cursor-not-allowed"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}
