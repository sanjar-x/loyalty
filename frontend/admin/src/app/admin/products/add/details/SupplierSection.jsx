'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { fetchSuppliers } from '@/services/suppliers';
import { ArrowIcon, ChevronIcon } from './icons';
import styles from './page.module.css';

// Map UI delivery mode → backend supplier type
const DELIVERY_TYPE_MAP = {
  china: 'cross_border',
  stock: 'local',
};

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
  const supplierRef = useRef(null);

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

  // Auto-reset supplier when delivery mode changes and current supplier doesn't match
  useEffect(() => {
    if (!supplierId || !suppliersLoaded) return;
    const current = suppliers.find((s) => s.id === supplierId);
    if (current && expectedType && current.type !== expectedType) {
      onSupplierChange?.(null);
    }
  }, [deliveryMode]); // eslint-disable-line react-hooks/exhaustive-deps — intentional: only react to deliveryMode changes, other deps are read from current closure

  const loadSuppliers = useCallback(async () => {
    if (suppliersLoaded || suppliersLoading) return;
    setSuppliersLoading(true);
    try {
      const data = await fetchSuppliers();
      setSuppliers(data.items ?? []);
      setSuppliersLoaded(true);
    } catch (err) {
      console.error('[SupplierSection] Failed to load suppliers:', err);
    } finally {
      setSuppliersLoading(false);
    }
  }, [suppliersLoaded, suppliersLoading]);

  // Eager load suppliers on mount
  useEffect(() => {
    loadSuppliers();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps — mount-only: loadSuppliers is guarded by suppliersLoaded flag internally

  // Close dropdown on outside click / escape
  useEffect(() => {
    if (!supplierOpen) return;

    function handlePointerDown(event) {
      if (!supplierRef.current?.contains(event.target)) setSupplierOpen(false);
    }
    function handleEscape(event) {
      if (event.key === 'Escape') setSupplierOpen(false);
    }

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [supplierOpen]);

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
                ? `${selectedSupplier.name} · ${selectedSupplier.region}`
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
                            {supplier.name} · {supplier.region}
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
