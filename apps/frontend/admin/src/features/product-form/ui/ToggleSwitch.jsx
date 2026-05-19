'use client';

import { useState } from 'react';
import { cn } from '@/shared/lib/utils';
import styles from './styles/productForm.module.css';

export default function ToggleSwitch({
  ariaLabel,
  initialChecked = false,
  checked,
  onChange,
  disabled = false,
}) {
  const [internalChecked, setInternalChecked] = useState(initialChecked);
  const isControlled = checked !== undefined;
  const resolvedChecked = isControlled ? checked : internalChecked;

  function handleClick() {
    if (disabled) return;
    const nextChecked = !resolvedChecked;

    if (!isControlled) {
      setInternalChecked(nextChecked);
    }

    onChange?.(nextChecked);
  }

  return (
    <button
      type="button"
      className={cn(styles.toggle, resolvedChecked && styles.toggleActive)}
      aria-label={ariaLabel}
      aria-pressed={resolvedChecked}
      aria-disabled={disabled}
      onClick={handleClick}
      style={disabled ? { opacity: 0.5, cursor: 'not-allowed' } : undefined}
    >
      <span className={styles.toggleThumb} />
    </button>
  );
}
