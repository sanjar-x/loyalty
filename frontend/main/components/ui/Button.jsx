import { cn } from "@/lib/format/cn";

import styles from "./Button.module.css";

export default function Button({
  children,
  variant = "primary",
  size = "md",
  loading = false,
  disabled = false,
  className = "",
  iconLeft = null,
  iconRight = null,
  ...props
}) {
  const isDisabled = disabled || loading;

  return (
    <button
      {...props}
      disabled={isDisabled}
      className={cn(
        styles.btn,
        styles[variant],
        styles[size],
        isDisabled && styles.disabled,
        className,
      )}
    >
      {loading && <span className={styles.loading}>…</span>}

      {iconLeft && <span className={styles.iconLeft}>{iconLeft}</span>}

      {children}

      {iconRight && <span className={styles.iconRight}>{iconRight}</span>}
    </button>
  );
}
