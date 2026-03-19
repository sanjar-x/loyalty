'use client';

import { useState } from 'react';
import { cn } from '@/lib/utils';
import styles from './page.module.css';

export default function ToggleSwitch({
  ariaLabel,
  initialChecked = false,
  checked,
  onChange,
}) {
  const [internalChecked, setInternalChecked] = useState(initialChecked);
  const isControlled = checked !== undefined;
  const resolvedChecked = isControlled ? checked : internalChecked;

  function handleClick() {
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
      onClick={handleClick}
    >
      <span className={styles.toggleThumb} />
    </button>
  );
}
