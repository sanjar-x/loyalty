'use client';

import { useEffect, useMemo, useRef, useState } from 'react';

import BottomSheet from '@/shared/ui/BottomSheet';

import {
  toDigits,
  digitsToNumber,
  formatNumber,
  buildCurrencyValue,
  countDigitsBeforeCaret,
  findCaretPosByDigitIndex,
} from '../lib/priceInput';
import styles from './PriceSheet.module.css';

export default function PriceSheet({
  open,
  onClose,
  title = 'Цена',
  value,
  minPlaceholder,
  maxPlaceholder,
  onApply,
}) {
  const initial = useMemo(() => {
    const min = value?.min ?? null;
    const max = value?.max ?? null;
    return {
      minDigits: min ? String(min) : '',
      maxDigits: max ? String(max) : '',
      min,
      max,
    };
  }, [value?.max, value?.min]);

  return (
    <PriceSheetInner
      open={open}
      onClose={onClose}
      title={title}
      initial={initial}
      minPlaceholder={minPlaceholder}
      maxPlaceholder={maxPlaceholder}
      onApply={onApply}
    />
  );
}

function PriceSheetInner({
  open,
  onClose,
  title,
  initial,
  minPlaceholder,
  maxPlaceholder,
  onApply,
}) {
  const [minDigits, setMinDigits] = useState(initial.minDigits);
  const [maxDigits, setMaxDigits] = useState(initial.maxDigits);

  const prevOpenRef = useRef(open);

  const minRef = useRef(null);
  const maxRef = useRef(null);

  useEffect(() => {
    const wasOpen = prevOpenRef.current;
    let frame = 0;

    if (open && !wasOpen) {
      frame = requestAnimationFrame(() => {
        setMinDigits(initial.minDigits);
        setMaxDigits(initial.maxDigits);
      });
    }

    prevOpenRef.current = open;
    return () => {
      if (frame) cancelAnimationFrame(frame);
    };
  }, [initial.maxDigits, initial.minDigits, open]);

  const draftMin = useMemo(() => digitsToNumber(minDigits), [minDigits]);
  const draftMax = useMemo(() => digitsToNumber(maxDigits), [maxDigits]);

  const changed = useMemo(() => {
    const aMin = initial.min ?? null;
    const aMax = initial.max ?? null;
    return aMin !== draftMin || aMax !== draftMax;
  }, [draftMax, draftMin, initial.max, initial.min]);

  const apply = () => {
    if (!changed) {
      onClose?.();
      return;
    }

    let nextMin = draftMin;
    let nextMax = draftMax;

    if (nextMin != null && nextMax != null && nextMin > nextMax) {
      const t = nextMin;
      nextMin = nextMax;
      nextMax = t;
    }

    onApply?.({ min: nextMin, max: nextMax });
    onClose?.();
  };

  const minLabel = useMemo(() => {
    const p = minPlaceholder != null ? `От ${formatNumber(minPlaceholder)} ₽` : 'От';
    return p;
  }, [minPlaceholder]);

  const maxLabel = useMemo(() => {
    const p = maxPlaceholder != null ? `До ${formatNumber(maxPlaceholder)} ₽` : 'До';
    return p;
  }, [maxPlaceholder]);

  const handleMinChange = (e) => {
    const input = e.target;
    const raw = input.value;

    const caretPos = input.selectionStart ?? raw.length;
    const digitsBeforeCaret = countDigitsBeforeCaret(raw, caretPos);

    const nextDigits = toDigits(raw);
    setMinDigits(nextDigits);

    requestAnimationFrame(() => {
      const el = minRef.current;
      if (!el) return;

      const nextFormatted = buildCurrencyValue(nextDigits);
      const nextCaretPos = findCaretPosByDigitIndex(nextFormatted, digitsBeforeCaret);

      try {
        el.setSelectionRange(nextCaretPos, nextCaretPos);
      } catch {
        // ba’zi mobil browserlarda setSelectionRange fail bo‘lishi mumkin
      }
    });
  };

  const handleMaxChange = (e) => {
    const input = e.target;
    const raw = input.value;

    const caretPos = input.selectionStart ?? raw.length;
    const digitsBeforeCaret = countDigitsBeforeCaret(raw, caretPos);

    const nextDigits = toDigits(raw);
    setMaxDigits(nextDigits);

    requestAnimationFrame(() => {
      const el = maxRef.current;
      if (!el) return;

      const nextFormatted = buildCurrencyValue(nextDigits);
      const nextCaretPos = findCaretPosByDigitIndex(nextFormatted, digitsBeforeCaret);

      try {
        el.setSelectionRange(nextCaretPos, nextCaretPos);
      } catch {
        // ignore
      }
    });
  };

  return (
    <BottomSheet
      open={open}
      onClose={onClose}
      title={title}
      footer={
        changed ? (
          <div className={styles.footerRow}>
            <button type="button" className={styles.cancelBtn} onClick={onClose}>
              Отменить
            </button>
            <button type="button" className={styles.applyBtn} onClick={apply}>
              Применить
            </button>
          </div>
        ) : (
          <button type="button" className={styles.cancelBtnFull} onClick={onClose}>
            Отмена
          </button>
        )
      }
    >
      <div className={styles.wrap}>
        <div className={styles.row}>
          {/* MIN */}
          <div className={styles.field}>
            <div className={styles.fieldLabel}>{minLabel} 2190 ₽</div>
            <div className={styles.fieldRow}>
              <input
                ref={minRef}
                className={styles.input}
                value={buildCurrencyValue(minDigits)}
                onChange={handleMinChange}
                inputMode="numeric"
                enterKeyHint="done"
                aria-label={minLabel}
              />
            </div>

            {minDigits ? (
              <button
                type="button"
                className={styles.clearBtn}
                aria-label="Очистить"
                onClick={() => setMinDigits('')}
              >
                <img src="/icons/global/markX.svg" alt="markx" />
              </button>
            ) : null}
          </div>

          {/* MAX */}
          <div className={styles.field}>
            <div className={`${styles.fieldLabel} ${styles.maxDigit}`}>
              {maxLabel} 20000 &#8381;
            </div>
            <div className={styles.fieldRow}>
              <input
                ref={maxRef}
                className={styles.input}
                value={buildCurrencyValue(maxDigits)}
                onChange={handleMaxChange}
                inputMode="numeric"
                enterKeyHint="done"
                aria-label={maxLabel}
              />
            </div>

            {maxDigits ? (
              <button
                type="button"
                className={styles.clearBtn}
                aria-label="Очистить"
                onClick={() => setMaxDigits('')}
              >
                <img src="/icons/global/markX.svg" alt="markx" />
              </button>
            ) : null}
          </div>
        </div>
      </div>
    </BottomSheet>
  );
}
