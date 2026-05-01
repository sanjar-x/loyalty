'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { i18n } from '@/shared/lib/utils';
import { CheckIcon, ChevronIcon, SmallCloseIcon } from './icons';
import styles from './styles/productForm.module.css';

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

function VariantAttributeSelect({ attribute, selectedIds, onToggle }) {
  const [open, setOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const rootRef = useRef(null);
  // Memoise the values fallback so the dependency arrays of the
  // useMemo hooks below stay referentially stable when `attribute.values`
  // is not provided.
  const attrValues = useMemo(() => attribute.values ?? [], [attribute.values]);
  const label = i18n(attribute.nameI18N, attribute.code);

  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);

  const filteredValues = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return attrValues;
    return attrValues.filter((v) => {
      const text = i18n(v.valueI18N, v.code);
      return text?.toLowerCase().includes(q);
    });
  }, [attrValues, searchQuery]);

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
        onClick={() => {
          setOpen((c) => {
            if (!c) setSearchQuery('');
            return !c;
          });
        }}
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
                  onMouseDown={(e) => e.stopPropagation()}
                  onClick={(e) => {
                    e.stopPropagation();
                    onToggle(val.id);
                  }}
                  aria-label={`Убрать ${i18n(val.valueI18N, val.code)}`}
                >
                  <span>{i18n(val.valueI18N, val.code)}</span>
                  <span className={styles.sizeChipClose}>
                    <SmallCloseIcon />
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
        <div className={styles.sizeDropdown} role="listbox" aria-label={label}>
          <div className={styles.dropdownSearchWrap}>
            <input
              className={styles.dropdownSearchInput}
              placeholder={`Поиск...`}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              autoFocus
              onMouseDown={(e) => e.stopPropagation()}
            />
          </div>
          <div className={styles.sizeOptionsList}>
            {filteredValues.length === 0 ? (
              <div
                className={styles.sizeOption}
                style={{ cursor: 'default', opacity: 0.5 }}
              >
                <span className={styles.sizeOptionLabel}>
                  Ничего не найдено
                </span>
              </div>
            ) : (
              filteredValues.map((val) => {
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
                        checked
                          ? styles.sizeCheckboxChecked
                          : styles.sizeCheckbox
                      }
                    >
                      {checked ? <CheckIcon /> : null}
                    </span>
                    <span className={styles.sizeOptionLabel}>
                      {i18n(val.valueI18N, val.code)}
                    </span>
                  </button>
                );
              })
            )}
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
    return <div className={styles.skeletonSelect} />;
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
