'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { i18n } from '@/lib/utils';
import { ChevronIcon } from './icons';
import styles from './page.module.css';

/**
 * Multi-select dropdown for variant-level attributes (sizes, colors, etc.)
 * driven by data from the form-attributes API.
 *
 * Props:
 *   attributes: FormAttribute[] — variant-level attributes from API
 *   values: { [attrId]: [valueId, ...] } — selected value IDs per attribute
 *   onChange: (attrId, valueIds) => void — callback when selection changes
 *   loading: boolean — show skeleton while form-attributes are loading
 */

function CheckIcon() {
  return (
    <svg
      width="14"
      height="10"
      viewBox="0 0 14 10"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M1 5.33333L4.6 9L13 1"
        stroke="white"
        strokeWidth="1.9"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function VariantAttributeSelect({ attribute, selectedIds, onToggle }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);
  const attrValues = attribute.values ?? [];
  const label = i18n(attribute.nameI18N, attribute.code);

  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);

  // Selected values in their original sort order
  const selectedValues = useMemo(
    () => attrValues.filter((v) => selectedSet.has(v.id)),
    [attrValues, selectedSet],
  );

  useEffect(() => {
    if (!open) return;

    function handlePointerDown(event) {
      if (!rootRef.current?.contains(event.target)) setOpen(false);
    }
    function handleEscape(event) {
      if (event.key === 'Escape') setOpen(false);
    }

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [open]);

  function handleFieldKeyDown(event) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      setOpen((c) => !c);
    }
  }

  return (
    <div className={styles.sizeSelect} ref={rootRef}>
      <div
        className={styles.sizeSelectTrigger}
        role="button"
        tabIndex={0}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((c) => !c)}
        onKeyDown={handleFieldKeyDown}
      >
        <div className={styles.sizeSelectTriggerContent}>
          <span className={styles.sizeSelectLabel}>{label}</span>
          <div className={styles.sizeSelectChips}>
            {selectedValues.length ? (
              selectedValues.map((val) => (
                <button
                  key={val.id}
                  type="button"
                  className={styles.sizeChip}
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggle(val.id);
                  }}
                  aria-label={`Убрать ${i18n(val.valueI18N, val.code)}`}
                >
                  <span>{i18n(val.valueI18N, val.code)}</span>
                  <span className={styles.sizeChipClose}>
                    <svg
                      width="12"
                      height="12"
                      viewBox="0 0 12 12"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path
                        d="M0.75 0.75L5.75 5.75M10.75 10.75L5.75 5.75M5.75 5.75L10.3929 0.75M5.75 5.75L0.75 10.75"
                        stroke="#7E7E7E"
                        strokeWidth="1.5"
                        strokeLinecap="round"
                      />
                    </svg>
                  </span>
                </button>
              ))
            ) : (
              <span className={styles.sizeSelectPlaceholder}>
                Выберите {label.toLowerCase()}
              </span>
            )}
          </div>
        </div>
        <span
          className={
            open ? styles.sizeSelectChevronOpen : styles.sizeSelectChevron
          }
        >
          <ChevronIcon />
        </span>
      </div>

      {open ? (
        <div
          className={styles.sizeDropdown}
          role="listbox"
          aria-label={label}
        >
          <div className={styles.sizeOptionsList}>
            {attrValues.map((val) => {
              const checked = selectedSet.has(val.id);
              return (
                <button
                  key={val.id}
                  type="button"
                  className={styles.sizeOption}
                  role="option"
                  aria-selected={checked}
                  onClick={() => onToggle(val.id)}
                >
                  <span
                    className={
                      checked ? styles.sizeCheckboxChecked : styles.sizeCheckbox
                    }
                  >
                    {checked ? <CheckIcon /> : null}
                  </span>
                  <span className={styles.sizeOptionLabel}>
                    {i18n(val.valueI18N, val.code)}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default function VariantSelect({
  attributes = [],
  values = {},
  onChange,
  loading = false,
}) {
  if (loading) {
    return <div className="h-12 rounded-lg bg-app-card animate-pulse" />;
  }

  if (attributes.length === 0) return null;

  function handleToggle(attrId, valueId) {
    const current = values[attrId] ?? [];
    const has = current.includes(valueId);
    const next = has
      ? current.filter((id) => id !== valueId)
      : [...current, valueId];
    onChange?.(attrId, next);
  }

  return attributes.map((attr) => (
    <VariantAttributeSelect
      key={attr.attributeId}
      attribute={attr}
      selectedIds={values[attr.attributeId] ?? []}
      onToggle={(valueId) => handleToggle(attr.attributeId, valueId)}
    />
  ));
}
