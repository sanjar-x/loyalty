'use client';

import { useState } from 'react';
import { Modal } from '@/shared/ui/Modal';
import { ErrorBanner } from '../shared/ErrorBanner';
import { createContext } from '@/features/pricing/api/contexts';
import { buildI18nPayload } from '@/shared/lib/utils';

export function CreateContextModal({ onClose, onSuccess }) {
  const [code, setCode] = useState('');
  const [nameRu, setNameRu] = useState('');
  const [nameEn, setNameEn] = useState('');
  const [marginFloorPct, setMarginFloorPct] = useState('0');
  const [roundingStep, setRoundingStep] = useState('0.01');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setError(null);

    try {
      await createContext({
        code,
        name: buildI18nPayload(nameRu, nameEn),
        margin_floor_pct: marginFloorPct,
        rounding_step: roundingStep,
      });
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
      title="Новый контекст ценообразования"
    >
      <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3">
        {error && (
          <ErrorBanner error={error} onDismiss={() => setError(null)} />
        )}

        <Field
          label="Код (snake_case)"
          value={code}
          onChange={setCode}
          placeholder="from_china"
        />
        <Field
          label="Название (RU)"
          value={nameRu}
          onChange={setNameRu}
          placeholder="Из Китая"
        />
        <Field
          label="Название (EN)"
          value={nameEn}
          onChange={setNameEn}
          placeholder="From China"
        />

        <div className="grid grid-cols-2 gap-3">
          <Field
            label="Margin floor"
            value={marginFloorPct}
            onChange={setMarginFloorPct}
            placeholder="0.10"
          />
          <Field
            label="Шаг округления"
            value={roundingStep}
            onChange={setRoundingStep}
            placeholder="0.01"
          />
        </div>

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
            disabled={saving || !code || !nameRu}
            className="bg-app-text rounded-lg px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {saving ? 'Создание…' : 'Создать'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function Field({ label, value, onChange, placeholder }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-app-muted text-xs font-medium">{label}</label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="border-app-border text-app-text focus:border-app-text focus:ring-app-text h-10 rounded-lg border bg-white px-3 text-sm transition-colors outline-none focus:ring-1"
      />
    </div>
  );
}
