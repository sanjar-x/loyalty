'use client';

import { i18n } from '@/shared/lib/utils';

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
    const lastMax =
      ranges.length > 0 ? ranges[ranges.length - 1].max || '0' : '0';
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
      <div className="border-app-border flex flex-col items-center gap-2 rounded-lg border border-dashed p-6">
        <p className="text-app-muted text-xs">Нет диапазонов</p>
        <button
          onClick={addRange}
          className="text-app-text text-xs font-medium underline hover:no-underline"
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
            <tr className="border-app-border text-app-muted border-b text-left text-[11px] font-medium">
              <th className="w-24 px-2 py-1.5">Min</th>
              <th className="w-24 px-2 py-1.5">Max</th>
              {rangeVariables.map((v) => (
                <th key={v.code} className="px-2 py-1.5">
                  {i18n(v.name, v.code)}
                </th>
              ))}
              <th className="w-8 px-2 py-1.5" />
            </tr>
          </thead>
          <tbody>
            {ranges.map((range, i) => {
              const isLast = i === ranges.length - 1;
              return (
                <tr key={range.id || i} className="border-app-card border-b">
                  <td className="px-2 py-1">
                    <input
                      type="text"
                      inputMode="decimal"
                      value={range.min}
                      onChange={(e) => updateRange(i, 'min', e.target.value)}
                      className="border-app-border focus:border-app-text h-8 w-full rounded border bg-white px-2 font-mono text-xs outline-none"
                    />
                  </td>
                  <td className="px-2 py-1">
                    {isLast ? (
                      <span className="text-app-muted px-2 text-xs">∞</span>
                    ) : (
                      <input
                        type="text"
                        inputMode="decimal"
                        value={range.max}
                        onChange={(e) => updateRange(i, 'max', e.target.value)}
                        className="border-app-border focus:border-app-text h-8 w-full rounded border bg-white px-2 font-mono text-xs outline-none"
                      />
                    )}
                  </td>
                  {rangeVariables.map((v) => (
                    <td key={v.code} className="px-2 py-1">
                      <input
                        type="text"
                        inputMode="decimal"
                        value={range.values[v.code] ?? ''}
                        onChange={(e) =>
                          updateRangeValue(i, v.code, e.target.value)
                        }
                        placeholder={v.defaultValue ?? '—'}
                        className="border-app-border focus:border-app-text h-8 w-full rounded border bg-white px-2 font-mono text-xs outline-none"
                      />
                    </td>
                  ))}
                  <td className="px-2 py-1">
                    <button
                      onClick={() => removeRange(i)}
                      className="text-app-muted rounded p-1 hover:text-red-500"
                    >
                      <svg
                        className="h-3.5 w-3.5"
                        viewBox="0 0 14 14"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.5"
                      >
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
        className="text-app-muted hover:bg-app-card hover:text-app-text self-start rounded-lg px-3 py-1.5 text-xs font-medium transition-colors"
      >
        + Добавить диапазон
      </button>
    </div>
  );
}
