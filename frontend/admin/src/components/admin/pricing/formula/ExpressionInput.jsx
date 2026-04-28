'use client';

import { useState, useRef } from 'react';
import { cn } from '@/lib/utils';

export function ExpressionInput({ value, onChange, variables, readOnly, placeholder }) {
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [cursorWord, setCursorWord] = useState('');
  const inputRef = useRef(null);

  const filteredVars = (variables || []).filter(
    (v) => !cursorWord || v.code.includes(cursorWord),
  );

  function handleChange(e) {
    const text = e.target.value;
    const parsed = parseExpression(text);
    onChange(text, parsed);

    const word = getCurrentWord(text, e.target.selectionStart);
    setCursorWord(word);
    setShowSuggestions(word.length > 0 && filteredVars.length > 0);
  }

  function handleKeyDown(e) {
    if (e.key === '@') {
      setCursorWord('');
      setShowSuggestions(true);
    }
    if (e.key === 'Escape') {
      setShowSuggestions(false);
    }
  }

  function insertVariable(code) {
    const input = inputRef.current;
    if (!input) return;

    const pos = input.selectionStart;
    const text = value || '';
    const wordStart = findWordStart(text, pos);
    const newText = text.slice(0, wordStart) + code + text.slice(pos);
    const parsed = parseExpression(newText);
    onChange(newText, parsed);
    setShowSuggestions(false);

    requestAnimationFrame(() => {
      const newPos = wordStart + code.length;
      input.focus();
      input.setSelectionRange(newPos, newPos);
    });
  }

  return (
    <div className="relative">
      <input
        ref={inputRef}
        type="text"
        value={value ?? ''}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        onFocus={() => {
          if (cursorWord) setShowSuggestions(true);
        }}
        onBlur={() => {
          setTimeout(() => setShowSuggestions(false), 200);
        }}
        disabled={readOnly}
        placeholder={placeholder}
        className={cn(
          'h-9 w-full rounded-md border border-transparent bg-transparent px-2 font-mono text-sm text-app-text outline-none transition-colors',
          'focus:border-app-border focus:bg-white',
          'disabled:cursor-default',
        )}
      />

      {showSuggestions && filteredVars.length > 0 && (
        <div className="absolute top-full left-0 z-20 mt-1 max-h-48 w-72 overflow-y-auto rounded-xl border border-app-border bg-white p-1 shadow-lg">
          {filteredVars.slice(0, 15).map((v) => (
            <button
              key={v.code}
              onMouseDown={(e) => {
                e.preventDefault();
                insertVariable(v.code);
              }}
              className="flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-left transition-colors hover:bg-[#f4f3f1]"
            >
              <code className="text-xs font-medium text-app-text">{v.code}</code>
              <span className="truncate text-xs text-app-muted">
                {v.unit} · {v.scope}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function getCurrentWord(text, pos) {
  const before = text.slice(0, pos);
  const match = before.match(/[a-z_][a-z0-9_]*$/);
  return match ? match[0] : '';
}

function findWordStart(text, pos) {
  const before = text.slice(0, pos);
  const match = before.match(/[a-z_][a-z0-9_]*$/);
  return match ? pos - match[0].length : pos;
}

function parseExpression(text) {
  if (!text || !text.trim()) return { const: '0' };

  const trimmed = text.trim();

  if (/^-?\d+(\.\d+)?$/.test(trimmed)) {
    return { const: trimmed };
  }

  if (/^[a-z_][a-z0-9_]*$/.test(trimmed)) {
    return { var: trimmed };
  }

  const binaryMatch = trimmed.match(/^(.+?)\s*([+\-*/])\s*(.+)$/);
  if (binaryMatch) {
    const [, left, op, right] = binaryMatch;
    return {
      op,
      args: [parseExpression(left), parseExpression(right)],
    };
  }

  const fnMatch = trimmed.match(/^([a-z_]+)\((.+)\)$/);
  if (fnMatch) {
    const [, fn, argsStr] = fnMatch;
    const args = splitArgs(argsStr).map(parseExpression);
    return { fn, args };
  }

  return { var: trimmed };
}

function splitArgs(str) {
  const args = [];
  let depth = 0;
  let current = '';
  for (const ch of str) {
    if (ch === '(') depth++;
    if (ch === ')') depth--;
    if (ch === ',' && depth === 0) {
      args.push(current.trim());
      current = '';
    } else {
      current += ch;
    }
  }
  if (current.trim()) args.push(current.trim());
  return args;
}
