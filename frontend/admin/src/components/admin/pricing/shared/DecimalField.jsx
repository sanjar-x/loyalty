'use client';

import { cn } from '@/lib/utils';

const DECIMAL_REGEX = /^-?\d*\.?\d*$/;

export function DecimalField({
  label,
  value,
  onChange,
  placeholder,
  disabled,
  error,
  className,
}) {
  function handleChange(e) {
    const raw = e.target.value;
    if (raw === '' || raw === '-' || DECIMAL_REGEX.test(raw)) {
      onChange(raw);
    }
  }

  return (
    <div className={cn('flex flex-col gap-1', className)}>
      {label && (
        <label className="text-xs font-medium text-app-muted">{label}</label>
      )}
      <input
        type="text"
        inputMode="decimal"
        value={value ?? ''}
        onChange={handleChange}
        placeholder={placeholder}
        disabled={disabled}
        className={cn(
          'h-10 rounded-lg border bg-white px-3 text-sm text-app-text outline-none transition-colors',
          'focus:border-app-text focus:ring-1 focus:ring-app-text',
          'disabled:cursor-not-allowed disabled:bg-[#f4f3f1] disabled:text-app-muted',
          error ? 'border-red-300' : 'border-app-border',
        )}
      />
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}
