"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";

import BottomSheet from "@/components/ui/BottomSheet";

import styles from "./PriceSheet.module.css";

const MAX_DIGITS = 6;

function toDigits(value: string | number | null | undefined): string {
  const digits = String(value || "").replace(/[^0-9]/g, "");
  return digits.slice(0, MAX_DIGITS);
}

function digitsToNumber(value: string): number | null {
  const n = Number(toDigits(value));
  return Number.isFinite(n) && n > 0 ? n : null;
}

function formatNumber(value: number | string): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return "";
  return n.toLocaleString("ru-RU");
}

function formatNumberFromDigits(digits: string): string {
  const n = Number(digits);
  if (!digits || !Number.isFinite(n)) return "";
  return formatNumber(n);
}

function buildCurrencyValue(digits: string): string {
  if (!digits) return "";
  return `${formatNumberFromDigits(digits)} ₽`;
}

function countDigitsBeforeCaret(text: string, caretPos: number): number {
  return text.slice(0, caretPos).replace(/\D/g, "").length;
}

/**
 * digitsBeforeCaret => formatlangan string ichida caret qayerda turishi kerakligini topadi
 * suffix ham hisobga olinadi (₽).
 */
function findCaretPosByDigitIndex(formattedText: string, digitsBeforeCaret: number): number {
  let pos = 0;
  let seenDigits = 0;

  while (pos < formattedText.length && seenDigits < digitsBeforeCaret) {
    if (/\d/.test(formattedText[pos])) seenDigits++;
    pos++;
  }

  // Agar suffix bor bo'lsa, caret suffix ichiga kirib ketmasin
  // Masalan: "12 000 ₽" -> caret "₽"dan oldin to'xtasin
  const rubIndex = formattedText.indexOf("₽");
  if (rubIndex !== -1 && pos > rubIndex - 1) {
    pos = rubIndex - 1;
  }

  return pos;
}

interface PriceValue {
  min?: number | null;
  max?: number | null;
}

interface PriceSheetProps {
  open: boolean;
  onClose?: () => void;
  title?: string;
  value?: PriceValue;
  minPlaceholder?: number;
  maxPlaceholder?: number;
  onApply?: (value: { min: number | null; max: number | null }) => void;
}

interface InitialState {
  minDigits: string;
  maxDigits: string;
  min: number | null;
  max: number | null;
}

export default function PriceSheet({
  open,
  onClose,
  title = "Цена",
  value,
  minPlaceholder,
  maxPlaceholder,
  onApply,
}: PriceSheetProps) {
  const initial = useMemo((): InitialState => {
    const min = value?.min ?? null;
    const max = value?.max ?? null;
    return {
      minDigits: min ? String(min) : "",
      maxDigits: max ? String(max) : "",
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

interface PriceSheetInnerProps {
  open: boolean;
  onClose?: () => void;
  title?: string;
  initial: InitialState;
  minPlaceholder?: number;
  maxPlaceholder?: number;
  onApply?: (value: { min: number | null; max: number | null }) => void;
}

function PriceSheetInner({
  open,
  onClose,
  title,
  initial,
  minPlaceholder,
  maxPlaceholder,
  onApply,
}: PriceSheetInnerProps) {
  const [minDigits, setMinDigits] = useState(initial.minDigits);
  const [maxDigits, setMaxDigits] = useState(initial.maxDigits);

  const prevOpenRef = useRef(open);

  const minRef = useRef<HTMLInputElement>(null);
  const maxRef = useRef<HTMLInputElement>(null);

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
    const p =
      minPlaceholder != null ? `От ${formatNumber(minPlaceholder)} ₽` : "От";
    return p;
  }, [minPlaceholder]);

  const maxLabel = useMemo(() => {
    const p =
      maxPlaceholder != null ? `До ${formatNumber(maxPlaceholder)} ₽` : "До";
    return p;
  }, [maxPlaceholder]);

  const handleMinChange = (e: React.ChangeEvent<HTMLInputElement>) => {
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
      const nextCaretPos = findCaretPosByDigitIndex(
        nextFormatted,
        digitsBeforeCaret,
      );

      try {
        el.setSelectionRange(nextCaretPos, nextCaretPos);
      } catch {
        // ba'zi mobil browserlarda setSelectionRange fail bo'lishi mumkin
      }
    });
  };

  const handleMaxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
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
      const nextCaretPos = findCaretPosByDigitIndex(
        nextFormatted,
        digitsBeforeCaret,
      );

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
            <button
              type="button"
              className={styles.cancelBtn}
              onClick={onClose}
            >
              Отменить
            </button>
            <button type="button" className={styles.applyBtn} onClick={apply}>
              Применить
            </button>
          </div>
        ) : (
          <button
            type="button"
            className={styles.cancelBtnFull}
            onClick={onClose}
          >
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
                onClick={() => setMinDigits("")}
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
                className={`${styles.input} ${styles.inputDisable}`}
                value={buildCurrencyValue(maxDigits)}
                onChange={handleMaxChange}
                inputMode="numeric"
                enterKeyHint="done"
                aria-label={maxLabel}
                disabled
              />
            </div>

            {maxDigits ? (
              <button
                type="button"
                className={styles.clearBtn}
                aria-label="Очистить"
                onClick={() => setMaxDigits("")}
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
