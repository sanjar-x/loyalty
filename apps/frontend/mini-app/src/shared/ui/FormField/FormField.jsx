'use client';

import { useState } from 'react';

import styles from './FormField.module.css';

/**
 * Shared floating-label form field. Sprint 2: renamed from
 * CheckoutFormField — generic, not tied to the checkout domain. Used by
 * checkout (CardSheet/CustomsSheet), recipient-form (RecipientSheet) and
 * any future form.
 *
 * Field owns focus state internally; parent owns value + error.
 *
 * @param {Object} props
 * @param {string} props.label
 * @param {string} props.value
 * @param {(e: React.ChangeEvent<HTMLInputElement>) => void} props.onChange
 * @param {string|null} [props.error]                Required/invalid copy
 * @param {string} [props.type]                      input[type]
 * @param {string} [props.inputMode]
 * @param {number} [props.maxLength]
 * @param {string} [props.autoCapitalize]
 * @param {boolean} [props.spellCheck]
 * @param {React.Ref<HTMLInputElement>} [props.inputRef]
 * @param {React.ReactNode} [props.rightSlot]        Inline icon / select
 * @param {string} [props.className]
 */
export default function FormField({
  label,
  value,
  onChange,
  error,
  type = 'text',
  inputMode,
  maxLength,
  autoCapitalize,
  spellCheck,
  inputRef,
  rightSlot,
  className,
  ...rest
}) {
  const [focused, setFocused] = useState(false);
  const isFloating = focused || Boolean(value);
  const hasError = Boolean(error);

  return (
    <div className={styles.fieldContainer}>
      <div
        className={`${styles.fieldShell} ${focused ? styles.fieldShellFocused : ''} ${hasError ? styles.fieldShellError : ''} ${className || ''}`}
      >
        <label
          className={`${styles.label} ${isFloating ? styles.labelFloating : ''} ${hasError ? styles.labelError : ''}`}
        >
          {label}
        </label>
        <input
          ref={inputRef}
          type={type}
          inputMode={inputMode}
          maxLength={maxLength}
          autoCapitalize={autoCapitalize}
          spellCheck={spellCheck}
          value={value}
          onChange={onChange}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          className={`${styles.input} ${hasError ? styles.inputError : ''}`}
          {...rest}
        />
        {rightSlot ? <div className={styles.rightSlot}>{rightSlot}</div> : null}
      </div>
      {error ? <div className={styles.fieldError}>{error}</div> : null}
    </div>
  );
}
