'use client';

import {
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from 'react';

import { cn } from '@/shared/lib/utils';

/**
 * Two-layer formula editor:
 *
 * - **What the user types/sees** are human-readable display strings,
 *   e.g. "Закупочная цена (CNY) * Курс CNY/RUB". Display strings may contain
 *   spaces, parentheses, slashes, Cyrillic — anything that comes from
 *   `Variable.name.ru` or a binding's `label`.
 * - **What is sent to the backend** are machine codes (snake_case identifiers
 *   like `purchase_price_cny`) inside the AST. The backend never sees a
 *   display string.
 *
 * Translation happens in two functions:
 * - `tokenize` does a *greedy longest-match* against the registered display
 *   names before falling back to operators/numbers/words. That's why a
 *   multi-word display like "Закупочная цена (CNY)" is recognised as a single
 *   token instead of being shredded into ["Закупочная", "цена", "(", "CNY", ")"].
 * - `displayToExpr` walks the resolved tokens. If any non-display word is
 *   left unresolved, the parse is rejected (returns null) so the AST never
 *   carries a half-typed Russian fragment up to the backend.
 */
export function ExpressionBuilder({
  expr,
  onChange,
  variables,
  bindings,
  currentIndex,
  readOnly,
}) {
  const lookups = useMemo(
    () => buildLookups(variables, bindings, currentIndex),
    [variables, bindings, currentIndex],
  );

  const [text, setText] = useState(() => exprToDisplay(expr, lookups));
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestionFilter, setSuggestionFilter] = useState('');
  const [caretPos, setCaretPos] = useState(0);
  const [activeIndex, setActiveIndex] = useState(null);
  const textareaRef = useRef(null);
  const lastParsedRef = useRef(expr);
  const listboxId = useId();
  const optionId = (i) => `${listboxId}-option-${i}`;

  // Re-sync the textarea only when the AST changes from outside (e.g. parent
  // restored a draft) — local edits round-trip through `lastParsedRef`.
  useEffect(() => {
    const incoming = JSON.stringify(expr);
    const last = JSON.stringify(lastParsedRef.current);
    if (incoming !== last) {
      setText(exprToDisplay(expr, lookups));
      lastParsedRef.current = expr;
    }
  }, [expr, lookups]);

  const suggestions = useMemo(() => {
    const items = [];
    for (const v of variables || []) {
      const display = v.name?.ru || v.name?.en || v.code;
      items.push({
        type: 'var',
        code: v.code,
        display,
        unit: v.unit,
        scope: v.scope,
      });
    }
    for (const b of lookups.refBindings) {
      items.push({
        type: 'ref',
        code: b.name,
        display: b.label || b.name,
        unit: null,
        scope: 'binding',
      });
    }
    if (!suggestionFilter) return items;
    const q = suggestionFilter.toLowerCase();
    return items.filter(
      (it) =>
        it.display.toLowerCase().includes(q) ||
        it.code.toLowerCase().includes(q),
    );
  }, [variables, lookups.refBindings, suggestionFilter]);

  function autoResize(el) {
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = el.scrollHeight + 'px';
  }

  const handleChange = useCallback(
    (e) => {
      const val = e.target.value;
      setText(val);
      autoResize(e.target);

      const pos = e.target.selectionStart;
      setCaretPos(pos);

      // The @-mention filter accepts spaces so users can search by full
      // multi-word names (e.g. "@Закупочная цен" → matches "Закупочная цена…").
      const before = val.slice(0, pos);
      const atMatch = before.match(/@([^@\n]*)$/);
      if (atMatch) {
        setSuggestionFilter(atMatch[1]);
        setShowSuggestions(true);
      } else {
        setShowSuggestions(false);
      }

      const parsed = displayToExpr(val, lookups);
      if (parsed !== null) {
        lastParsedRef.current = parsed;
        onChange(parsed);
      }
    },
    [onChange, lookups],
  );

  // FA-406d: WAI-ARIA APG combobox active-descendant lifecycle.
  //   - Reset to null whenever the popup closes.
  //   - Clamp on suggestion-array resizing (e.g. user types more chars to
  //     narrow the filter): if the prior active index is now past the end,
  //     snap it to the last valid index. Preserves user's navigation
  //     position across narrowing rather than resetting blindly.
  useEffect(() => {
    if (!showSuggestions) setActiveIndex(null);
  }, [showSuggestions]);

  useEffect(() => {
    setActiveIndex((prev) => {
      if (prev === null) return null;
      if (suggestions.length === 0) return null;
      if (prev >= suggestions.length) return suggestions.length - 1;
      return prev;
    });
  }, [suggestions.length]);

  function handleKeyDown(e) {
    if (e.key === 'Escape') {
      setShowSuggestions(false);
      setActiveIndex(null);
      return;
    }
    if (e.key === 'ArrowDown') {
      if (!showSuggestions || suggestions.length === 0) return;
      e.preventDefault();
      setActiveIndex((prev) =>
        prev === null ? 0 : (prev + 1) % suggestions.length,
      );
      return;
    }
    if (e.key === 'ArrowUp') {
      if (!showSuggestions || suggestions.length === 0) return;
      e.preventDefault();
      setActiveIndex((prev) =>
        prev === null
          ? suggestions.length - 1
          : (prev - 1 + suggestions.length) % suggestions.length,
      );
      return;
    }
    if (e.key === 'Enter') {
      // Per APG: Enter accepts only when an option has been activated via
      // arrow keys. Without active state, fall through to the textarea's
      // native Enter (newline).
      if (showSuggestions && activeIndex !== null && suggestions[activeIndex]) {
        e.preventDefault();
        insertSuggestion(suggestions[activeIndex]);
      }
      return;
    }
    if (e.key === 'Tab' && showSuggestions && suggestions.length > 0) {
      e.preventDefault();
      // Tab inserts the active option when one exists (synchronizes with
      // the new arrow-nav contract); otherwise falls back to the first
      // suggestion (preserves the FA-401 "power-user shortcut" behavior).
      const target =
        activeIndex !== null ? suggestions[activeIndex] : suggestions[0];
      insertSuggestion(target);
    }
  }

  function insertSuggestion(item) {
    const el = textareaRef.current;
    if (!el) return;

    const before = text.slice(0, caretPos);
    const after = text.slice(caretPos);

    // Trim back to the start of the current @-mention if present, otherwise
    // splice at the caret. The mention may contain spaces — strip everything
    // from the last `@` to the caret.
    const atIdx = before.lastIndexOf('@');
    const wordStart = atIdx >= 0 ? atIdx : caretPos;

    // Insert the **display name** so the user sees a readable formula. The
    // tokenizer will resolve it back to `item.code` on every re-parse, and
    // the AST stays clean (snake_case codes only).
    const insertText = item.display;
    const needsTrailingSpace = !after.startsWith(' ') && !after.startsWith(')');
    const tail = needsTrailingSpace ? ' ' + after : after;
    const newBefore = before.slice(0, wordStart) + insertText;
    const newText = newBefore + tail;

    setText(newText);
    setShowSuggestions(false);

    const parsed = displayToExpr(newText, lookups);
    if (parsed !== null) {
      lastParsedRef.current = parsed;
      onChange(parsed);
    }

    requestAnimationFrame(() => {
      const newPos = newBefore.length + (needsTrailingSpace ? 1 : 0);
      el.focus();
      el.setSelectionRange(newPos, newPos);
    });
  }

  // Recognised tokens drive the chip strip below the textarea — each chip
  // shows the display name with the machine code in its tooltip.
  const tokens = text ? tokenize(text, lookups.sortedDisplays) : [];
  const recognizedTokens = tokens.filter(
    (t) => t.type === 'var_resolved' || t.type === 'ref_resolved',
  );

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
        placeholder="Закупочная цена (CNY) * Курс CNY/RUB"
        rows={1}
        spellCheck={false}
        role="combobox"
        aria-haspopup="listbox"
        aria-expanded={showSuggestions}
        aria-controls={listboxId}
        aria-autocomplete="list"
        aria-activedescendant={
          activeIndex !== null ? optionId(activeIndex) : undefined
        }
        className={cn(
          'border-app-border text-app-text w-full resize-none overflow-hidden rounded-lg border bg-white px-3 py-2 text-sm leading-6 transition-colors outline-none',
          'focus:border-app-text focus:ring-app-text focus:ring-1',
          'placeholder:text-app-muted',
          'disabled:cursor-default disabled:bg-transparent disabled:opacity-60',
        )}
      />

      {recognizedTokens.length > 0 && (
        <div className="mt-1.5 flex flex-wrap items-center gap-1">
          {recognizedTokens.map((tok, i) => {
            const isRef = tok.type === 'ref_resolved';
            const v = isRef ? null : lookups.codeToVar.get(tok.code);
            const color = isRef
              ? 'bg-violet-100 text-violet-700'
              : SCOPE_COLORS[v?.scope] || 'bg-gray-100 text-gray-600';
            return (
              <span
                key={`${tok.code}-${i}`}
                className={cn(
                  'inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px] font-medium',
                  color,
                )}
                title={tok.code}
              >
                <span>{tok.value}</span>
                <code className="font-mono opacity-60">{tok.code}</code>
                {v?.unit && <span className="opacity-50">{v.unit}</span>}
                {isRef && <span className="opacity-50">↑ref</span>}
              </span>
            );
          })}
        </div>
      )}

      <div className="mt-1 flex items-center gap-2">
        {!readOnly && (
          <span className="text-app-muted text-[10px]">
            <kbd className="rounded border border-gray-300 bg-gray-100 px-1 py-0.5 font-mono text-[9px]">
              @
            </kbd>{' '}
            вставить переменную или ссылку на строку
          </span>
        )}
      </div>

      {showSuggestions && suggestions.length > 0 && (
        <div
          id={listboxId}
          role="listbox"
          className="border-app-border absolute left-0 z-30 mt-1 max-h-56 w-96 overflow-y-auto rounded-xl border bg-white p-1 shadow-xl"
        >
          {suggestions.slice(0, 20).map((item, i) => {
            const isActive = i === activeIndex;
            return (
              <button
                key={`${item.code}-${i}`}
                id={optionId(i)}
                type="button"
                role="option"
                aria-selected={isActive}
                onMouseDown={(e) => {
                  e.preventDefault();
                  insertSuggestion(item);
                }}
                onMouseEnter={() => setActiveIndex(i)}
                className={cn(
                  'flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left transition-colors',
                  isActive ? 'bg-app-card' : 'hover:bg-app-card',
                )}
                title={item.code}
              >
                <span
                  className={cn(
                    'shrink-0 rounded px-1.5 py-0.5 text-xs font-medium',
                    item.type === 'ref'
                      ? 'bg-violet-100 text-violet-700'
                      : SCOPE_COLORS[item.scope] || 'bg-gray-100 text-gray-600',
                  )}
                >
                  {item.display}
                </span>
                <code className="text-app-muted shrink-0 font-mono text-[11px]">
                  {item.code}
                </code>
                <span className="text-app-muted ml-auto shrink-0 text-[11px]">
                  {item.type === 'ref'
                    ? '↑ строка'
                    : `${item.unit || ''} · ${SCOPE_LABELS[item.scope] || item.scope}`}
                </span>
              </button>
            );
          })}
          <div className="border-t border-gray-100 px-3 py-1.5 text-[10px] text-gray-400">
            <kbd className="rounded border border-gray-200 px-1 font-mono">
              ↑↓
            </kbd>{' '}
            выбрать ·{' '}
            <kbd className="rounded border border-gray-200 px-1 font-mono">
              Enter
            </kbd>{' '}
            вставить ·{' '}
            <kbd className="rounded border border-gray-200 px-1 font-mono">
              Tab
            </kbd>{' '}
            первый
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

function buildLookups(variables, bindings, currentIndex) {
  const codeToVar = new Map();
  const codeToDisplay = new Map();
  const displayToCode = new Map();
  const refNames = new Set();
  const refBindings = [];

  for (const v of variables || []) {
    codeToVar.set(v.code, v);
    const display = v.name?.ru || v.name?.en || v.code;
    if (!codeToDisplay.has(v.code)) codeToDisplay.set(v.code, display);
    if (!displayToCode.has(display)) {
      displayToCode.set(display, { code: v.code, isRef: false });
    }
  }

  for (let i = 0; i < (bindings || []).length; i++) {
    if (i >= currentIndex) break;
    const b = bindings[i];
    if (!b.name) continue;
    refNames.add(b.name);
    refBindings.push(b);
    const display = b.label || b.name;
    if (!codeToDisplay.has(b.name)) codeToDisplay.set(b.name, display);
    if (!displayToCode.has(display)) {
      displayToCode.set(display, { code: b.name, isRef: true });
    }
  }

  // Greedy longest-match: try long phrases before single words so we never
  // end up tokenising "Закупочная цена" into "Закупочная" + "цена".
  const sortedDisplays = Array.from(displayToCode.entries())
    .map(([display, info]) => ({ display, ...info }))
    .sort((a, b) => b.display.length - a.display.length);

  return {
    codeToVar,
    codeToDisplay,
    displayToCode,
    refNames,
    refBindings,
    sortedDisplays,
  };
}

function exprToDisplay(expr, lookups) {
  if (!expr || typeof expr !== 'object') return '';
  if ('const' in expr) return String(expr.const);
  if ('var' in expr) return lookups.codeToDisplay.get(expr.var) ?? expr.var;
  if ('ref' in expr) return lookups.codeToDisplay.get(expr.ref) ?? expr.ref;
  if ('op' in expr && Array.isArray(expr.args)) {
    return expr.args.map((a) => exprToDisplay(a, lookups)).join(` ${expr.op} `);
  }
  if ('fn' in expr && Array.isArray(expr.args)) {
    return `${expr.fn}(${expr.args.map((a) => exprToDisplay(a, lookups)).join(', ')})`;
  }
  return JSON.stringify(expr);
}

function displayToExpr(text, lookups) {
  const trimmed = (text || '').trim();
  if (!trimmed) return { const: '0' };

  const tokens = tokenize(trimmed, lookups.sortedDisplays).filter(
    (t) => t.type !== 'space',
  );

  // If any plain word remains unresolved (user is mid-typing a name without
  // having picked it from the suggestion list), bail out and keep the
  // previous valid AST. Otherwise we'd send a half-typed Russian fragment
  // to the backend as `{var:"Закупочная"}`.
  for (const t of tokens) {
    if (t.type === 'word' || t.type === 'other') return null;
  }

  try {
    return parseExpr(tokens, 0).node;
  } catch {
    return null;
  }
}

const KNOWN_FNS = new Set([
  'min',
  'max',
  'round',
  'ceil',
  'floor',
  'abs',
  'if',
]);
const OPS = new Set(['+', '-', '*', '/']);
// Identifiers in raw text are ASCII-only (snake_case). Multi-word display
// names with Cyrillic + spaces + parens are not parsed here — they are
// captured upstream by the greedy display matcher in `tokenize`.
const IDENT_HEAD = /[A-Za-z_]/;
const IDENT_TAIL = /[A-Za-z0-9_]/;

function tokenize(text, sortedDisplays) {
  const tokens = [];
  let i = 0;
  while (i < text.length) {
    if (/\s/.test(text[i])) {
      let ws = '';
      while (i < text.length && /\s/.test(text[i])) {
        ws += text[i];
        i++;
      }
      tokens.push({ type: 'space', value: ws });
      continue;
    }

    // 1) Greedy match against registered display names. Longest-first ensures
    // "Курс CNY/RUB" wins over a shorter prefix, and "Закупочная цена (CNY)"
    // is captured as ONE token instead of being shredded by the punctuation
    // rules below.
    let matched = null;
    if (sortedDisplays) {
      for (const d of sortedDisplays) {
        if (d.display.length === 0) continue;
        if (text.startsWith(d.display, i)) {
          // Don't match in the middle of a longer ASCII identifier
          // ("price_cnyfoo" should not match a display "price_cny").
          const after = text[i + d.display.length];
          const lastCharIsIdent = IDENT_TAIL.test(
            d.display[d.display.length - 1],
          );
          const afterContinues = after && IDENT_TAIL.test(after);
          if (!lastCharIsIdent || !afterContinues) {
            matched = d;
            break;
          }
        }
      }
    }
    if (matched) {
      tokens.push({
        type: matched.isRef ? 'ref_resolved' : 'var_resolved',
        value: matched.display,
        code: matched.code,
      });
      i += matched.display.length;
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
    if (
      /\d/.test(text[i]) ||
      (text[i] === '.' && i + 1 < text.length && /\d/.test(text[i + 1]))
    ) {
      let num = '';
      while (i < text.length && /[\d.]/.test(text[i])) {
        num += text[i];
        i++;
      }
      tokens.push({ type: 'number', value: num });
      continue;
    }
    if (IDENT_HEAD.test(text[i])) {
      let word = '';
      while (i < text.length && IDENT_TAIL.test(text[i])) {
        word += text[i];
        i++;
      }
      if (KNOWN_FNS.has(word)) {
        tokens.push({ type: 'function', value: word });
      } else {
        tokens.push({ type: 'word', value: word });
      }
      continue;
    }
    // Anything else (unmatched Cyrillic, punctuation we don't grammar) — emit
    // 'other' so `displayToExpr` can detect a half-typed name and refuse.
    tokens.push({ type: 'other', value: text[i] });
    i++;
  }
  return tokens;
}

function parseExpr(tokens, pos) {
  let { node, pos: p } = parseTerm(tokens, pos);
  while (
    p < tokens.length &&
    (tokens[p].value === '+' || tokens[p].value === '-')
  ) {
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
  while (
    p < tokens.length &&
    (tokens[p].value === '*' || tokens[p].value === '/')
  ) {
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
  if (tok.type === 'number')
    return { node: { const: tok.value }, pos: pos + 1 };
  if (tok.type === 'ref_resolved')
    return { node: { ref: tok.code }, pos: pos + 1 };
  if (tok.type === 'var_resolved')
    return { node: { var: tok.code }, pos: pos + 1 };
  if (tok.type === 'function') {
    let p = pos + 1;
    if (p < tokens.length && tokens[p].value === '(') {
      p++;
      const args = [];
      while (p < tokens.length && tokens[p].value !== ')') {
        if (tokens[p].value === ',') {
          p++;
          continue;
        }
        const arg = parseExpr(tokens, p);
        args.push(arg.node);
        p = arg.pos;
      }
      if (p < tokens.length) p++;
      return { node: { fn: tok.value, args }, pos: p };
    }
    return { node: { fn: tok.value, args: [{ const: '0' }] }, pos: p };
  }
  // Plain ASCII identifier that didn't resolve — refuse to absorb. Caller
  // (`displayToExpr`) already filtered these out, but keep the safety net.
  return { node: { const: '0' }, pos: pos + 1 };
}
