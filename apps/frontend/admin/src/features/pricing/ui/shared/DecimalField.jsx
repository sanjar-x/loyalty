'use client';

import { cn } from '@/shared/lib/utils';

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
        <label className="text-app-muted text-xs font-medium">{label}</label>
      )}
      <input
        type="text"
        inputMode="decimal"
        value={value ?? ''}
        onChange={handleChange}
        placeholder={placeholder}
        disabled={disabled}
        className={cn(
          'text-app-text h-10 rounded-lg border bg-white px-3 text-sm transition-colors outline-none',
          'focus:border-app-text focus:ring-app-text focus:ring-1',
          'disabled:bg-app-card disabled:text-app-muted disabled:cursor-not-allowed',
          error ? 'border-red-300' : 'border-app-border',
        )}
      />
      {error && <p className="text-xs text-red-500">{error}</p>}
    </div>
  );
}
