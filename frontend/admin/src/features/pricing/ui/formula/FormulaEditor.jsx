'use client';

import { useCallback } from 'react';
import { BindingRow } from './BindingRow';

const COMPONENT_TAGS = [
  'cogs',
  'shipping',
  'commission',
  'tax',
  'margin',
  'final_price',
  'intermediate',
];

function createEmptyBinding() {
  return {
    name: '',
    label: '',
    component_tag: 'intermediate',
    expr: { const: '0' },
  };
}

export function FormulaEditor({ bindings, onChange, variables, readOnly }) {
  const updateBinding = useCallback(
    (index, updated) => {
      const next = [...bindings];
      next[index] = updated;
      onChange(next);
    },
    [bindings, onChange],
  );

  const removeBinding = useCallback(
    (index) => {
      const next = bindings.filter((_, i) => i !== index);
      onChange(next);
    },
    [bindings, onChange],
  );

  const addBinding = useCallback(() => {
    onChange([...bindings, createEmptyBinding()]);
  }, [bindings, onChange]);

  const moveBinding = useCallback(
    (from, to) => {
      if (to < 0 || to >= bindings.length) return;
      const next = [...bindings];
      const [moved] = next.splice(from, 1);
      next.splice(to, 0, moved);
      onChange(next);
    },
    [bindings, onChange],
  );

  return (
    <div className="flex flex-col gap-1">
      <div className="text-app-muted mb-1 px-3 text-[11px] font-medium">
        Каждая строка: <code>имя</code> = <code>выражение</code> ·{' '}
        <code>tag</code>
      </div>

      {bindings.map((binding, index) => (
        <BindingRow
          key={index}
          index={index}
          binding={binding}
          bindings={bindings}
          variables={variables}
          componentTags={COMPONENT_TAGS}
          isLast={index === bindings.length - 1}
          totalCount={bindings.length}
          onChange={(updated) => updateBinding(index, updated)}
          onRemove={() => removeBinding(index)}
          onMoveUp={() => moveBinding(index, index - 1)}
          onMoveDown={() => moveBinding(index, index + 1)}
          readOnly={readOnly}
        />
      ))}

      {!readOnly && (
        <button
          onClick={addBinding}
          className="text-app-muted hover:bg-app-card hover:text-app-text mt-1 flex items-center gap-2 self-start rounded-lg px-3 py-2 text-sm font-medium transition-colors"
        >
          <svg
            className="h-4 w-4"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
          >
            <path d="M8 3v10M3 8h10" />
          </svg>
          Добавить строку
        </button>
      )}
    </div>
  );
}
