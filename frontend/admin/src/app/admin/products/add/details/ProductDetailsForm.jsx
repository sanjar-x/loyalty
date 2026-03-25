'use client';

import useProductForm from '@/hooks/useProductForm';
import BrandSelect from './BrandSelect';
import DeliverySection from './DeliverySection';
import DynamicAttributes from './DynamicAttributes';
import ImagesSection from './ImagesSection';
import SizeSelect from './SizeSelect';
import SizeTableSection from './SizeTableSection';
import ToggleSwitch from './ToggleSwitch';
import styles from './page.module.css';

export default function ProductDetailsForm({ leafLabel, categoryId }) {
  const form = useProductForm({ categoryId, defaultTitle: leafLabel });

  return (
    <>
      <section className={styles.card}>
        <h2 className={styles.cardTitle}>Основные данные</h2>
        <div className={styles.fieldGroup}>
          <BrandSelect
            value={form.state.brandId}
            onChange={(brand) => form.setBrandId(brand.id, brand.name)}
          />

          <div className={styles.floatingField}>
            <label className={styles.floatingLabel}>Название</label>
            <input
              className={styles.floatingInput}
              value={form.state.titleRu}
              onChange={(e) => form.setTitleRu(e.target.value)}
            />
          </div>

          <SizeSelect
            value={form.state.variantAttrs}
            onChange={(attrId, valueIds) => form.setVariantAttr(attrId, valueIds)}
            categoryId={categoryId}
          />
        </div>
      </section>

      <DynamicAttributes
        categoryId={categoryId}
        values={form.allAttrValues}
        onChange={(attrId, selectedValues, level) =>
          form.handleAttributeUpdate(attrId, selectedValues, level)
        }
      />

      <SizeTableSection />

      <ImagesSection
        images={form.state.images}
        onAdd={form.addImage}
        onRemove={form.removeImage}
        onSet={form.setImages}
      />

      <section className={styles.card}>
        <div className={styles.switchRow}>
          <h2 className={styles.switchLabel}>Оригинал</h2>
          <ToggleSwitch
            ariaLabel="Переключить оригинальность товара"
            checked={form.state.isOriginal}
            onChange={(val) => form.setField('isOriginal', val)}
          />
        </div>
      </section>

      <DeliverySection
        deliveryMode={form.state.deliveryMode}
        onDeliveryModeChange={(val) => form.setField('deliveryMode', val)}
        sourceUrl={form.state.sourceUrl}
        onSourceUrlChange={(val) => form.setField('sourceUrl', val)}
        supplierId={form.state.supplierId}
        onSupplierChange={(val) => form.setField('supplierId', val)}
      />

      <section className={styles.card}>
        <div className={styles.cardTitleRow}>
          <h2 className={styles.cardTitle}>Цена</h2>
          <div className={styles.toggleRow}>
            <span className={styles.toggleLabel}>Вариативная</span>
            <ToggleSwitch
              ariaLabel="Переключить вариативную цену"
              checked={form.state.variablePricing}
              onChange={(val) => form.setField('variablePricing', val)}
            />
          </div>
        </div>

        {form.state.variablePricing ? (
          <div className={styles.priceVariableList}>
            {/* TODO: iterate over selected variant values from form-attributes */}
            <p className={styles.cardSubtitle}>
              Выберите размеры выше для вариативных цен
            </p>
          </div>
        ) : (
          <div className={styles.fieldRow}>
            <input
              className={styles.input}
              placeholder="Цена"
              aria-label="Цена"
              value={form.state.priceAmount}
              onChange={(e) => form.setField('priceAmount', e.target.value)}
            />
            <input
              className={styles.input}
              placeholder="Закупочная цена"
              aria-label="Закупочная цена"
              value={form.state.compareAtPrice}
              onChange={(e) => form.setField('compareAtPrice', e.target.value)}
            />
          </div>
        )}
      </section>
    </>
  );
}
