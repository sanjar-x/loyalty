'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { fetchSuppliers, createSupplier } from '@/services/suppliers';
import CountrySelect from './CountrySelect';
import SubdivisionSelect from './SubdivisionSelect';
import { ChevronIcon } from './icons';
import styles from './page.module.css';

// Map UI delivery mode → backend supplier type
const DELIVERY_TYPE_MAP = {
  china: 'cross_border',
  stock: 'local',
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
 *   deliveryMode: "china" | "stock"
 *   onDeliveryModeChange: (mode) => void
 *   sourceUrl: string
 *   onSourceUrlChange: (url) => void
 *   supplierId: string | null
 *   onSupplierChange: (supplierId) => void
 */

const DELIVERY_OPTIONS = [
  { value: 'china', label: 'Из Китая' },
  { value: 'stock', label: 'Из наличия' },
];

export default function SupplierSection({
  deliveryMode = 'china',
  onDeliveryModeChange,
  sourceUrl = '',
  onSourceUrlChange,
  supplierId = null,
  onSupplierChange,
}) {
  // Supplier dropdown state
  const [supplierOpen, setSupplierOpen] = useState(false);
  const [suppliers, setSuppliers] = useState([]);
  const [suppliersLoading, setSuppliersLoading] = useState(false);
  const [suppliersLoaded, setSuppliersLoaded] = useState(false);
  const [suppliersLoadError, setSuppliersLoadError] = useState(false);
  const supplierRef = useRef(null);

  // Create supplier modal state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newSupplierName, setNewSupplierName] = useState('');
  const [newCountryCode, setNewCountryCode] = useState('');
  const [newSubdivisionCode, setNewSubdivisionCode] = useState('');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState('');
  const supplierModalRef = useRef(null); // #14 — focus trap ref

  // Source URL focus state
  const [urlFocused, setUrlFocused] = useState(false);

  // Filter suppliers by type matching current delivery mode
  const expectedType = DELIVERY_TYPE_MAP[deliveryMode] ?? null;
  const filteredSuppliers = useMemo(
    () =>
      expectedType
        ? suppliers.filter((s) => s.type === expectedType)
        : suppliers,
    [suppliers, expectedType],
  );

  // Derive selected supplier from supplierId + loaded list
  const selectedSupplier = supplierId
    ? (suppliers.find((s) => s.id === supplierId) ?? null)
    : null;

  const isFormComplete = Boolean(newSupplierName.trim() && newCountryCode);

  // Auto-reset supplier when delivery mode changes and current supplier doesn't match
  useEffect(() => {
    if (!supplierId || !suppliersLoaded) return;
    const current = suppliers.find((s) => s.id === supplierId);
    if (current && expectedType && current.type !== expectedType) {
      onSupplierChange?.(null);
    }
  }, [deliveryMode]); // eslint-disable-line react-hooks/exhaustive-deps — intentional: only react to deliveryMode changes, other deps are read from current closure

  const loadSuppliers = useCallback(async (force = false) => {
    if (!force && (suppliersLoaded || suppliersLoading)) return;
    setSuppliersLoading(true);
    setSuppliersLoadError(false);
    try {
      const data = await fetchSuppliers();
      setSuppliers(data.items ?? []);
      setSuppliersLoaded(true);
    } catch {
      setSuppliersLoadError(true);
    } finally {
      setSuppliersLoading(false);
    }
  }, [suppliersLoaded, suppliersLoading]);

  // Eager load suppliers on mount
  useEffect(() => {
    loadSuppliers();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps — mount-only: loadSuppliers is guarded by suppliersLoaded flag internally

  // Close dropdown and modal on outside click / escape
  useEffect(() => {
    if (!supplierOpen && !isAddModalOpen) return;

    function handlePointerDown(event) {
      if (!supplierRef.current?.contains(event.target)) {
        setSupplierOpen(false);
        setIsAddModalOpen(false);
      }
    }
    function handleEscape(event) {
      if (event.key === 'Escape') {
        setIsAddModalOpen(false);
        setSupplierOpen(false);
      }
    }

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [supplierOpen, isAddModalOpen]);

  // #14 — Focus trap for supplier creation modal
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

    const supplierType = DELIVERY_TYPE_MAP[deliveryMode] ?? 'cross_border';

    try {
      const result = await createSupplier({
        name: newSupplierName.trim(),
        type: supplierType,
        countryCode: newCountryCode,
        ...(newSubdivisionCode ? { subdivisionCode: newSubdivisionCode } : {}),
      });

      // Build a local supplier object matching SupplierResponse shape
      const newSupplier = {
        id: result.id,
        name: newSupplierName.trim(),
        type: supplierType,
        countryCode: newCountryCode,
        subdivisionCode: newSubdivisionCode || null,
        isActive: true,
      };

      setSuppliers((prev) => [...prev, newSupplier]);
      onSupplierChange?.(result.id);

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

  const showSourceUrl = deliveryMode === 'china';

  return (
    <section className={styles.card}>
      <h2 className={styles.cardTitle}>Доставка</h2>
      <div className={styles.fieldGroup}>
        {/* Delivery mode tabs */}
        <div
          className={styles.segmented}
          role="tablist"
          aria-label="Способ доставки"
        >
          {DELIVERY_OPTIONS.map((option) => {
            const isActive = option.value === deliveryMode;
            return (
              <button
                key={option.value}
                type="button"
                role="tab"
                aria-selected={isActive}
                className={isActive ? styles.segmentActive : styles.segment}
                onClick={() => onDeliveryModeChange?.(option.value)}
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
            onClick={() => {
              setSupplierOpen((c) => !c);
              loadSuppliers();
            }}
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
                  <div style={{ padding: '12px 16px', textAlign: 'center' }}>
                    <p style={{ margin: '0 0 8px', color: '#ef4444', fontSize: 13 }}>
                      Не удалось загрузить поставщиков
                    </p>
                    <button
                      type="button"
                      style={{
                        padding: '6px 12px',
                        borderRadius: 6,
                        border: '1px solid #d1d5db',
                        background: '#fff',
                        cursor: 'pointer',
                        fontSize: 13,
                      }}
                      onClick={() => loadSuppliers(true)}
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
                          onSupplierChange?.(supplier.id);
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
                    Тип:{' '}
                    {deliveryMode === 'china'
                      ? 'Трансграничный (cross-border)'
                      : 'Локальный (local)'}
                    {' — '}
                    определяется автоматически по способу доставки
                  </div>

                  {createError && (
                    <p
                      style={{
                        color: '#e53e3e',
                        fontSize: '13px',
                        margin: '4px 0 0',
                      }}
                    >
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

        {/* Source URL (only for "Из Китая" mode) */}
        {showSourceUrl ? (
          <div className={styles.sizeTableUrlRow}>
            <div
              className={
                urlFocused
                  ? styles.sizeTableUrlFieldFocused
                  : styles.sizeTableUrlField
              }
            >
              <span className={styles.sizeTableUrlLabel}>Ссылка на товар</span>
              <input
                value={sourceUrl}
                onChange={(event) => onSourceUrlChange?.(event.target.value)}
                onFocus={() => setUrlFocused(true)}
                onBlur={() => setUrlFocused(false)}
                onKeyDown={handleUrlKeyDown}
                className={styles.sizeTableUrlInput}
                aria-label="Ссылка на товар"
              />
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}
