"use client";
import React from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";

import styles from "./SearchBar.module.css";

interface SearchBarProps {
  isSearchActivated?: boolean;
  isSearchClear?: () => void;
  navigateOnFocusTo?: string;
  readOnly?: boolean;
  autoFocus?: boolean;
  showIcon?: boolean;
  actionLabel?: string;
  actionAriaLabel?: string;
  onAction?: () => void;
  value?: string;
  defaultValue?: string;
  onChange?: React.ChangeEventHandler<HTMLInputElement>;
  onFocus?: React.FocusEventHandler<HTMLInputElement>;
  onBlur?: React.FocusEventHandler<HTMLInputElement>;
  onKeyDown?: React.KeyboardEventHandler<HTMLInputElement>;
  inputMode?: React.HTMLAttributes<HTMLInputElement>["inputMode"];
  enterKeyHint?: React.InputHTMLAttributes<HTMLInputElement>["enterKeyHint"];
  inputRef?: React.Ref<HTMLInputElement>;
  className?: string;
}

export default function SearchBar({
  isSearchActivated,
  isSearchClear,
  navigateOnFocusTo = "",
  readOnly = false,
  autoFocus = false,
  showIcon = true,
  actionLabel = "",
  actionAriaLabel = "Выполнить поиск",
  onAction,
  value,
  defaultValue,
  onChange,
  onFocus,
  onBlur,
  onKeyDown,
  inputMode,
  enterKeyHint,
  inputRef,
  className,
}: SearchBarProps) {
  const router = useRouter();

  const rawText =
    typeof value === "string"
      ? value
      : typeof defaultValue === "string"
        ? defaultValue
        : "";
  const canAction = rawText.trim().length > 0;

  const handleFocus = (e: React.FocusEvent<HTMLInputElement>) => {
    onFocus?.(e);
    if (navigateOnFocusTo) router.push(navigateOnFocusTo);
  };

  return (
    <div className={className ? `${styles.outer} ${className}` : styles.outer}>
      <div className={styles.inner}>
        {showIcon ? (
          <Search size={18} color="#7E7E7E" aria-hidden="true" />
        ) : null}
        <input
          ref={inputRef}
          type="text"
          placeholder="Поиск"
          className={styles.input}
          readOnly={readOnly}
          autoFocus={autoFocus}
          value={value}
          defaultValue={defaultValue}
          onChange={onChange}
          onFocus={handleFocus}
          onBlur={onBlur}
          onKeyDown={onKeyDown}
          inputMode={inputMode}
          enterKeyHint={enterKeyHint}
        />

        {isSearchActivated ? (
          <button
            className={styles.isSearchActivated}
            onClick={() => {
              isSearchClear?.();
            }}
          >
            <img src="/icons/global/markX.svg" alt="xIcon" />
          </button>
        ) : null}

        {/* {actionLabel ? (
          <Button
            type="button"
            size="sm"
            variant="primary"
            className={styles.actionBtn}
            aria-label={actionAriaLabel}
            disabled={!canAction}
            onMouseDown={(e) => {
              e.preventDefault();
            }}
            onClick={() => onAction?.()}
          >
            {actionLabel}
          </Button>
        ) : null} */}
      </div>
    </div>
  );
}
