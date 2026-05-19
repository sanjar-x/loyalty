'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  createSupplier,
  supplierKeys,
  useSuppliers,
} from '@/entities/supplier';
import CountrySelect from './CountrySelect';
import SubdivisionSelect from './SubdivisionSelect';
import { ChevronIcon } from './icons';
import styles from './styles/productForm.module.css';

// Backend SupplierResponse.type values (snake_case enum).
const SUPPLIER_TYPES = {
  CROSS_BORDER: 'cross_border',
  LOCAL: 'local',
};

// Visual filter tabs over the supplier list. Each tab maps directly to
// the backend `SupplierType` enum — we don't keep a separate "delivery
// mode" field on the product form (the supplier is the source of
// truth). The filter is local UI state and is initialised from the
// already-selected supplier when the form hydrates.
const SUPPLIER_TYPE_FILTERS = [
  { value: SUPPLIER_TYPES.CROSS_BORDER, label: 'Трансграничный' },
  { value: SUPPLIER_TYPES.LOCAL, label: 'Локальный' },
];

const SUPPLIER_TYPE_LABELS = {
  [SUPPLIER_TYPES.CROSS_BORDER]: 'Трансграничный (cross-border)',
  [SUPPLIER_TYPES.LOCAL]: 'Локальный (local)',
};

function getSupplierRegion(supplier) {
  return supplier.region ?? supplier.countryCode ?? '';
}

function PlusIcon() {
  return (
    <svg
      width="30"
      height="30"
      viewBox="0 0 30 30"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M15 6.25C15.5178 6.25 15.9375 6.66973 15.9375 7.1875V14.0625H22.8125C23.3303 14.0625 23.75 14.4822 23.75 15C23.75 15.5178 23.3303 15.9375 22.8125 15.9375H15.9375V22.8125C15.9375 23.3303 15.5178 23.75 15 23.75C14.4822 23.75 14.0625 23.3303 14.0625 22.8125V15.9375H7.1875C6.66973 15.9375 6.25 15.5178 6.25 15C6.25 14.4822 6.66973 14.0625 7.1875 14.0625H14.0625V7.1875C14.0625 6.66973 14.4822 6.25 15 6.25Z"
        fill="black"
      />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg
      width="30"
      height="30"
      viewBox="0 0 30 30"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M7.2728 6.21214C6.9799 5.91924 6.50503 5.91924 6.21214 6.21214C5.91924 6.50503 5.91924 6.9799 6.21214 7.2728L13.9393 15L6.21214 22.7272C5.91924 23.0201 5.91924 23.495 6.21214 23.7879C6.50503 24.0808 6.9799 24.0808 7.2728 23.7879L15 16.0607L22.7272 23.7879C23.0201 24.0808 23.495 24.0808 23.7879 23.7879C24.0808 23.495 24.0808 23.0201 23.7879 22.7272L16.0607 15L23.7879 7.2728C24.0808 6.9799 24.0808 6.50503 23.7879 6.21214C23.495 5.91924 23.0201 5.91924 22.7272 6.21214L15 13.9393L7.2728 6.21214Z"
        fill="black"
      />
    </svg>
  );
}

/**
 * Supplier selection section — controlled component.
 *
 * Props:
 *   sourceUrl: string
 *   onSourceUrlChange: (url) => void
 *   supplierId: string | null
 *   onSupplierChange: (supplierId) => void
 *
 * Cross-border vs local is *derived* from the selected supplier's
 * `type` field (backend SupplierType enum). We don't store a separate
 * delivery-mode flag on the product — that used to exist as a
 * frontend-only field but it duplicated the supplier choice and led to
 * desync bugs (purchase currency stuck on CNY after a local supplier
 * was picked).
 *
 * «Оригинал» (`isOriginal`) is similarly derived in the parent — a
 * product is "оригинал" iff its supplier is Poizon. There's no
 * separate boolean flag and no two-way binding to maintain here.
 */

export default function SupplierSection({
  sourceUrl = '',
  onSourceUrlChange,
  supplierId = null,
  onSupplierChange,
}) {
  // Supplier dropdown state
  const queryClient = useQueryClient();
  const [supplierOpen, setSupplierOpen] = useState(false);
  const {
    data: suppliersData,
    isPending: suppliersInitialLoading,
    isError: suppliersLoadError,
    refetch: refetchSuppliers,
  } = useSuppliers();
  const suppliers = useMemo(() => suppliersData?.items ?? [], [suppliersData]);
  const suppliersLoading = suppliersInitialLoading && !suppliersData;
  const supplierRef = useRef(null);

  // Derive selected supplier from supplierId + loaded list
  const selectedSupplier = supplierId
    ? (suppliers.find((s) => s.id === supplierId) ?? null)
    : null;

  // Visual filter for the supplier dropdown — purely UI state. Seeded
  // from the currently-selected supplier's type so the dropdown opens
  // already filtered to the right segment; defaults to cross-border
  // for fresh products because that's the more common case.
  const [typeFilter, setTypeFilter] = useState(
    selectedSupplier?.type ?? SUPPLIER_TYPES.CROSS_BORDER,
  );

  // When the selected supplier's type doesn't match the active filter
  // (e.g. user picked Poizon while the filter was on «Локальный»), snap
  // the filter to the supplier's type so the dropdown stays consistent.
  useEffect(() => {
    if (selectedSupplier && selectedSupplier.type !== typeFilter) {
      setTypeFilter(selectedSupplier.type);
    }
  }, [selectedSupplier, typeFilter]);

  const filteredSuppliers = useMemo(
    () => suppliers.filter((s) => s.type === typeFilter),
    [suppliers, typeFilter],
  );

  // Create supplier modal state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newSupplierName, setNewSupplierName] = useState('');
  const [newCountryCode, setNewCountryCode] = useState('');
  const [newSubdivisionCode, setNewSubdivisionCode] = useState('');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState('');
  const supplierModalRef = useRef(null);

  // Source URL focus state
  const [urlFocused, setUrlFocused] = useState(false);

  const isFormComplete = Boolean(newSupplierName.trim() && newCountryCode);

  // Plain delegation — there's no separate "isOriginal" flag to keep
  // in sync; the parent derives it from the selected supplier.
  function applySupplierChange(nextSupplierId) {
    onSupplierChange?.(nextSupplierId);
  }

  // Close dropdown on outside click
  useEffect(() => {
    if (!supplierOpen) return;
    function handleClickOutside(e) {
      if (supplierRef.current && !supplierRef.current.contains(e.target)) {
        setSupplierOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [supplierOpen]);

  // Modal focus trap
  useEffect(() => {
    if (!isAddModalOpen) return;
    const modal = supplierModalRef.current;
    if (!modal) return;

    function handleTabTrap(e) {
      if (e.key !== 'Tab') return;
      const focusable = modal.querySelectorAll(
        'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }

    modal.addEventListener('keydown', handleTabTrap);
    const firstFocusable = modal.querySelector('input, select, button');
    firstFocusable?.focus();

    return () => modal.removeEventListener('keydown', handleTabTrap);
  }, [isAddModalOpen]);

  function openAddModal() {
    setSupplierOpen(false);
    setNewSupplierName('');
    setNewCountryCode('');
    setNewSubdivisionCode('');
    setCreateError('');
    setIsAddModalOpen(true);
  }

  function closeAddModal() {
    setIsAddModalOpen(false);
  }

  async function handleCreateSupplier() {
    if (!newSupplierName.trim() || !newCountryCode || creating) return;
    setCreating(true);
    setCreateError('');

    // Ad-hoc creation is only enabled for local suppliers (see the
    // conditional on the «Добавить поставщика» button below), so the
    // type is fixed here. Cross-border accounts live in the central
    // upstream registry and must be added via the suppliers settings
    // screen, not from the product form.
    const supplierType = SUPPLIER_TYPES.LOCAL;

    try {
      const result = await createSupplier({
        name: newSupplierName.trim(),
        type: supplierType,
        countryCode: newCountryCode,
        ...(newSubdivisionCode ? { subdivisionCode: newSubdivisionCode } : {}),
      });

      // Optimistic insert into cache so the new supplier shows up in the
      // dropdown immediately, without waiting for the refetch round-trip.
      const newSupplier = {
        id: result.id,
        name: newSupplierName.trim(),
        type: supplierType,
        countryCode: newCountryCode,
        subdivisionCode: newSubdivisionCode || null,
        isActive: true,
      };
      queryClient.setQueryData(supplierKeys.lists(), (prev) => {
        const items = prev?.items ?? [];
        return {
          ...prev,
          items: [...items, newSupplier],
          total: (prev?.total ?? items.length) + 1,
        };
      });
      // Background refetch reconciles with the canonical server response
      // (slug normalization, server-assigned timestamps, etc.).
      queryClient.invalidateQueries({ queryKey: supplierKeys.all });

      // Newly-created supplier — never Poizon (unique by name in the
      // registry), so the binding helper will turn the Original flag off.
      applySupplierChange(result.id);

      // Reset modal
      setNewSupplierName('');
      setNewCountryCode('');
      setNewSubdivisionCode('');
      setIsAddModalOpen(false);
    } catch (err) {
      setCreateError(err.message);
    } finally {
      setCreating(false);
    }
  }

  function handleUrlKeyDown(event) {
    if (event.key === 'Enter') {
      event.preventDefault();
    }
  }

  // Cross-border suppliers (Poizon / JD / etc.) source from an external
  // marketplace URL — local suppliers don't have one.
  const showSourceUrl =
    selectedSupplier?.type === SUPPLIER_TYPES.CROSS_BORDER ||
    (!selectedSupplier && typeFilter === SUPPLIER_TYPES.CROSS_BORDER);

  return (
    <section className={styles.card}>
      <h2 className={styles.cardTitle}>Поставщик</h2>
      <div className={styles.fieldGroup}>
        {/* Supplier-type filter tabs — UI only, do not write to form state.
            The actual supplier type flows from the selected supplier on
            submit; these tabs just narrow the dropdown. */}
        <div
          className={styles.segmented}
          role="tablist"
          aria-label="Тип поставщика"
        >
          {SUPPLIER_TYPE_FILTERS.map((option) => {
            const isActive = option.value === typeFilter;
            return (
              <button
                key={option.value}
                type="button"
                role="tab"
                aria-selected={isActive}
                className={isActive ? styles.segmentActive : styles.segment}
                onClick={() => setTypeFilter(option.value)}
              >
                {option.label}
              </button>
            );
          })}
        </div>

        {/* Supplier dropdown */}
        <div className={styles.brandSelect} ref={supplierRef}>
          <button
            type="button"
            className={styles.brandSelectTrigger}
            aria-haspopup="listbox"
            aria-expanded={supplierOpen}
            onClick={() => setSupplierOpen((c) => !c)}
          >
            <span className={styles.brandSelectValue}>
              {selectedSupplier
                ? `${selectedSupplier.name} · ${getSupplierRegion(selectedSupplier)}`
                : 'Поставщик'}
            </span>
            <span className={styles.selectChevron}>
              <ChevronIcon />
            </span>
          </button>

          {supplierOpen ? (
            <div
              className={styles.brandDropdown}
              role="listbox"
              aria-label="Список поставщиков"
            >
              <div className={styles.brandDropdownScrollArea}>
                {suppliersLoading ? (
                  <div className={styles.brandSectionHeader}>Загрузка…</div>
                ) : suppliersLoadError ? (
                  <div className="px-4 py-3 text-center">
                    <p className="text-app-danger mb-2 text-[13px]">
                      Не удалось загрузить поставщиков
                    </p>
                    <button
                      type="button"
                      className="border-app-border bg-app-panel hover:bg-app-card cursor-pointer rounded-md border px-3 py-1.5 text-[13px]"
                      onClick={() => refetchSuppliers()}
                    >
                      Повторить
                    </button>
                  </div>
                ) : filteredSuppliers.length === 0 ? (
                  <div className={styles.brandSectionHeader}>
                    Нет поставщиков
                  </div>
                ) : (
                  filteredSuppliers.map((supplier) => {
                    const isSelected = supplierId === supplier.id;
                    return (
                      <button
                        key={supplier.id}
                        type="button"
                        className={styles.brandOption}
                        role="option"
                        aria-selected={isSelected}
                        onClick={() => {
                          applySupplierChange(supplier.id);
                          setSupplierOpen(false);
                        }}
                      >
                        <div className={styles.brandOptionMain}>
                          <span className={styles.brandOptionName}>
                            {supplier.name} · {getSupplierRegion(supplier)}
                          </span>
                        </div>
                        <span
                          className={styles.brandOptionCheck}
                          aria-hidden="true"
                        >
                          {isSelected ? (
                            <span className={styles.brandOptionCheckInner} />
                          ) : null}
                        </span>
                      </button>
                    );
                  })
                )}
              </div>

              {/* Manual supplier creation is only meaningful for local
                  suppliers — cross-border accounts must come from the
                  central upstream registry (Poizon/JD broker accounts)
                  and can't be entered ad-hoc from the product form. */}
              {typeFilter === SUPPLIER_TYPES.LOCAL && (
                <button
                  type="button"
                  className={styles.brandAddButton}
                  onClick={openAddModal}
                >
                  <span className={styles.brandAddIcon}>
                    <PlusIcon />
                  </span>
                  <span>Добавить поставщика</span>
                </button>
              )}
            </div>
          ) : null}

          {/* Create supplier modal */}
          {isAddModalOpen ? (
            <div
              className={styles.brandModalOverlay}
              role="presentation"
              onClick={closeAddModal}
            >
              <div
                ref={supplierModalRef}
                className={styles.brandModal}
                role="dialog"
                aria-modal="true"
                aria-labelledby="supplier-modal-title"
                onClick={(event) => event.stopPropagation()}
              >
                <div className={styles.brandModalHeader}>
                  <h3
                    id="supplier-modal-title"
                    className={styles.brandModalTitle}
                  >
                    Добавление поставщика
                  </h3>
                  <button
                    type="button"
                    className={styles.brandModalClose}
                    aria-label="Закрыть окно добавления поставщика"
                    onClick={closeAddModal}
                  >
                    <CloseIcon />
                  </button>
                </div>

                <div className={styles.brandModalBody}>
                  <input
                    className={styles.brandModalInput}
                    placeholder="Название поставщика"
                    value={newSupplierName}
                    onChange={(event) => {
                      setNewSupplierName(event.target.value);
                      setCreateError('');
                    }}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') {
                        event.preventDefault();
                        handleCreateSupplier();
                      }
                    }}
                    autoFocus
                  />

                  <CountrySelect
                    value={newCountryCode}
                    onChange={(code) => {
                      setNewCountryCode(code);
                      setNewSubdivisionCode('');
                      setCreateError('');
                    }}
                  />

                  <SubdivisionSelect
                    countryCode={newCountryCode}
                    value={newSubdivisionCode}
                    onChange={(code) => {
                      setNewSubdivisionCode(code);
                      setCreateError('');
                    }}
                  />

                  <div className={styles.supplierTypeHint}>
                    Тип: {SUPPLIER_TYPE_LABELS[SUPPLIER_TYPES.LOCAL]}
                    {' — '}
                    локальные поставщики создаются прямо из формы товара
                  </div>

                  {createError && (
                    <p className="text-app-danger m-0 mt-1 text-[13px]">
                      {createError}
                    </p>
                  )}
                </div>

                <div className={styles.brandModalActions}>
                  <button
                    type="button"
                    className={styles.brandModalPrimaryButton}
                    disabled={!isFormComplete || creating}
                    onClick={handleCreateSupplier}
                  >
                    {creating ? 'Создание...' : 'Добавить поставщика'}
                  </button>
                </div>
              </div>
            </div>
          ) : null}
        </div>

        {/* Source URL — only for cross-border suppliers */}
        {showSourceUrl && (
          <div
            className={
              urlFocused
                ? styles.sizeTableUrlFieldFocused
                : styles.sizeTableUrlField
            }
          >
            <span className={styles.sizeTableUrlLabel}>Ссылка на источник</span>
            <input
              className={styles.sizeTableUrlInput}
              value={sourceUrl}
              onChange={(event) => onSourceUrlChange?.(event.target.value)}
              onFocus={() => setUrlFocused(true)}
              onBlur={() => setUrlFocused(false)}
              onKeyDown={handleUrlKeyDown}
              placeholder="https://poizon.com/..."
              aria-label="Ссылка на товар у поставщика"
            />
          </div>
        )}
      </div>
    </section>
  );
}
