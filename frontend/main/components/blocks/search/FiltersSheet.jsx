"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Info, X } from "lucide-react";

import BottomSheet from "@/components/ui/BottomSheet";

import styles from "./FiltersSheet.module.css";

const MAX_DIGITS = 6;

function toDigits(value) {
  const digits = String(value || "").replace(/[^0-9]/g, "");
  return digits.slice(0, MAX_DIGITS);
}

function digitsToNumber(value) {
  const n = Number(toDigits(value));
  return Number.isFinite(n) && n > 0 ? n : null;
}

function formatNumber(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "";
  return n.toLocaleString("ru-RU");
}

function formatNumberFromDigits(digits) {
  const n = Number(digits);
  if (!digits || !Number.isFinite(n)) return "";
  return formatNumber(n);
}

function buildCurrencyValue(digits) {
  if (!digits) return "";
  return `${formatNumberFromDigits(digits)} ₽`;
}

function countDigitsBeforeCaret(text, caretPos) {
  return text.slice(0, caretPos).replace(/\D/g, "").length;
}

function findCaretPosByDigitIndex(formattedText, digitsBeforeCaret) {
  let pos = 0;
  let seenDigits = 0;

  while (pos < formattedText.length && seenDigits < digitsBeforeCaret) {
    if (/\d/.test(formattedText[pos])) seenDigits++;
    pos++;
  }

  const rubIndex = formattedText.indexOf("₽");
  if (rubIndex !== -1 && pos > rubIndex - 1) {
    pos = rubIndex - 1;
  }

  return pos;
}

function priceChipLabel(range) {
  const min = range?.min ?? null;
  const max = range?.max ?? null;
  if (min == null && max == null) return null;
  if (min != null && max != null)
    return `От ${formatNumber(min)} ₽ до ${formatNumber(max)} ₽`;
  if (min != null) return `От ${formatNumber(min)} ₽`;
  return `До ${formatNumber(max)} ₽`;
}

function joinOrPlaceholder(items, placeholder) {
  const arr = Array.isArray(items) ? items.filter(Boolean) : [];
  if (!arr.length) return placeholder;
  return arr.join(", ");
}

export default function FiltersSheet({
  open,
  onClose,
  title = "Фильтры",
  categories = ["Одежда", "Обувь", "Аксессуары"],
  typeOptions,
  brandOptions,
  value,
  priceBounds,
  onApply,
  onOpenTypePicker,
  onOpenBrandPicker,
}) {
  const initial = useMemo(() => {
    return {
      categoryIds: Array.isArray(value?.categoryIds) ? value.categoryIds : [],
      types: Array.isArray(value?.types) ? value.types : [],
      brands: Array.isArray(value?.brands) ? value.brands : [],
      priceRange: value?.priceRange ?? { min: null, max: null },
      delivery: {
        inStock: Boolean(value?.delivery?.inStock),
        fromChina: Boolean(value?.delivery?.fromChina),
      },
      original: Boolean(value?.original),
    };
  }, [
    value?.brands,
    value?.categoryIds,
    value?.delivery?.fromChina,
    value?.delivery?.inStock,
    value?.original,
    value?.priceRange,
    value?.types,
  ]);

  const [draft, setDraft] = useState(initial);
  const prevOpenRef = useRef(open);

  const minRef = useRef(null);
  const maxRef = useRef(null);

  const [minDigits, setMinDigits] = useState(() =>
    initial.priceRange?.min ? String(initial.priceRange.min) : "",
  );
  const [maxDigits, setMaxDigits] = useState(() =>
    initial.priceRange?.max ? String(initial.priceRange.max) : "",
  );

  useEffect(() => {
    const wasOpen = prevOpenRef.current;
    let frame = 0;

    if (open && !wasOpen) {
      frame = requestAnimationFrame(() => {
        setDraft(initial);
        setMinDigits(
          initial.priceRange?.min ? String(initial.priceRange.min) : "",
        );
        setMaxDigits(
          initial.priceRange?.max ? String(initial.priceRange.max) : "",
        );
      });
    }

    prevOpenRef.current = open;
    return () => {
      if (frame) cancelAnimationFrame(frame);
    };
  }, [initial, open]);

  const draftMin = useMemo(() => digitsToNumber(minDigits), [minDigits]);
  const draftMax = useMemo(() => digitsToNumber(maxDigits), [maxDigits]);

  const normalizedPriceRange = useMemo(() => {
    let min = draftMin;
    let max = draftMax;
    if (min != null && max != null && min > max) {
      const t = min;
      min = max;
      max = t;
    }
    return { min, max };
  }, [draftMax, draftMin]);

  const changed = useMemo(() => {
    const a = initial;
    const b = {
      ...draft,
      priceRange: normalizedPriceRange,
    };

    const aCats = new Set(a.categoryIds || []);
    const bCats = new Set(b.categoryIds || []);
    const sameCategory =
      aCats.size === bCats.size &&
      Array.from(aCats).every((x) => bCats.has(x));
    const sameOriginal = Boolean(a.original) === Boolean(b.original);
    const sameDelivery =
      Boolean(a.delivery?.inStock) === Boolean(b.delivery?.inStock) &&
      Boolean(a.delivery?.fromChina) === Boolean(b.delivery?.fromChina);

    const samePrice =
      (a.priceRange?.min ?? null) === (b.priceRange?.min ?? null) &&
      (a.priceRange?.max ?? null) === (b.priceRange?.max ?? null);

    const aTypes = new Set(a.types || []);
    const bTypes = new Set(b.types || []);
    const sameTypes =
      aTypes.size === bTypes.size &&
      Array.from(aTypes).every((x) => bTypes.has(x));

    const aBrands = new Set(a.brands || []);
    const bBrands = new Set(b.brands || []);
    const sameBrands =
      aBrands.size === bBrands.size &&
      Array.from(aBrands).every((x) => bBrands.has(x));

    return !(
      sameCategory &&
      sameTypes &&
      sameBrands &&
      samePrice &&
      sameDelivery &&
      sameOriginal
    );
  }, [draft, initial, normalizedPriceRange]);

  const apply = () => {
    const next = {
      ...draft,
      priceRange: normalizedPriceRange,
    };

    if (!changed) {
      onClose?.();
      return;
    }

    onApply?.(next);
    onClose?.();
  };

  const selectedChips = useMemo(() => {
    const chips = [];

    for (const catId of draft.categoryIds || []) {
      const cat = categories.find((c) => c.id === catId);
      if (cat) chips.push({ key: `cat:${catId}`, label: cat.name });
    }

    for (const t of draft.types || []) {
      chips.push({ key: `type:${t}`, label: t });
    }

    const priceLabel = priceChipLabel(normalizedPriceRange);
    if (priceLabel) {
      chips.push({ key: "price", label: priceLabel });
    }

    for (const b of draft.brands || []) {
      chips.push({ key: `brand:${b}`, label: b });
    }

    if (draft.delivery?.inStock) {
      chips.push({ key: "delivery:inStock", label: "Из наличия" });
    }

    if (draft.delivery?.fromChina) {
      chips.push({ key: "delivery:fromChina", label: "Из Китая" });
    }

    if (draft.original) {
      chips.push({ key: "original", label: "Оригинал" });
    }

    return chips;
  }, [draft, normalizedPriceRange]);

  const removeChip = (key) => {
    if (key === "price") {
      setMinDigits("");
      setMaxDigits("");
      return;
    }

    if (key === "original") {
      setDraft((prev) => ({ ...prev, original: false }));
      return;
    }

    if (key === "delivery:inStock") {
      setDraft((prev) => ({
        ...prev,
        delivery: { ...prev.delivery, inStock: false },
      }));
      return;
    }

    if (key === "delivery:fromChina") {
      setDraft((prev) => ({
        ...prev,
        delivery: { ...prev.delivery, fromChina: false },
      }));
      return;
    }

    if (key.startsWith("cat:")) {
      const catId = Number(key.slice("cat:".length));
      setDraft((prev) => ({
        ...prev,
        categoryIds: (prev.categoryIds || []).filter((id) => id !== catId),
      }));
      return;
    }

    if (key.startsWith("type:")) {
      const valueToRemove = key.slice("type:".length);
      setDraft((prev) => ({
        ...prev,
        types: (prev.types || []).filter((x) => x !== valueToRemove),
      }));
      return;
    }

    if (key.startsWith("brand:")) {
      const valueToRemove = key.slice("brand:".length);
      setDraft((prev) => ({
        ...prev,
        brands: (prev.brands || []).filter((x) => x !== valueToRemove),
      }));
    }
  };

  const minLabel = useMemo(() => {
    const p =
      priceBounds?.min != null ? `От ${formatNumber(priceBounds.min)} ₽` : "От";
    return p;
  }, [priceBounds?.min]);

  const maxLabel = useMemo(() => {
    const p =
      priceBounds?.max != null ? `До ${formatNumber(priceBounds.max)} ₽` : "До";
    return p;
  }, [priceBounds?.max]);

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

  const [minFocused, setMinFocused] = useState(false);
  const [maxFocused, setMaxFocused] = useState(false);
  const [originalInfoOpen, setOriginalInfoOpen] = useState(false);

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
    <>
      <BottomSheet
        isFilter={true}
        open={open}
        onClose={onClose}
        title={title}
      >
        <div className={styles.body}>
          {selectedChips.length ? (
            <div
              className={styles.selectedChips}
              aria-label="Выбранные фильтры"
            >
              {selectedChips.map((chip) => (
                <button
                  key={chip.key}
                  type="button"
                  className={styles.selectedChip}
                  onClick={() => removeChip(chip.key)}
                >
                  <span className={styles.selectedChipLabel}>{chip.label}</span>
                  <span className={styles.selectedChipX} aria-hidden="true">
                    <img src="/icons/global/markXBlack.svg" alt="markx" />
                  </span>
                </button>
              ))}
            </div>
          ) : null}

          <div className={styles.section}>
            <div className={styles.sectionTitle}>Категория</div>
            <div
              className={styles.segmented}
              role="group"
              aria-label="Категория"
            >
              {categories.map((c) => {
                const active = (draft.categoryIds || []).includes(c.id);
                return (
                  <button
                    key={c.id}
                    type="button"
                    className={active ? styles.segmentActive : styles.segment}
                    onClick={() =>
                      setDraft((prev) => {
                        const ids = prev.categoryIds || [];
                        return {
                          ...prev,
                          categoryIds: active
                            ? ids.filter((id) => id !== c.id)
                            : [...ids, c.id],
                        };
                      })
                    }
                  >
                    <span className={styles.segmentLabel}>{c.name}</span>
                    {active ? (
                      <span className={styles.segmentX} aria-hidden="true">
                        <img src="/icons/global/markXBlack.svg" alt="markx" />
                      </span>
                    ) : null}
                  </button>
                );
              })}
            </div>
          </div>

          <div className={styles.section}>
            <div className={styles.sectionTitle}>Тип</div>
            <button
              type="button"
              className={styles.field}
              onClick={() => onOpenTypePicker?.(draft.types)}
            >
              <div className={styles.fieldValue}>
                {joinOrPlaceholder(draft.types, "Не выбран")}
              </div>
              {draft.types?.length ? (
                <span
                  className={styles.fieldClear}
                  aria-label="Очистить"
                  onClick={(e) => {
                    e.stopPropagation();
                    setDraft((prev) => ({ ...prev, types: [] }));
                  }}
                >
                  <X size={18} aria-hidden="true" />
                </span>
              ) : null}
              {!draft.types?.length ? (
                <img src="/icons/global/arrowDownGrey.svg" alt="arrowDown" />
              ) : null}
            </button>
          </div>

          <div className={styles.section}>
            <div className={styles.sectionTitle}>Бренд</div>
            <button
              type="button"
              className={styles.field}
              onClick={() => onOpenBrandPicker?.(draft.brands)}
            >
              <div className={styles.fieldValue}>
                {joinOrPlaceholder(draft.brands, "Не выбран")}
              </div>
              {draft.brands?.length ? (
                <span
                  className={styles.fieldClear}
                  aria-label="Очистить"
                  onClick={(e) => {
                    e.stopPropagation();
                    setDraft((prev) => ({ ...prev, brands: [] }));
                  }}
                >
                  <X size={18} aria-hidden="true" />
                </span>
              ) : null}
              {!draft.brands?.length ? (
                <img src="/icons/global/arrowDownGrey.svg" alt="arrowDown" />
              ) : null}
            </button>
          </div>

          <div className={styles.section}>
            <div className={styles.sectionTitle}>Цена</div>
            <div className={styles.priceWrap}>
              <div className={styles.priceRow}>
                {/* MIN */}
                <div className={styles.priceField}>
                  <div
                    className={`${styles.priceLabel} ${
                      minFocused || minDigits ? styles.priceLabelActive : ""
                    }`}
                  >
                    {minLabel} 2190 &#8381;
                  </div>

                  <input
                    ref={minRef}
                    className={styles.priceInput}
                    value={buildCurrencyValue(minDigits)}
                    onChange={handleMinChange}
                    onFocus={() => setMinFocused(true)}
                    onBlur={() => setMinFocused(false)}
                    inputMode="numeric"
                    enterKeyHint="done"
                    placeholder={minFocused ? "₽" : ""}
                  />

                  {minDigits ? (
                    <button className={styles.priceAppear}>
                      <img src="/icons/global/markX.svg" alt="" />
                    </button>
                  ) : null}
                </div>

                {/* MAX */}
                <div
                  className={styles.priceField}
                >
                  <div
                    className={`${styles.priceLabel} ${
                      maxFocused || maxDigits ? styles.priceLabelActive : ""
                    }`}
                  >
                    {maxLabel} 20000 &#8381;
                  </div>
                  <input
                    ref={maxRef}
                    className={styles.priceInput}
                    value={buildCurrencyValue(maxDigits)}
                    onChange={handleMaxChange}
                    onFocus={() => setMaxFocused(true)}
                    onBlur={() => setMaxFocused(false)}
                    inputMode="numeric"
                    enterKeyHint="done"
                    placeholder={maxFocused ? "₽" : ""}
                  />

                  {maxDigits ? (
                    <button
                      type="button"
                      className={styles.priceClearBtn}
                      aria-label="Очистить"
                      onClick={() => setMaxDigits("")}
                    >
                      <img src="/icons/global/markX.svg" alt="arrowDown" />
                    </button>
                  ) : null}
                </div>
              </div>
            </div>
          </div>

          <div className={styles.section}>
            <div className={styles.sectionTitle}>Доставка</div>
            <div className={styles.chipRow}>
              <button
                type="button"
                className={
                  draft.delivery?.inStock
                    ? styles.toggleChipActive
                    : styles.toggleChip
                }
                onClick={() =>
                  setDraft((prev) => ({
                    ...prev,
                    delivery: {
                      ...prev.delivery,
                      inStock: !prev.delivery?.inStock,
                    },
                  }))
                }
              >
                Из наличия
              </button>
              <button
                type="button"
                className={
                  draft.delivery?.fromChina
                    ? styles.toggleChipActive
                    : styles.toggleChip
                }
                onClick={() =>
                  setDraft((prev) => ({
                    ...prev,
                    delivery: {
                      ...prev.delivery,
                      fromChina: !prev.delivery?.fromChina,
                    },
                  }))
                }
              >
                Из Китая
              </button>
            </div>
          </div>

          <div className={styles.section}>
            <div className={styles.switchRow}>
              <div className={styles.switchLeft}>
                <div className={styles.switchTitle}>Оригинал</div>
                <button
                  type="button"
                  className={styles.infoBtn}
                  onClick={() => setOriginalInfoOpen(true)}
                  aria-label="Подробнее об оригинале"
                >
                  <Info size={16} className={styles.infoIcon} />
                </button>
              </div>

              <label className={styles.switch}>
                <input
                  type="checkbox"
                  checked={draft.original}
                  onChange={(e) =>
                    setDraft((prev) => ({
                      ...prev,
                      original: e.target.checked,
                    }))
                  }
                />
                <span className={styles.switchTrack} aria-hidden="true" />
              </label>
            </div>
          </div>

          <div className={styles.footerRow}>
            <button type="button" className={styles.cancelBtn} onClick={onClose}>
              Отменить
            </button>
            <button type="button" className={styles.applyBtn} onClick={apply}>
              Применить
            </button>
          </div>
        </div>
      </BottomSheet>

      <BottomSheet
        open={originalInfoOpen}
        onClose={() => setOriginalInfoOpen(false)}
        title="Оригинал"
        footer={
          <div className={styles.footerRow}>
            <button
              type="button"
              className={styles.cancelBtn}
              onClick={() => {
                setOriginalInfoOpen(false);
              }}
            >
              Подробнее
            </button>
            <button
              type="button"
              className={styles.applyBtn}
              onClick={() => setOriginalInfoOpen(false)}
            >
              Понятно
            </button>
          </div>
        }
      >
        <div className={styles.originalInfoBody}>
          <p>
            Все товары со значком «ОРИГИНАЛ» проходят через маркетплейс POIZON.
          </p>
          <p>
            Перед отправкой каждый товар проверяется на оригинальность по
            внутренней системе верификации и получает подтверждение в виде
            сертификата и пломбы.
          </p>
          <p>
            Если товар окажется неоригинальным, мы вернем деньги в двукратном
            размере и начислим баллы на сумму покупки.
          </p>
        </div>
      </BottomSheet>

      {/* Optional pickers, if parent provides handlers */}
      {typeOptions}
      {brandOptions}
    </>
  );
}
