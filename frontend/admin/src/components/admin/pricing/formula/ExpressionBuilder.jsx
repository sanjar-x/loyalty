'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { cn } from '@/lib/utils';
import { expressionToText } from './astUtils';

export function ExpressionBuilder({ expr, onChange, variables, readOnly }) {
  const [text, setText] = useState(() => expressionToText(expr));
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestionFilter, setSuggestionFilter] = useState('');
  const [caretPos, setCaretPos] = useState(0);
  const textareaRef = useRef(null);
  const lastParsedRef = useRef(expr);

  useEffect(() => {
    const incoming = JSON.stringify(expr);
    const last = JSON.stringify(lastParsedRef.current);
    if (incoming !== last) {
      setText(expressionToText(expr));
      lastParsedRef.current = expr;
    }
  }, [expr]);

  const filteredVars = (variables || []).filter(
    (v) => !suggestionFilter || v.code.toLowerCase().includes(suggestionFilter.toLowerCase()),
  );

  function autoResize(el) {
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = el.scrollHeight + 'px';
  }

  const handleChange = useCallback((e) => {
    const val = e.target.value;
    setText(val);
    autoResize(e.target);

    const pos = e.target.selectionStart;
    setCaretPos(pos);

    const before = val.slice(0, pos);
    const atMatch = before.match(/@([a-z_][a-z0-9_]*)?$/);
    if (atMatch) {
      setSuggestionFilter(atMatch[1] || '');
      setShowSuggestions(true);
    } else {
      setShowSuggestions(false);
    }

    const parsed = parseText(val);
    lastParsedRef.current = parsed;
    onChange(parsed);
  }, [onChange]);

  function handleKeyDown(e) {
    if (e.key === 'Escape') {
      setShowSuggestions(false);
    }
    if (e.key === 'Tab' && showSuggestions && filteredVars.length > 0) {
      e.preventDefault();
      insertVariable(filteredVars[0].code);
    }
  }

  function insertVariable(code) {
    const el = textareaRef.current;
    if (!el) return;

    const before = text.slice(0, caretPos);
    const after = text.slice(caretPos);
    const atIdx = before.lastIndexOf('@');
    const newBefore = before.slice(0, atIdx) + code;
    const newText = newBefore + (after.startsWith(' ') ? after : ' ' + after);

    setText(newText);
    setShowSuggestions(false);

    const parsed = parseText(newText);
    lastParsedRef.current = parsed;
    onChange(parsed);

    requestAnimationFrame(() => {
      const newPos = newBefore.length + 1;
      el.focus();
      el.setSelectionRange(newPos, newPos);
    });
  }

  const varCodes = new Set((variables || []).map((v) => v.code));
  const varMap = Object.fromEntries((variables || []).map((v) => [v.code, v]));
  const tokens = text ? tokenize(text) : [];
  const usedVars = tokens.filter((t) => t.type === 'variable' && varCodes.has(t.value));

  return (
    <div className="relative">
      <textarea
        ref={(el) => {
          textareaRef.current = el;
          autoResize(el);
        }}
        value={text}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        onFocus={(e) => {
          if (e.target.value === '0') e.target.select();
        }}
        onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
        disabled={readOnly}
        placeholder="purchase_price_cny * exchange_rate"
        rows={1}
        spellCheck={false}
        className={cn(
          'w-full resize-none overflow-hidden rounded-lg border border-app-border bg-white px-3 py-2 font-mono text-sm leading-6 text-app-text outline-none transition-colors',
          'focus:border-app-text focus:ring-1 focus:ring-app-text',
          'placeholder:text-app-muted',
          'disabled:cursor-default disabled:bg-transparent disabled:opacity-60',
        )}
      />

      {usedVars.length > 0 && (
        <div className="mt-1.5 flex flex-wrap items-center gap-1">
          {usedVars.map((tok, i) => {
            const v = varMap[tok.value];
            const color = SCOPE_COLORS[v?.scope] || 'bg-gray-100 text-gray-600';
            return (
              <span key={`${tok.value}-${i}`} className={cn('inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-medium', color)}>
                {tok.value}
                {v?.unit && <span className="opacity-50">{v.unit}</span>}
              </span>
            );
          })}
        </div>
      )}

      <div className="mt-1 flex items-center gap-2">
        {!readOnly && (
          <span className="text-[10px] text-app-muted">
            <kbd className="rounded border border-gray-300 bg-gray-100 px-1 py-0.5 font-mono text-[9px]">@</kbd> вставить переменную · операторы: + - * / · функции: min() max() round() if()
          </span>
        )}
      </div>

      {showSuggestions && filteredVars.length > 0 && (
        <div className="absolute left-0 z-30 mt-1 max-h-56 w-80 overflow-y-auto rounded-xl border border-app-border bg-white p-1 shadow-xl">
          {filteredVars.slice(0, 20).map((v) => (
            <button
              key={v.code}
              onMouseDown={(e) => {
                e.preventDefault();
                insertVariable(v.code);
              }}
              className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left transition-colors hover:bg-[#f4f3f1]"
            >
              <code className={cn('shrink-0 rounded px-1.5 py-0.5 text-xs font-medium', SCOPE_COLORS[v.scope] || 'bg-gray-100 text-gray-600')}>
                {v.code}
              </code>
              <span className="truncate text-xs text-app-muted">
                {v.unit} · {SCOPE_LABELS[v.scope] || v.scope}
              </span>
            </button>
          ))}
          <div className="border-t border-gray-100 px-3 py-1.5 text-[10px] text-gray-400">
            <kbd className="rounded border border-gray-200 px-1 font-mono">Tab</kbd> вставить первый
          </div>
        </div>
      )}
    </div>
  );
}

const SCOPE_LABELS = {
  global: 'глобальная',
  supplier: 'поставщик',
  category: 'категория',
  range: 'диапазон',
  product_input: 'ввод товара',
  sku_input: 'SKU',
};

const SCOPE_COLORS = {
  global: 'bg-emerald-100 text-emerald-700',
  supplier: 'bg-blue-100 text-blue-700',
  category: 'bg-purple-100 text-purple-700',
  range: 'bg-orange-100 text-orange-700',
  product_input: 'bg-pink-100 text-pink-700',
  sku_input: 'bg-cyan-100 text-cyan-700',
};

const KNOWN_FNS = new Set(['min', 'max', 'round', 'ceil', 'floor', 'abs', 'if']);
const OPS = new Set(['+', '-', '*', '/']);

function tokenize(text) {
  const tokens = [];
  let i = 0;
  while (i < text.length) {
    if (/\s/.test(text[i])) {
      let ws = '';
      while (i < text.length && /\s/.test(text[i])) { ws += text[i]; i++; }
      tokens.push({ type: 'space', value: ws });
      continue;
    }
    if (OPS.has(text[i])) {
      tokens.push({ type: 'operator', value: text[i] });
      i++;
      continue;
    }
    if (text[i] === '(' || text[i] === ')' || text[i] === ',') {
      tokens.push({ type: 'paren', value: text[i] });
      i++;
      continue;
    }
    if (/\d/.test(text[i]) || (text[i] === '.' && i + 1 < text.length && /\d/.test(text[i + 1]))) {
      let num = '';
      while (i < text.length && /[\d.]/.test(text[i])) { num += text[i]; i++; }
      tokens.push({ type: 'number', value: num });
      continue;
    }
    if (/[a-zA-Z_]/.test(text[i])) {
      let word = '';
      while (i < text.length && /[a-zA-Z0-9_]/.test(text[i])) { word += text[i]; i++; }
      if (KNOWN_FNS.has(word)) {
        tokens.push({ type: 'function', value: word });
      } else {
        tokens.push({ type: 'variable', value: word });
      }
      continue;
    }
    tokens.push({ type: 'other', value: text[i] });
    i++;
  }
  return tokens;
}

function parseText(text) {
  const trimmed = (text || '').trim();
  if (!trimmed) return { const: '0' };

  try {
    const tokens = tokenize(trimmed).filter((t) => t.type !== 'space');
    const result = parseExpr(tokens, 0);
    return result.node;
  } catch {
    if (/^[a-z_][a-z0-9_]*$/.test(trimmed)) return { var: trimmed };
    if (/^-?\d+(\.\d+)?$/.test(trimmed)) return { const: trimmed };
    return { var: trimmed };
  }
}

function parseExpr(tokens, pos) {
  let { node, pos: p } = parseTerm(tokens, pos);

  while (p < tokens.length && (tokens[p].value === '+' || tokens[p].value === '-')) {
    const op = tokens[p].value;
    p++;
    const right = parseTerm(tokens, p);
    node = { op, args: [node, right.node] };
    p = right.pos;
  }

  return { node, pos: p };
}

function parseTerm(tokens, pos) {
  let { node, pos: p } = parseFactor(tokens, pos);

  while (p < tokens.length && (tokens[p].value === '*' || tokens[p].value === '/')) {
    const op = tokens[p].value;
    p++;
    const right = parseFactor(tokens, p);
    node = { op, args: [node, right.node] };
    p = right.pos;
  }

  return { node, pos: p };
}

function parseFactor(tokens, pos) {
  if (pos >= tokens.length) return { node: { const: '0' }, pos };

  const tok = tokens[pos];

  if (tok.type === 'paren' && tok.value === '(') {
    const inner = parseExpr(tokens, pos + 1);
    let p = inner.pos;
    if (p < tokens.length && tokens[p].value === ')') p++;
    return { node: inner.node, pos: p };
  }

  if (tok.type === 'number') {
    return { node: { const: tok.value }, pos: pos + 1 };
  }

  if (tok.type === 'function') {
    let p = pos + 1;
    if (p < tokens.length && tokens[p].value === '(') {
      p++;
      const args = [];
      while (p < tokens.length && tokens[p].value !== ')') {
        if (tokens[p].value === ',') { p++; continue; }
        const arg = parseExpr(tokens, p);
        args.push(arg.node);
        p = arg.pos;
      }
      if (p < tokens.length && tokens[p].value === ')') p++;
      return { node: { fn: tok.value, args }, pos: p };
    }
    return { node: { fn: tok.value, args: [{ const: '0' }] }, pos: p };
  }

  if (tok.type === 'variable') {
    return { node: { var: tok.value }, pos: pos + 1 };
  }

  return { node: { const: '0' }, pos: pos + 1 };
}
