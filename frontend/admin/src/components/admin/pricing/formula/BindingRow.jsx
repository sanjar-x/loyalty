'use client';

import { cn } from '@/lib/utils';
import { ExpressionBuilder } from './ExpressionBuilder';

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

  function handleLabelChange(e) {
    const label = e.target.value;
    const name = isFinalPrice ? 'final_price' : labelToName(label);
    onChange({ ...binding, label, name });
  }

  function handleTagChange(e) {
    onChange({ ...binding, component_tag: e.target.value });
  }

  function handleExprChange(newExpr) {
    onChange({ ...binding, expr: newExpr });
  }

  const displayLabel = binding.label ?? binding.name ?? '';

  return (
    <div
      className={cn(
        'group flex items-start gap-2 rounded-xl border border-transparent px-3 py-2 transition-colors',
        'hover:border-gray-200 hover:bg-[#fafafa]',
        isFinalPrice && 'border-emerald-200 bg-emerald-50/30',
      )}
    >
      <div className="flex shrink-0 flex-col gap-0.5 pt-2">
        <div className="flex items-center gap-1.5">
          <input
            type="text"
            value={displayLabel}
            onChange={handleLabelChange}
            disabled={readOnly || isFinalPrice}
            placeholder="Название строки"
            className={cn(
              'h-8 w-44 rounded-lg border border-app-border bg-white px-2.5 text-sm outline-none transition-colors',
              'focus:border-app-text focus:ring-1 focus:ring-app-text',
              'disabled:border-transparent disabled:bg-transparent',
              isFinalPrice && 'font-semibold text-emerald-700',
            )}
          />
          <span className="text-sm text-gray-400">=</span>
        </div>
        {!isFinalPrice && binding.name && (
          <span className="pl-1 font-mono text-[10px] text-gray-400" title="Техническое имя в формуле">
            {binding.name}
          </span>
        )}
      </div>

      <div className="min-w-0 flex-1">
        <ExpressionBuilder
          expr={binding.expr}
          onChange={handleExprChange}
          variables={variables}
          readOnly={readOnly}
        />
      </div>

      <div className="flex shrink-0 items-center gap-1.5 pt-2">
        <select
          value={binding.component_tag}
          onChange={handleTagChange}
          disabled={readOnly}
          className={cn(
            'h-8 rounded-lg border border-app-border bg-white px-2 text-xs outline-none',
            'disabled:border-transparent disabled:bg-transparent',
            binding.component_tag === 'final_price' && 'font-medium text-emerald-600',
            binding.component_tag === 'cogs' && 'text-blue-600',
            binding.component_tag === 'shipping' && 'text-purple-600',
            binding.component_tag === 'margin' && 'text-amber-600',
            binding.component_tag === 'tax' && 'text-red-600',
          )}
        >
          {componentTags.map((tag) => (
            <option key={tag} value={tag}>{TAG_LABELS[tag] || tag}</option>
          ))}
        </select>

        {!readOnly && (
          <div className="flex items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
            {index > 0 && (
              <button onClick={onMoveUp} className="rounded p-1 text-gray-400 hover:text-app-text" title="Вверх">
                <svg className="h-3.5 w-3.5" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M6 2v8M3 5l3-3 3 3" />
                </svg>
              </button>
            )}
            {index < totalCount - 1 && (
              <button onClick={onMoveDown} className="rounded p-1 text-gray-400 hover:text-app-text" title="Вниз">
                <svg className="h-3.5 w-3.5" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M6 10V2M3 7l3 3 3-3" />
                </svg>
              </button>
            )}
            {!isFinalPrice && (
              <button onClick={onRemove} className="rounded p-1 text-gray-400 hover:text-red-500" title="Удалить">
                <svg className="h-3.5 w-3.5" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M3 3l8 8M11 3l-8 8" />
                </svg>
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

const TAG_LABELS = {
  cogs: 'Себестоимость',
  shipping: 'Доставка',
  commission: 'Комиссия',
  tax: 'Налог',
  margin: 'Маржа',
  final_price: 'Итого',
  intermediate: 'Промежуточное',
};

const TRANSLIT = {
  'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'zh',
  'з':'z','и':'i','й':'y','к':'k','л':'l','м':'m','н':'n','о':'o',
  'п':'p','р':'r','с':'s','т':'t','у':'u','ф':'f','х':'kh','ц':'ts',
  'ч':'ch','ш':'sh','щ':'shch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya',
};

function labelToName(label) {
  if (!label) return '';
  const lower = label.toLowerCase();
  let result = '';
  for (const ch of lower) {
    if (TRANSLIT[ch] !== undefined) {
      result += TRANSLIT[ch];
    } else if (/[a-z0-9]/.test(ch)) {
      result += ch;
    } else {
      result += '_';
    }
  }
  return result
    .replace(/_+/g, '_')
    .replace(/^_|_$/g, '')
    .slice(0, 64) || 'binding';
}
