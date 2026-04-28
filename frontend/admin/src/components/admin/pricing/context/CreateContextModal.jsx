'use client';

import { useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { ErrorBanner } from '../shared/ErrorBanner';
import { createContext } from '@/services/pricing/contexts';
import { buildI18nPayload } from '@/lib/utils';

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
    <Modal open onClose={onClose} title="Новый контекст ценообразования">
      <form onSubmit={handleSubmit} className="mt-4 flex flex-col gap-3">
        {error && <ErrorBanner error={error} onDismiss={() => setError(null)} />}

        <Field label="Код (snake_case)" value={code} onChange={setCode} placeholder="from_china" />
        <Field label="Название (RU)" value={nameRu} onChange={setNameRu} placeholder="Из Китая" />
        <Field label="Название (EN)" value={nameEn} onChange={setNameEn} placeholder="From China" />

        <div className="grid grid-cols-2 gap-3">
          <Field label="Margin floor" value={marginFloorPct} onChange={setMarginFloorPct} placeholder="0.10" />
          <Field label="Шаг округления" value={roundingStep} onChange={setRoundingStep} placeholder="0.01" />
        </div>

        <div className="mt-2 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-4 py-2 text-sm font-medium text-app-muted transition-colors hover:text-app-text"
          >
            Отмена
          </button>
          <button
            type="submit"
            disabled={saving || !code || !nameRu}
            className="rounded-lg bg-app-text px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
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
      <label className="text-xs font-medium text-app-muted">{label}</label>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="h-10 rounded-lg border border-app-border bg-white px-3 text-sm text-app-text outline-none transition-colors focus:border-app-text focus:ring-1 focus:ring-app-text"
      />
    </div>
  );
}
