'use client';

import { i18n } from '@/lib/utils';

function newRange() {
  return {
    id: crypto.randomUUID(),
    min: '0',
    max: '',
    values: {},
  };
}

export function RangesEditor({ ranges, onChange, rangeVariables }) {
  function addRange() {
    const lastMax = ranges.length > 0 ? ranges[ranges.length - 1].max || '0' : '0';
    onChange([...ranges, { ...newRange(), min: lastMax }]);
  }

  function updateRange(index, field, value) {
    const next = [...ranges];
    next[index] = { ...next[index], [field]: value };
    onChange(next);
  }

  function updateRangeValue(index, code, value) {
    const next = [...ranges];
    next[index] = {
      ...next[index],
      values: { ...next[index].values, [code]: value },
    };
    onChange(next);
  }

  function removeRange(index) {
    onChange(ranges.filter((_, i) => i !== index));
  }

  if (ranges.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-app-border p-6">
        <p className="text-xs text-app-muted">Нет диапазонов</p>
        <button
          onClick={addRange}
          className="text-xs font-medium text-app-text underline hover:no-underline"
        >
          + Добавить диапазон
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-app-border text-left text-[11px] font-medium text-app-muted">
              <th className="px-2 py-1.5 w-24">Min</th>
              <th className="px-2 py-1.5 w-24">Max</th>
              {rangeVariables.map((v) => (
                <th key={v.code} className="px-2 py-1.5">
                  {i18n(v.name, v.code)}
                </th>
              ))}
              <th className="px-2 py-1.5 w-8" />
            </tr>
          </thead>
          <tbody>
            {ranges.map((range, i) => {
              const isLast = i === ranges.length - 1;
              return (
                <tr key={range.id || i} className="border-b border-[#f4f3f1]">
                  <td className="px-2 py-1">
                    <input
                      type="text"
                      inputMode="decimal"
                      value={range.min}
                      onChange={(e) => updateRange(i, 'min', e.target.value)}
                      className="h-8 w-full rounded border border-app-border bg-white px-2 font-mono text-xs outline-none focus:border-app-text"
                    />
                  </td>
                  <td className="px-2 py-1">
                    {isLast ? (
                      <span className="px-2 text-xs text-app-muted">∞</span>
                    ) : (
                      <input
                        type="text"
                        inputMode="decimal"
                        value={range.max}
                        onChange={(e) => updateRange(i, 'max', e.target.value)}
                        className="h-8 w-full rounded border border-app-border bg-white px-2 font-mono text-xs outline-none focus:border-app-text"
                      />
                    )}
                  </td>
                  {rangeVariables.map((v) => (
                    <td key={v.code} className="px-2 py-1">
                      <input
                        type="text"
                        inputMode="decimal"
                        value={range.values[v.code] ?? ''}
                        onChange={(e) => updateRangeValue(i, v.code, e.target.value)}
                        placeholder={v.defaultValue ?? '—'}
                        className="h-8 w-full rounded border border-app-border bg-white px-2 font-mono text-xs outline-none focus:border-app-text"
                      />
                    </td>
                  ))}
                  <td className="px-2 py-1">
                    <button
                      onClick={() => removeRange(i)}
                      className="rounded p-1 text-app-muted hover:text-red-500"
                    >
                      <svg className="h-3.5 w-3.5" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
                        <path d="M3 3l8 8M11 3l-8 8" />
                      </svg>
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <button
        onClick={addRange}
        className="self-start rounded-lg px-3 py-1.5 text-xs font-medium text-app-muted transition-colors hover:bg-[#f4f3f1] hover:text-app-text"
      >
        + Добавить диапазон
      </button>
    </div>
  );
}
