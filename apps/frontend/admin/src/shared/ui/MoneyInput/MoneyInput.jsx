'use client';

import { useEffect, useState } from 'react';
import { cn } from '@/shared/lib/utils';

const DEFAULT_CURRENCIES = ['RUB'];

/**
 * Controlled money input — pair of <input type="text"> for the integer amount
 * and a <select>/<span> for the currency code. Emits the canonical shape
 * `{ amount: number, currency: string } | null` consumed by the catalog API
 * builders.
 *
 * Why amount is "user-facing units" (e.g. rubles, not kopecks): the form keeps
 * mental model 1:1 with what the user types. Conversion to the backend
 * smallest-unit (×100) happens once, at the API builder layer.
 *
 * Why local state for currency: while the amount input is empty we emit
 * `null` (so the caller can detect "field unset") — but we still need to
 * remember the user's currency choice across the empty/non-empty transition,
 * otherwise a stray backspace would silently reset the dropdown.
 */
export function MoneyInput({
  value,
  onChange,
  currencies = DEFAULT_CURRENCIES,
  required = false,
  label,
  helperText,
  disabled = false,
  placeholder = '0',
  ariaLabel,
  className,
  inputClassName,
  hasError = false,
  errorText,
  id,
}) {
  const fallbackCurrency = currencies[0] ?? 'RUB';
  const currencyChoosable = currencies.length > 1;
  // Locked mode (single allowed currency) bypasses the localCurrency state
  // entirely — the parent has already decided which currency this input
  // emits and what the badge should read. This handles two practical
  // cases: (1) a value rehydrated from the server with a currency that no
  // longer matches the current rule (legacy data), and (2) the parent
  // flipping currencies dynamically (e.g. supplier swap → purchaseCurrency).
  const lockedCurrency = currencyChoosable ? null : fallbackCurrency;
  const [localCurrency, setLocalCurrency] = useState(
    value?.currency ?? fallbackCurrency,
  );

  // Sync local currency when the parent rehydrates with a different value
  // (e.g. edit mode: form receives a money object from the server snapshot).
  useEffect(() => {
    if (lockedCurrency) return;
    if (value?.currency && value.currency !== localCurrency) {
      setLocalCurrency(value.currency);
    }
  }, [value?.currency, localCurrency, lockedCurrency]);

  // The currency we actually emit / display. In locked mode the parent
  // wins; in choosable mode the user's selection (or hydrated value) wins.
  const effectiveCurrency = lockedCurrency ?? localCurrency;

  const amountStr =
    value?.amount != null && value.amount !== '' ? String(value.amount) : '';

  function handleAmountChange(event) {
    const next = event.target.value.replace(/[^0-9]/g, '');
    if (next === '') {
      onChange(null);
      return;
    }
    onChange({ amount: parseInt(next, 10) || 0, currency: effectiveCurrency });
  }

  function handleCurrencyChange(event) {
    const next = event.target.value;
    setLocalCurrency(next);
    if (value && value.amount != null) {
      onChange({ amount: value.amount, currency: next });
    }
  }
  const inputId =
    id ?? (label ? `money-input-${label.replace(/\s+/g, '-')}` : undefined);

  return (
    <div className={cn('flex flex-col gap-1', className)}>
      {label && (
        <label htmlFor={inputId} className="text-app-muted text-xs font-medium">
          {label}
          {required && <span className="text-app-danger ml-1">*</span>}
        </label>
      )}
      <div
        className={cn(
          'border-app-border bg-app-panel flex items-stretch overflow-hidden rounded-lg border transition-colors',
          'focus-within:border-app-text',
          hasError && 'border-app-danger focus-within:border-app-danger',
          disabled && 'opacity-60',
        )}
      >
        <input
          id={inputId}
          type="text"
          inputMode="numeric"
          value={amountStr}
          onChange={handleAmountChange}
          placeholder={placeholder}
          disabled={disabled}
          aria-label={ariaLabel ?? label}
          aria-invalid={hasError || undefined}
          className={cn(
            'text-app-text min-w-0 flex-1 bg-transparent px-3 py-2 text-sm outline-none',
            inputClassName,
          )}
        />
        {currencyChoosable ? (
          <select
            value={localCurrency}
            onChange={handleCurrencyChange}
            disabled={disabled}
            aria-label={`${ariaLabel ?? label ?? 'Сумма'} — валюта`}
            className="border-app-border text-app-text bg-app-card cursor-pointer border-l px-3 py-2 text-sm outline-none"
          >
            {currencies.map((currency) => (
              <option key={currency} value={currency}>
                {currency}
              </option>
            ))}
          </select>
        ) : (
          <span
            className="border-app-border text-app-muted bg-app-card flex items-center border-l px-3 py-2 text-sm"
            aria-hidden="true"
          >
            {effectiveCurrency}
          </span>
        )}
      </div>
      {helperText && !errorText && (
        <p className="text-app-muted text-xs">{helperText}</p>
      )}
      {errorText && hasError && (
        <p className="text-app-danger text-xs" role="alert">
          {errorText}
        </p>
      )}
    </div>
  );
}
