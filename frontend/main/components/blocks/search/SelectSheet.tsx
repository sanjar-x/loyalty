"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import BottomSheet from "@/components/ui/BottomSheet";

import styles from "./SelectSheet.module.css";

interface SelectOption {
  kind?: "section";
  label: string;
  value?: string;
}

function toArray(value: unknown): string[] {
  if (!value) return [];
  return Array.isArray(value) ? value : [value as string];
}

function normalizeText(value: unknown): string {
  return String(value || "")
    .trim()
    .replace(/\s+/g, " ")
    .toLowerCase();
}

function getAlphaKey(label: string | undefined): string {
  const first = String(label || "")
    .trim()
    .charAt(0);
  if (!first) return "#";
  const upper = first.toUpperCase();
  if (/^[0-9]$/.test(upper)) return "#";
  return upper;
}

interface SelectSheetProps {
  open: boolean;
  onClose?: () => void;
  title?: string;
  options?: SelectOption[];
  multiple?: boolean;
  value?: string | string[] | null;
  control?: "auto" | "check" | "radio";
  showSelectedChips?: boolean;
  searchable?: boolean;
  searchPlaceholder?: string;
  groupBy?: "alpha" | string;
  onApply?: (value: string | string[] | null) => void;
  isTypeModule?: boolean;
}

export default function SelectSheet({
  open,
  onClose,
  title,
  options,
  multiple = false,
  value,
  control = "auto",
  showSelectedChips = false,
  searchable = false,
  searchPlaceholder = "Поиск",
  groupBy,
  onApply,
  isTypeModule,
}: SelectSheetProps) {
  const normalizedValue = useMemo(
    () => (multiple ? toArray(value) : (value ?? null)),
    [multiple, value],
  );

  const resolvedControl =
    control === "auto" ? (multiple ? "check" : "radio") : control;

  return (
    <SelectSheetStateful
      open={open}
      onClose={onClose}
      title={title}
      options={options}
      multiple={multiple}
      initialValue={normalizedValue}
      control={resolvedControl}
      showSelectedChips={showSelectedChips}
      searchable={searchable}
      searchPlaceholder={searchPlaceholder}
      groupBy={groupBy}
      onApply={onApply}
      isTypeModule={isTypeModule}
    />
  );
}

interface SelectSheetStatefulProps {
  open: boolean;
  onClose?: () => void;
  title?: string;
  options?: SelectOption[];
  multiple: boolean;
  initialValue: string | string[] | null;
  control: string;
  showSelectedChips: boolean;
  searchable: boolean;
  searchPlaceholder: string;
  groupBy?: string;
  onApply?: (value: string | string[] | null) => void;
  isTypeModule?: boolean;
}

function SelectSheetStateful({
  open,
  onClose,
  title,
  options,
  multiple,
  initialValue,
  control,
  showSelectedChips,
  searchable,
  searchPlaceholder,
  groupBy,
  onApply,
  isTypeModule,
}: SelectSheetStatefulProps) {
  const [draft, setDraft] = useState<string | string[] | null>(initialValue);
  const [search, setSearch] = useState("");
  const prevOpenRef = useRef(open);

  useEffect(() => {
    const wasOpen = prevOpenRef.current;
    let frame = 0;
    if (open && !wasOpen) {
      frame = requestAnimationFrame(() => {
        setDraft(initialValue);
        setSearch("");
      });
    }
    prevOpenRef.current = open;
    return () => {
      if (frame) cancelAnimationFrame(frame);
    };
  }, [initialValue, open]);

  const labelByValue = useMemo(() => {
    const map = new Map<string, string>();
    for (const opt of options || []) {
      if (!opt) continue;
      if (opt.kind === "section") continue;
      if (typeof opt.value === "undefined") continue;
      map.set(opt.value!, opt.label);
    }
    return map;
  }, [options]);

  const changed = useMemo(() => {
    if (multiple) {
      const a = new Set(toArray(initialValue));
      const b = new Set(toArray(draft));
      if (a.size !== b.size) return true;
      for (const item of a) if (!b.has(item)) return true;
      return false;
    }
    return (initialValue ?? null) !== (draft ?? null);
  }, [draft, initialValue, multiple]);

  const toggle = (next: string) => {
    if (!multiple) {
      setDraft(next);
      return;
    }

    setDraft((prev) => {
      const arr = toArray(prev);
      const set = new Set(arr);
      if (set.has(next)) set.delete(next);
      else set.add(next);
      return Array.from(set);
    });
  };

  const apply = () => {
    if (!changed) {
      onClose?.();
      return;
    }

    onApply?.(draft);
    onClose?.();
  };

  const selectedValues = multiple ? toArray(draft) : [];

  const removeSelected = (valueToRemove: string) => {
    if (!multiple) return;
    setDraft((prev) => toArray(prev).filter((v) => v !== valueToRemove));
  };

  const displayOptions = useMemo(() => {
    const rawOptions = Array.isArray(options) ? options : [];
    const q = searchable ? normalizeText(search) : "";

    const flat = rawOptions.filter((opt) => opt && opt.kind !== "section");
    const filteredFlat = q
      ? flat.filter((opt) => normalizeText(opt.label).includes(q as string))
      : flat;

    if (groupBy === "alpha") {
      const groups = new Map<string, SelectOption[]>();
      for (const opt of filteredFlat) {
        const key = getAlphaKey(opt.label);
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key)!.push(opt);
      }

      const keys = Array.from(groups.keys()).sort((a, b) =>
        String(a).localeCompare(String(b)),
      );

      const out: SelectOption[] = [];
      for (const key of keys) {
        out.push({ kind: "section", label: key });
        out.push(...groups.get(key)!);
      }
      return out;
    }

    if (!q) return rawOptions;

    // Preserve existing sections, but drop empty ones after filtering.
    const out: SelectOption[] = [];
    let pendingSection: SelectOption | null = null;
    let sectionHasItems = false;

    for (const opt of rawOptions) {
      if (!opt) continue;
      if (opt.kind === "section") {
        if (pendingSection && sectionHasItems) out.push(pendingSection);
        pendingSection = opt;
        sectionHasItems = false;
        continue;
      }

      if (!normalizeText(opt.label).includes(q as string)) continue;
      if (pendingSection && !sectionHasItems) {
        out.push(pendingSection);
        sectionHasItems = true;
      }
      out.push(opt);
    }

    return out;
  }, [groupBy, options, search, searchable]);

  return (
    <BottomSheet
      open={open}
      onClose={onClose}
      title={title}
      isTypeModule={isTypeModule}
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
            Отменить
          </button>
        )
      }
    >
      {searchable ? (
        <div className={styles.searchWrap}>
          <div className={styles.searchField}>
            <span className={styles.searchIcon} aria-hidden="true">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="21"
                height="21"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#CAC9C7"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="lucide lucide-search"
                aria-hidden="true"
              >
                <path d="m21 21-4.34-4.34"></path>
                <circle cx="11" cy="11" r="8"></circle>
              </svg>
            </span>
            <input
              className={styles.searchInput}
              value={search}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearch(e.target.value)}
              placeholder={searchPlaceholder}
              inputMode="search"
              enterKeyHint="search"
              aria-label={searchPlaceholder}
            />
          </div>
        </div>
      ) : null}

      {multiple && showSelectedChips && selectedValues.length ? (
        <div className={styles.selectedChips} aria-label="Выбранные">
          <div className={styles.selectedChipsRow}>
            {selectedValues.map((v) => {
              const label = labelByValue.get(v) ?? String(v);
              return (
                <button
                  key={String(v)}
                  type="button"
                  className={styles.selectedChip}
                  onClick={() => removeSelected(v)}
                >
                  <span className={styles.selectedChipText}>{label}</span>
                  <span className={styles.selectedChipX} aria-hidden="true">
                    <img src="/icons/global/markXBlack.svg" alt="" />
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      ) : null}

      <div className={styles.list} role={multiple ? "group" : "radiogroup"}>
        {(displayOptions || []).map((opt, idx) => {
          if (!opt) return null;
          if (opt.kind === "section") {
            return (
              <div
                key={`section-${idx}-${opt.label}`}
                className={styles.sectionLabel}
                aria-hidden="true"
              >
                {opt.label}
              </div>
            );
          }

          const selected = multiple
            ? toArray(draft).includes(opt.value!)
            : (draft ?? null) === opt.value;

          const controlClass = selected
            ? styles.checkSelected
            : styles.checkUnselected;

          return (
            <button
              key={String(opt.value)}
              type="button"
              className={styles.row}
              onClick={() => toggle(opt.value!)}
              role={multiple ? "checkbox" : "radio"}
              aria-checked={selected}
            >
              <span className={styles.label}>{opt.label}</span>
              <span
                className={`${controlClass} ${multiple ? "" : styles.selectedRadio}`}
                aria-hidden="true"
              />
            </button>
          );
        })}
      </div>
    </BottomSheet>
  );
}
