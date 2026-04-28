'use client';

import { useState, useRef } from 'react';
import { cn } from '@/lib/utils';

const OPERATORS = ['+', '-', '*', '/'];
const FUNCTIONS = ['min', 'max', 'round', 'ceil', 'floor', 'abs', 'if'];

export function ExpressionBuilder({ expr, onChange, variables, readOnly }) {
  return (
    <div className="flex min-h-[36px] flex-wrap items-center gap-1 rounded-lg border border-app-border bg-white px-2 py-1.5">
      <ExprNode expr={expr} onChange={onChange} variables={variables} readOnly={readOnly} path={[]} />
      {!readOnly && isEmptyExpr(expr) && (
        <AddNodeMenu
          variables={variables}
          onSelect={(node) => onChange(node)}
          label="+ Выражение"
        />
      )}
    </div>
  );
}

function ExprNode({ expr, onChange, variables, readOnly, path }) {
  if (!expr || typeof expr !== 'object') {
    return <ConstChip value="" onChange={(v) => onChange({ const: v })} readOnly={readOnly} />;
  }

  if ('const' in expr) {
    return (
      <ConstChip
        value={expr.const}
        onChange={(v) => onChange({ const: v })}
        readOnly={readOnly}
        onDelete={() => onChange({ const: '0' })}
      />
    );
  }

  if ('var' in expr) {
    const v = variables?.find((x) => x.code === expr.var);
    return (
      <VarChip
        code={expr.var}
        unit={v?.unit}
        scope={v?.scope}
        readOnly={readOnly}
        onReplace={readOnly ? undefined : (node) => onChange(node)}
        variables={variables}
      />
    );
  }

  if ('ref' in expr) {
    return (
      <span className="inline-flex items-center rounded-md bg-violet-100 px-2 py-0.5 text-xs font-medium text-violet-700">
        {expr.ref}
      </span>
    );
  }

  if ('op' in expr && Array.isArray(expr.args)) {
    return (
      <OpNode
        op={expr.op}
        args={expr.args}
        onChange={onChange}
        variables={variables}
        readOnly={readOnly}
        path={path}
      />
    );
  }

  if ('fn' in expr && Array.isArray(expr.args)) {
    return (
      <FnNode
        fn={expr.fn}
        args={expr.args}
        onChange={onChange}
        variables={variables}
        readOnly={readOnly}
        path={path}
      />
    );
  }

  return <span className="text-xs text-red-400">???</span>;
}

function OpNode({ op, args, onChange, variables, readOnly, path }) {
  function updateArg(index, newArg) {
    const newArgs = [...args];
    newArgs[index] = newArg;
    onChange({ op, args: newArgs });
  }

  function changeOp(newOp) {
    onChange({ op: newOp, args });
  }

  function addArg() {
    onChange({ op, args: [...args, { const: '0' }] });
  }

  function removeArg(index) {
    if (args.length <= 2) return;
    onChange({ op, args: args.filter((_, i) => i !== index) });
  }

  return (
    <div className="inline-flex flex-wrap items-center gap-0.5 rounded-lg bg-gray-50 px-1 py-0.5">
      <span className="text-[10px] text-gray-400">(</span>
      {args.map((arg, i) => (
        <div key={i} className="flex items-center gap-0.5">
          {i > 0 && (
            readOnly ? (
              <span className="mx-0.5 text-sm font-bold text-blue-600">{op}</span>
            ) : (
              <select
                value={op}
                onChange={(e) => changeOp(e.target.value)}
                className="mx-0.5 h-6 rounded border-none bg-blue-100 px-1 text-xs font-bold text-blue-700 outline-none"
              >
                {OPERATORS.map((o) => (
                  <option key={o} value={o}>{o}</option>
                ))}
              </select>
            )
          )}
          <div className="flex items-center gap-0.5">
            <ExprNode
              expr={arg}
              onChange={(newArg) => updateArg(i, newArg)}
              variables={variables}
              readOnly={readOnly}
              path={[...path, i]}
            />
            {!readOnly && args.length > 2 && (
              <button
                onClick={() => removeArg(i)}
                className="ml-0.5 rounded p-0.5 text-gray-300 hover:text-red-400"
                title="Удалить операнд"
              >
                <svg className="h-2.5 w-2.5" viewBox="0 0 10 10" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="M2 2l6 6M8 2l-6 6" />
                </svg>
              </button>
            )}
          </div>
        </div>
      ))}
      <span className="text-[10px] text-gray-400">)</span>
      {!readOnly && (op === '+' || op === '*') && (
        <button
          onClick={addArg}
          className="ml-0.5 rounded bg-gray-200 px-1 py-0.5 text-[10px] text-gray-500 hover:bg-gray-300"
          title="Добавить операнд"
        >
          +
        </button>
      )}
    </div>
  );
}

function FnNode({ fn, args, onChange, variables, readOnly, path }) {
  function updateArg(index, newArg) {
    const newArgs = [...args];
    newArgs[index] = newArg;
    onChange({ fn, args: newArgs });
  }

  function changeFn(newFn) {
    onChange({ fn: newFn, args });
  }

  return (
    <div className="inline-flex flex-wrap items-center gap-0.5 rounded-lg bg-amber-50 px-1 py-0.5 ring-1 ring-amber-200">
      {readOnly ? (
        <span className="text-xs font-semibold text-amber-700">{fn}(</span>
      ) : (
        <>
          <select
            value={fn}
            onChange={(e) => changeFn(e.target.value)}
            className="h-5 rounded border-none bg-amber-100 px-1 text-xs font-semibold text-amber-700 outline-none"
          >
            {FUNCTIONS.map((f) => (
              <option key={f} value={f}>{f}</option>
            ))}
          </select>
          <span className="text-xs text-amber-600">(</span>
        </>
      )}
      {args.map((arg, i) => (
        <div key={i} className="flex items-center gap-0.5">
          {i > 0 && <span className="text-xs text-amber-400">,</span>}
          <ExprNode
            expr={arg}
            onChange={(newArg) => updateArg(i, newArg)}
            variables={variables}
            readOnly={readOnly}
            path={[...path, i]}
          />
        </div>
      ))}
      <span className="text-xs text-amber-600">)</span>
    </div>
  );
}

function ConstChip({ value, onChange, readOnly, onDelete }) {
  const [editing, setEditing] = useState(false);
  const inputRef = useRef(null);

  if (readOnly) {
    return (
      <span className="inline-flex items-center rounded-md bg-gray-100 px-2 py-0.5 font-mono text-xs text-gray-700">
        {value || '0'}
      </span>
    );
  }

  if (editing) {
    return (
      <input
        ref={inputRef}
        autoFocus
        type="text"
        inputMode="decimal"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onBlur={() => setEditing(false)}
        onKeyDown={(e) => { if (e.key === 'Enter') setEditing(false); }}
        className="h-6 w-16 rounded-md border border-gray-300 bg-white px-1.5 font-mono text-xs text-gray-700 outline-none focus:border-blue-400"
      />
    );
  }

  return (
    <span
      onClick={() => setEditing(true)}
      className="inline-flex cursor-pointer items-center rounded-md bg-gray-100 px-2 py-0.5 font-mono text-xs text-gray-700 transition-colors hover:bg-gray-200"
      title="Нажмите чтобы изменить"
    >
      {value || '0'}
    </span>
  );
}

function VarChip({ code, unit, scope, readOnly, onReplace, variables }) {
  const [showMenu, setShowMenu] = useState(false);

  const SCOPE_COLORS = {
    global: 'bg-emerald-100 text-emerald-700 ring-emerald-200',
    supplier: 'bg-blue-100 text-blue-700 ring-blue-200',
    category: 'bg-purple-100 text-purple-700 ring-purple-200',
    range: 'bg-orange-100 text-orange-700 ring-orange-200',
    product_input: 'bg-pink-100 text-pink-700 ring-pink-200',
    sku_input: 'bg-cyan-100 text-cyan-700 ring-cyan-200',
  };

  const colorClass = SCOPE_COLORS[scope] || 'bg-gray-100 text-gray-700 ring-gray-200';

  return (
    <span className="relative inline-flex items-center">
      <span
        onClick={!readOnly ? () => setShowMenu(!showMenu) : undefined}
        className={cn(
          'inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium ring-1',
          colorClass,
          !readOnly && 'cursor-pointer hover:brightness-95',
        )}
      >
        <span className="font-mono">{code}</span>
        {unit && <span className="text-[10px] opacity-60">{unit}</span>}
      </span>

      {showMenu && (
        <div className="absolute top-full left-0 z-30 mt-1 max-h-48 w-64 overflow-y-auto rounded-xl border border-app-border bg-white p-1 shadow-lg">
          {variables?.map((v) => (
            <button
              key={v.code}
              onMouseDown={(e) => {
                e.preventDefault();
                onReplace({ var: v.code });
                setShowMenu(false);
              }}
              className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left transition-colors hover:bg-[#f4f3f1]"
            >
              <code className="text-xs font-medium">{v.code}</code>
              <span className="text-[10px] text-app-muted">{v.unit} · {v.scope}</span>
            </button>
          ))}
        </div>
      )}
    </span>
  );
}

function AddNodeMenu({ variables, onSelect, label }) {
  const [open, setOpen] = useState(false);

  return (
    <span className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="rounded-md bg-[#f4f3f1] px-2 py-1 text-[11px] font-medium text-app-muted transition-colors hover:bg-[#eae9e6] hover:text-app-text"
      >
        {label}
      </button>

      {open && (
        <div className="absolute top-full left-0 z-30 mt-1 w-56 rounded-xl border border-app-border bg-white p-1.5 shadow-lg">
          <div className="mb-1 px-2 text-[10px] font-semibold uppercase tracking-wide text-gray-400">Переменная</div>
          <div className="max-h-32 overflow-y-auto">
            {variables?.map((v) => (
              <button
                key={v.code}
                onMouseDown={(e) => {
                  e.preventDefault();
                  onSelect({ var: v.code });
                  setOpen(false);
                }}
                className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1 text-left transition-colors hover:bg-[#f4f3f1]"
              >
                <code className="text-xs">{v.code}</code>
                <span className="text-[10px] text-app-muted">{v.unit}</span>
              </button>
            ))}
          </div>

          <div className="my-1 border-t border-gray-100" />
          <div className="mb-1 px-2 text-[10px] font-semibold uppercase tracking-wide text-gray-400">Константа</div>
          <button
            onMouseDown={(e) => { e.preventDefault(); onSelect({ const: '0' }); setOpen(false); }}
            className="flex w-full items-center rounded-lg px-2.5 py-1 text-left text-xs transition-colors hover:bg-[#f4f3f1]"
          >
            Число (0)
          </button>

          <div className="my-1 border-t border-gray-100" />
          <div className="mb-1 px-2 text-[10px] font-semibold uppercase tracking-wide text-gray-400">Оператор</div>
          <div className="flex gap-1 px-2">
            {OPERATORS.map((op) => (
              <button
                key={op}
                onMouseDown={(e) => {
                  e.preventDefault();
                  onSelect({ op, args: [{ const: '0' }, { const: '0' }] });
                  setOpen(false);
                }}
                className="flex h-7 w-7 items-center justify-center rounded-md bg-blue-50 text-xs font-bold text-blue-600 hover:bg-blue-100"
              >
                {op}
              </button>
            ))}
          </div>

          <div className="my-1 border-t border-gray-100" />
          <div className="mb-1 px-2 text-[10px] font-semibold uppercase tracking-wide text-gray-400">Функция</div>
          <div className="flex flex-wrap gap-1 px-2 pb-1">
            {FUNCTIONS.map((fn) => (
              <button
                key={fn}
                onMouseDown={(e) => {
                  e.preventDefault();
                  const argCount = fn === 'if' ? 3 : fn === 'round' ? 2 : 1;
                  onSelect({ fn, args: Array.from({ length: argCount }, () => ({ const: '0' })) });
                  setOpen(false);
                }}
                className="rounded-md bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700 ring-1 ring-amber-200 hover:bg-amber-100"
              >
                {fn}()
              </button>
            ))}
          </div>
        </div>
      )}
    </span>
  );
}

function isEmptyExpr(expr) {
  if (!expr) return true;
  if (typeof expr !== 'object') return true;
  if ('const' in expr && (expr.const === '0' || expr.const === '')) return true;
  return false;
}
