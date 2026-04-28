'use client';

import { cn } from '@/lib/utils';
import { ExpressionInput } from './ExpressionInput';
import { expressionToText } from './astUtils';

export function BindingRow({
  index,
  binding,
  variables,
  componentTags,
  isLast,
  totalCount,
  onChange,
  onRemove,
  onMoveUp,
  onMoveDown,
  readOnly,
}) {
  const isFinalPrice = isLast && binding.name === 'final_price';

  function handleNameChange(e) {
    onChange({ ...binding, name: e.target.value.replace(/[^a-z0-9_]/g, '') });
  }

  function handleTagChange(e) {
    onChange({ ...binding, component_tag: e.target.value });
  }

  function handleExprChange(exprText, parsedExpr) {
    onChange({ ...binding, _exprText: exprText, expr: parsedExpr });
  }

  return (
    <div
      className={cn(
        'group grid grid-cols-[180px_1fr_140px_36px] items-start gap-2 rounded-lg px-2 py-1.5 transition-colors',
        'hover:bg-[#fafafa]',
        isFinalPrice && 'bg-emerald-50/50 ring-1 ring-emerald-200',
      )}
    >
      <input
        type="text"
        value={binding.name}
        onChange={handleNameChange}
        disabled={readOnly}
        placeholder="binding_name"
        className={cn(
          'h-9 rounded-md border border-transparent bg-transparent px-2 font-mono text-sm text-app-text outline-none transition-colors',
          'focus:border-app-border focus:bg-white',
          'disabled:cursor-default',
          isFinalPrice && 'font-semibold text-emerald-700',
        )}
      />

      <ExpressionInput
        value={binding._exprText ?? expressionToText(binding.expr)}
        onChange={handleExprChange}
        variables={variables}
        readOnly={readOnly}
        placeholder="purchase_price_cny * exchange_rate"
      />

      <select
        value={binding.component_tag}
        onChange={handleTagChange}
        disabled={readOnly}
        className={cn(
          'h-9 rounded-md border border-transparent bg-transparent px-2 text-xs text-app-muted outline-none transition-colors',
          'focus:border-app-border focus:bg-white',
          'disabled:cursor-default',
          binding.component_tag === 'final_price' && 'font-medium text-emerald-600',
        )}
      >
        {componentTags.map((tag) => (
          <option key={tag} value={tag}>{tag}</option>
        ))}
      </select>

      {!readOnly && (
        <div className="flex items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
          <div className="flex flex-col">
            {index > 0 && (
              <button
                onClick={onMoveUp}
                className="rounded p-0.5 text-app-muted hover:text-app-text"
                title="Вверх"
              >
                <svg className="h-3 w-3" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M6 2v8M3 5l3-3 3 3" />
                </svg>
              </button>
            )}
            {index < totalCount - 1 && (
              <button
                onClick={onMoveDown}
                className="rounded p-0.5 text-app-muted hover:text-app-text"
                title="Вниз"
              >
                <svg className="h-3 w-3" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M6 10V2M3 7l3 3 3-3" />
                </svg>
              </button>
            )}
          </div>
          {!isFinalPrice && (
            <button
              onClick={onRemove}
              className="rounded p-0.5 text-app-muted hover:text-red-500"
              title="Удалить"
            >
              <svg className="h-3.5 w-3.5" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M3 3l8 8M11 3l-8 8" />
              </svg>
            </button>
          )}
        </div>
      )}
    </div>
  );
}

