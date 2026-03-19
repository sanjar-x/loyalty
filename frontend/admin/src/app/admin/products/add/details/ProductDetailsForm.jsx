'use client';

import { useMemo, useState } from 'react';
import BrandSelect from './BrandSelect';
import DeliverySection from './DeliverySection';
import ImagesSection from './ImagesSection';
import SizeSelect, { DEFAULT_SELECTED_SIZES, SIZE_OPTIONS } from './SizeSelect';
import SizeTableSection from './SizeTableSection';
import ToggleSwitch from './ToggleSwitch';
import styles from './page.module.css';

const SIZE_ORDER = new Map(SIZE_OPTIONS.map((size, index) => [size, index]));

function sortSizes(sizes) {
  return [...sizes].sort(
    (left, right) =>
      (SIZE_ORDER.get(left) ?? Number.MAX_SAFE_INTEGER) -
      (SIZE_ORDER.get(right) ?? Number.MAX_SAFE_INTEGER),
  );
}

export default function ProductDetailsForm({ leafLabel }) {
  const [selectedSizes, setSelectedSizes] = useState(DEFAULT_SELECTED_SIZES);
  const [variablePricing, setVariablePricing] = useState(false);

  const orderedSizes = useMemo(() => sortSizes(selectedSizes), [selectedSizes]);

  return (
    <>
      <section className={styles.card}>
        <h2 className={styles.cardTitle}>Основные данные</h2>
        <div className={styles.fieldGroup}>
          <BrandSelect />

          <div className={styles.floatingField}>
            <label className={styles.floatingLabel}>Название</label>
            <input className={styles.floatingInput} defaultValue={leafLabel} />
          </div>

          <SizeSelect value={orderedSizes} onChange={setSelectedSizes} />
        </div>
      </section>

      <SizeTableSection />

      <ImagesSection />

      <section className={styles.card}>
        <div className={styles.switchRow}>
          <h2 className={styles.switchLabel}>Оригинал</h2>
          <ToggleSwitch
            ariaLabel="Переключить оригинальность товара"
            initialChecked
          />
        </div>
      </section>

      <DeliverySection />

      <section className={styles.card}>
        <div className={styles.cardTitleRow}>
          <h2 className={styles.cardTitle}>Цена</h2>
          <div className={styles.toggleRow}>
            <span className={styles.toggleLabel}>Вариативная</span>
            <ToggleSwitch
              ariaLabel="Переключить вариативную цену"
              checked={variablePricing}
              onChange={setVariablePricing}
            />
          </div>
        </div>

        {variablePricing ? (
          <div className={styles.priceVariableList}>
            {orderedSizes.map((size) => (
              <div key={size} className={styles.priceVariableRow}>
                <div className={styles.priceSizeBadge}>{size}</div>
                <input
                  className={styles.priceVariableInput}
                  placeholder="Цена"
                  aria-label="Цена"
                />
                <input
                  className={styles.priceVariableInput}
                  placeholder="Закупочная цена"
                  aria-label="Закупочная цена"
                />
              </div>
            ))}
          </div>
        ) : (
          <div className={styles.fieldRow}>
            <input className={styles.input} placeholder="Цена" aria-label="Цена" />
            <input className={styles.input} placeholder="Закупочная цена" aria-label="Закупочная цена" />
          </div>
        )}
      </section>
    </>
  );
}
