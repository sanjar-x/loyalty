"use client";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";

import Button from "@/components/ui/Button";

import styles from "./SearchBar.module.css";

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
}) {
  const router = useRouter();

  const rawText =
    typeof value === "string"
      ? value
      : typeof defaultValue === "string"
        ? defaultValue
        : "";
  const canAction = rawText.trim().length > 0;

  const handleFocus = (e) => {
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
              isSearchClear();
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
