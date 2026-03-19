'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronIcon } from './icons';
import styles from './page.module.css';

const SIZE_PRESETS = [
  { id: 'xs-l', label: 'XS - L', values: ['XS', 'S', 'M', 'L'] },
  { id: 's-xl', label: 'S - XL', values: ['S', 'M', 'L', 'XL'] },
  { id: 'm-2xl', label: 'M - 2XL', values: ['M', 'L', 'XL', '2XL'] },
];

export const SIZE_OPTIONS = [
  '2XS',
  'XS',
  'S',
  'M',
  'L',
  'XL',
  '2XL',
  '3XL',
  '4XL',
];

export const DEFAULT_SELECTED_SIZES = ['S', 'M', 'L', 'XL', '2XL'];

const SIZE_INDEX = new Map(SIZE_OPTIONS.map((size, index) => [size, index]));

export function sortSizes(sizes) {
  return [...new Set(sizes)].sort(
    (left, right) =>
      (SIZE_INDEX.get(left) ?? Number.MAX_SAFE_INTEGER) -
      (SIZE_INDEX.get(right) ?? Number.MAX_SAFE_INTEGER),
  );
}

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

export default function SizeSelect({
  value,
  onChange,
  defaultValue = DEFAULT_SELECTED_SIZES,
}) {
  const [open, setOpen] = useState(false);
  const [internalSelectedSizes, setInternalSelectedSizes] = useState(() =>
    sortSizes(defaultValue),
  );
  const rootRef = useRef(null);
  const isControlled = value !== undefined;
  const selectedSizes = isControlled ? sortSizes(value) : internalSelectedSizes;

  useEffect(() => {
    if (!open) {
      return;
    }

    function handlePointerDown(event) {
      if (!rootRef.current?.contains(event.target)) {
        setOpen(false);
      }
    }

    function handleEscape(event) {
      if (event.key === 'Escape') {
        setOpen(false);
      }
    }

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [open]);

  const selectedSet = useMemo(() => new Set(selectedSizes), [selectedSizes]);

  function updateSelectedSizes(nextValueOrUpdater) {
    const nextValue = sortSizes(
      typeof nextValueOrUpdater === 'function'
        ? nextValueOrUpdater(selectedSizes)
        : nextValueOrUpdater,
    );

    if (!isControlled) {
      setInternalSelectedSizes(nextValue);
    }

    onChange?.(nextValue);
  }

  function toggleSize(size) {
    updateSelectedSizes((current) =>
      current.includes(size)
        ? current.filter((item) => item !== size)
        : [...current, size],
    );
  }

  function togglePreset(values) {
    const allIncluded = values.every((value) => selectedSet.has(value));

    updateSelectedSizes((current) => {
      if (allIncluded) {
        return current.filter((item) => !values.includes(item));
      }

      const next = [...current];
      values.forEach((value) => {
        if (!next.includes(value)) {
          next.push(value);
        }
      });
      return next;
    });
  }

  function handleFieldKeyDown(event) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      setOpen((current) => !current);
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
        onClick={() => setOpen((current) => !current)}
        onKeyDown={handleFieldKeyDown}
      >
        <div className={styles.sizeSelectTriggerContent}>
          <span className={styles.sizeSelectLabel}>Размеры</span>
          <div className={styles.sizeSelectChips}>
            {selectedSizes.length ? (
              selectedSizes.map((size) => (
                <button
                  key={size}
                  type="button"
                  className={styles.sizeChip}
                  onClick={(event) => {
                    event.stopPropagation();
                    toggleSize(size);
                  }}
                  aria-label={`Убрать размер ${size}`}
                >
                  <span>{size}</span>
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
                Выберите размеры
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
          aria-label="Список размеров"
        >
          <div className={styles.sizePresetRow}>
            {SIZE_PRESETS.map((preset) => {
              const active = preset.values.every((value) =>
                selectedSet.has(value),
              );

              return (
                <button
                  key={preset.id}
                  type="button"
                  className={styles.sizePresetButton}
                  onClick={() => togglePreset(preset.values)}
                >
                  <span
                    className={
                      active ? styles.sizeCheckboxChecked : styles.sizeCheckbox
                    }
                  >
                    {active ? <CheckIcon /> : null}
                  </span>
                  <span>{preset.label}</span>
                </button>
              );
            })}
          </div>

          <div className={styles.sizeOptionsList}>
            {SIZE_OPTIONS.map((size) => {
              const checked = selectedSet.has(size);

              return (
                <button
                  key={size}
                  type="button"
                  className={styles.sizeOption}
                  role="option"
                  aria-selected={checked}
                  onClick={() => toggleSize(size)}
                >
                  <span
                    className={
                      checked ? styles.sizeCheckboxChecked : styles.sizeCheckbox
                    }
                  >
                    {checked ? <CheckIcon /> : null}
                  </span>
                  <span className={styles.sizeOptionLabel}>{size}</span>
                </button>
              );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
}
