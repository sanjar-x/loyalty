'use client';

import { useId, useState } from 'react';
import EyeIcon from '@/assets/icons/eye.svg';
import EyeOffIcon from '@/assets/icons/eye-off.svg';
import { cn } from '@/shared/lib/utils';
import { Checkbox } from '@/shared/ui/Checkbox';

// Shared input shell used by every control in the provider form.
export const INPUT_CLASS =
  'border-app-border focus:border-app-text-dark w-full rounded-lg border px-3 py-2 text-sm transition-colors outline-none disabled:bg-app-card disabled:cursor-not-allowed';

/**
 * One labelled form control. A single component covers every field type the
 * provider form needs — keeps the call sites declarative and the markup
 * (label / hint / error / aria wiring) consistent.
 *
 *   type ∈ text | password | number | select | textarea | stringList
 *
 * `onChange` receives the raw string value (not the event).
 */
export function FormField({
  label,
  type = 'text',
  value,
  onChange,
  options,
  rows = 4,
  placeholder,
  hint,
  error,
  required = false,
  unit,
  mono = false,
  disabled = false,
}) {
  const id = useId();
  const [revealed, setRevealed] = useState(false);
  const describedBy =
    [hint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(' ') ||
    undefined;
  const ariaInvalid = error ? true : undefined;

  let control;
  if (type === 'select') {
    control = (
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled}
        className={INPUT_CLASS}
        aria-describedby={describedBy}
        aria-invalid={ariaInvalid}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    );
  } else if (type === 'textarea' || type === 'stringList') {
    control = (
      <textarea
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={disabled}
        rows={rows}
        placeholder={placeholder}
        spellCheck={false}
        className={cn(INPUT_CLASS, mono && 'font-mono')}
        aria-describedby={describedBy}
        aria-invalid={ariaInvalid}
      />
    );
  } else {
    const isPassword = type === 'password';
    control = (
      <div className="relative">
        <input
          id={id}
          type={isPassword && !revealed ? 'password' : 'text'}
          inputMode={type === 'number' ? 'decimal' : undefined}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          disabled={disabled}
          placeholder={placeholder}
          autoComplete="off"
          className={cn(
            INPUT_CLASS,
            (isPassword || unit) && 'pr-10',
            mono && 'font-mono',
          )}
          aria-describedby={describedBy}
          aria-invalid={ariaInvalid}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setRevealed((prev) => !prev)}
            aria-label={revealed ? 'Скрыть значение' : 'Показать значение'}
            className="text-app-muted hover:text-app-text-dark absolute top-1/2 right-2.5 -translate-y-1/2"
          >
            {revealed ? (
              <EyeOffIcon className="h-4 w-4" />
            ) : (
              <EyeIcon className="h-4 w-4" />
            )}
          </button>
        )}
        {!isPassword && unit && (
          <span className="text-app-muted pointer-events-none absolute top-1/2 right-3 -translate-y-1/2 text-xs">
            {unit}
          </span>
        )}
      </div>
    );
  }

  return (
    <div>
      <label
        htmlFor={id}
        className="text-app-text-dark mb-1 block text-sm font-medium"
      >
        {label}
        {required && (
          <span className="text-app-danger" aria-hidden="true">
            {' '}
            *
          </span>
        )}
      </label>
      {control}
      {hint && !error && (
        <p id={`${id}-hint`} className="text-app-muted mt-1 text-xs">
          {hint}
        </p>
      )}
      {error && (
        <p
          id={`${id}-error`}
          role="alert"
          className="text-app-danger mt-1 text-xs"
        >
          {error}
        </p>
      )}
    </div>
  );
}

/** Checkbox with an inline label + optional helper line. */
export function CheckboxRow({
  label,
  hint,
  checked,
  onChange,
  disabled = false,
}) {
  return (
    <label
      className={cn(
        'flex items-start gap-2.5',
        disabled ? 'cursor-not-allowed' : 'cursor-pointer',
      )}
    >
      <Checkbox
        checked={checked}
        onChange={onChange}
        disabled={disabled}
        className="mt-0.5"
      />
      <span>
        <span className="text-app-text-dark block text-sm font-medium">
          {label}
        </span>
        {hint && <span className="text-app-muted block text-xs">{hint}</span>}
      </span>
    </label>
  );
}
