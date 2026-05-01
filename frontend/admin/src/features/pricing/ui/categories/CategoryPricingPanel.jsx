'use client';

import { useState, useEffect } from 'react';
import { i18n } from '@/shared/lib/utils';
import { DecimalField } from '../shared/DecimalField';
import { RangesEditor } from './RangesEditor';

export function CategoryPricingPanel({
  settings,
  categoryVariables,
  rangeVariables,
  onSave,
  onDelete,
}) {
  const [values, setValues] = useState({});
  const [ranges, setRanges] = useState([]);
  const [explicitNoRanges, setExplicitNoRanges] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (settings) {
      setValues(settings.values ?? {});
      setRanges(settings.ranges ?? []);
      setExplicitNoRanges(settings.explicitNoRanges ?? false);
    } else {
      setValues({});
      setRanges([]);
      setExplicitNoRanges(false);
    }
  }, [settings]);

  function handleValueChange(code, val) {
    setValues((prev) => ({ ...prev, [code]: val }));
  }

  async function handleSubmit() {
    setSaving(true);
    try {
      const normalizedRanges = ranges.map((r, i) => ({
        ...r,
        max: i === ranges.length - 1 && !r.max ? null : r.max,
      }));
      await onSave({
        values,
        ranges: normalizedRanges,
        explicit_no_ranges: explicitNoRanges,
        expected_version_lock: settings?.versionLock,
      });
    } finally {
      setSaving(false);
    }
  }

  const hasSettings = settings != null;

  return (
    <div className="border-app-border flex flex-col gap-5 rounded-xl border bg-white p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-app-text text-sm font-semibold">
          Настройки категории
        </h3>
        {hasSettings && (
          <button
            onClick={onDelete}
            className="text-xs text-red-500 transition-colors hover:text-red-700"
          >
            Сбросить настройки
          </button>
        )}
      </div>

      {categoryVariables.length > 0 && (
        <section className="flex flex-col gap-3">
          <h4 className="text-app-muted text-xs font-medium">
            Значения переменных (scope: category)
          </h4>
          <div className="grid grid-cols-2 gap-3">
            {categoryVariables.map((v) => (
              <DecimalField
                key={v.code}
                label={`${i18n(v.name)} (${v.code})`}
                value={values[v.code] ?? ''}
                onChange={(val) => handleValueChange(v.code, val)}
                placeholder={v.defaultValue ?? '—'}
              />
            ))}
          </div>
        </section>
      )}

      <section className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h4 className="text-app-muted text-xs font-medium">
            Диапазоны (scope: range)
          </h4>
          <label className="text-app-text flex items-center gap-2 text-xs">
            <input
              type="checkbox"
              checked={explicitNoRanges}
              onChange={(e) => {
                setExplicitNoRanges(e.target.checked);
                if (e.target.checked) setRanges([]);
              }}
              className="rounded"
            />
            Без диапазонов
          </label>
        </div>

        {!explicitNoRanges && (
          <RangesEditor
            ranges={ranges}
            onChange={setRanges}
            rangeVariables={rangeVariables}
          />
        )}

        {explicitNoRanges && rangeVariables.length > 0 && (
          <div className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-700">
            Range-переменные будут использовать значения из category-scope или
            default.
          </div>
        )}
      </section>

      <div className="flex items-center gap-2">
        <button
          onClick={handleSubmit}
          disabled={saving}
          className="bg-app-text rounded-lg px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {saving
            ? 'Сохранение…'
            : hasSettings
              ? 'Сохранить'
              : 'Создать настройки'}
        </button>
      </div>
    </div>
  );
}
