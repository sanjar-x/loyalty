'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import useProductForm from '@/hooks/useProductForm';
import useImageUpload from '@/hooks/useImageUpload';
import useSubmitProduct from '@/hooks/useSubmitProduct';
import { i18n } from '@/lib/utils';
import { fetchFormAttributes } from '@/services/attributes';

const fmtPrice = (v) =>
  v ? new Intl.NumberFormat('ru-RU').format(Number(v)) : '';
import BrandSelect from './BrandSelect';
import ProductPreviewCard from './ProductPreviewCard';
import SupplierSection from './SupplierSection';
import DynamicAttributes from './DynamicAttributes';
import ImagesSection from './ImagesSection';
import SizeTableSection from './SizeTableSection';
import ToggleSwitch from './ToggleSwitch';
import VariantSelect from './VariantSelect';
import styles from './page.module.css';

export default function ProductDetailsForm({
  leafLabel,
  categoryId,
  breadcrumbs,
}) {
  const router = useRouter();
  const form = useProductForm({ categoryId, defaultTitle: leafLabel });
  const imageUpload = useImageUpload();
  const submit = useSubmitProduct();

  // Uploads in progress — block submit while images are being processed
  const uploadsInProgress = form.state.images.some((img) => {
    const s = imageUpload.uploads[img.localId]?.status;
    return s === 'uploading' || s === 'processing';
  });

  const hasFailedUploads = form.state.images.some(
    (img) => imageUpload.uploads[img.localId]?.status === 'failed',
  );

  const errorRef = useRef(null);

  useEffect(() => {
    if (submit.error) {
      errorRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [submit.error]);

  async function handleSubmit(mode) {
    const result = await submit.execute(form, mode, imageUpload.uploads);
    if (result?.productId && !result.error) {
      router.push('/admin/products');
    }
  }

  // Image handlers: add → start upload, remove → clean up, crop → re-upload
  const handleImageAdd = useCallback(
    (image) => {
      form.addImage(image);
      imageUpload.startUpload(image).catch(() => {});
    },
    [form, imageUpload],
  );

  const handleImageRemove = useCallback(
    (localId) => {
      form.removeImage(localId);
      imageUpload.removeUpload(localId);
    },
    [form.removeImage, imageUpload.removeUpload],
  );

  const handleImageCropped = useCallback(
    (newImage) => {
      imageUpload.startUpload(newImage).catch(() => {});
    },
    [imageUpload],
  );

  const handleImageRetry = useCallback(
    (image) => {
      imageUpload.startUpload(image).catch(() => {});
    },
    [imageUpload],
  );

  // Load form-attributes once, share between DynamicAttributes and VariantSelect
  const [formData, setFormData] = useState(null);
  const [attrsLoading, setAttrsLoading] = useState(true);
  const [attrsError, setAttrsError] = useState(false);

  useEffect(() => {
    if (!categoryId) {
      setAttrsLoading(false);
      return;
    }
    setAttrsLoading(true);
    setAttrsError(false);
    fetchFormAttributes(categoryId)
      .then((data) => setFormData(data))
      .catch(() => setAttrsError(true))
      .finally(() => setAttrsLoading(false));
  }, [categoryId]);

  // Split attributes by level
  const allAttrs = formData?.groups?.flatMap((g) => g.attributes) ?? [];
  const variantAttrs = allAttrs.filter((a) => a.level === 'variant');

  // Check required product-level attributes are filled
  const requiredAttrsMissing = useMemo(() => {
    if (!formData) return false;
    const attrs = formData.groups?.flatMap((g) => g.attributes) ?? [];
    return attrs
      .filter((a) => a.requirementLevel === 'required' && a.level !== 'variant')
      .some((a) => !form.allAttrValues[a.attributeId]?.length);
  }, [formData, form.allAttrValues]);

  // Collect selected variant values for variable pricing rows
  const selectedVariantValues = variantAttrs.flatMap((attr) => {
    const selectedIds = form.state.variantAttrs[attr.attributeId] ?? [];
    return (attr.values ?? [])
      .filter((v) => selectedIds.includes(v.id))
      .map((v) => ({ ...v, attrName: i18n(attr.nameI18N, attr.code) }));
  });

  return (
    <div className={styles.layout}>
      <div className={styles.mainColumn}>
        {breadcrumbs}

        <div
          aria-busy={submit.submitting}
          style={
            submit.submitting
              ? { pointerEvents: 'none', opacity: 0.7 }
              : undefined
          }
        >
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

              <VariantSelect
                attributes={variantAttrs}
                values={form.state.variantAttrs}
                onChange={(attrId, valueIds) =>
                  form.setVariantAttr(attrId, valueIds)
                }
                loading={attrsLoading}
              />
            </div>
          </section>

          {attrsError ? (
            <section className={styles.card}>
              <p className={styles.errorText}>Не удалось загрузить атрибуты</p>
              <button
                type="button"
                className={styles.secondaryButton}
                onClick={() => {
                  setAttrsLoading(true);
                  setAttrsError(false);
                  fetchFormAttributes(categoryId)
                    .then((data) => setFormData(data))
                    .catch(() => setAttrsError(true))
                    .finally(() => setAttrsLoading(false));
                }}
                style={{ marginTop: 8 }}
              >
                Повторить
              </button>
            </section>
          ) : (
            <DynamicAttributes
              formData={formData}
              loading={attrsLoading}
              values={form.allAttrValues}
              onChange={(attrId, selectedValues, level) =>
                form.handleAttributeUpdate(attrId, selectedValues, level)
              }
              excludeLevel="variant"
            />
          )}

          <SizeTableSection
            value={form.state.sizeGuide}
            onChange={(val) => form.setField('sizeGuide', val)}
          />

          <ImagesSection
            images={form.state.images}
            onAdd={handleImageAdd}
            onRemove={handleImageRemove}
            onSet={form.setImages}
            uploads={imageUpload.uploads}
            onRetry={handleImageRetry}
            onImageCropped={handleImageCropped}
          />

          <section className={styles.card}>
            <div className={styles.cardTitleRow}>
              <h2 className={styles.cardTitle}>Оригинал</h2>
              <ToggleSwitch
                ariaLabel="Переключить оригинал"
                checked={form.state.isOriginal}
                onChange={(val) => form.setField('isOriginal', val)}
              />
            </div>
          </section>

          <SupplierSection
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
                {selectedVariantValues.length > 0 ? (
                  selectedVariantValues.map((val) => (
                    <div key={val.id} className={styles.priceVariableRow}>
                      <div className={styles.priceSizeBadge}>
                        {i18n(val.valueI18N, val.code)}
                      </div>
                      <input
                        className={styles.priceVariableInput}
                        placeholder="Цена"
                        aria-label={`Цена ${i18n(val.valueI18N, val.code)}`}
                        inputMode="decimal"
                        value={fmtPrice(form.state.perSkuPrices[val.id]?.price)}
                        onChange={(e) =>
                          form.setSkuPrice(val.id, {
                            price: e.target.value.replace(/[^0-9]/g, ''),
                          })
                        }
                      />
                      <input
                        className={styles.priceVariableInput}
                        placeholder="Закупочная цена"
                        aria-label={`Закупочная цена ${i18n(val.valueI18N, val.code)}`}
                        inputMode="decimal"
                        value={fmtPrice(
                          form.state.perSkuPrices[val.id]?.compareAt,
                        )}
                        onChange={(e) =>
                          form.setSkuPrice(val.id, {
                            compareAt: e.target.value.replace(/[^0-9]/g, ''),
                          })
                        }
                      />
                    </div>
                  ))
                ) : (
                  <p className={styles.cardSubtitle}>
                    Выберите размеры выше для вариативных цен
                  </p>
                )}
              </div>
            ) : (
              <div className={styles.fieldRow}>
                <div className={styles.floatingField}>
                  <label className={styles.floatingLabel}>Цена</label>
                  <input
                    className={styles.floatingInput}
                    aria-label="Цена"
                    inputMode="decimal"
                    value={fmtPrice(form.state.priceAmount)}
                    onChange={(e) => {
                      const v = e.target.value.replace(/[^0-9]/g, '');
                      form.setField('priceAmount', v);
                    }}
                  />
                </div>
                <input
                  className={styles.input}
                  placeholder="Закупочная цена"
                  aria-label="Закупочная цена"
                  inputMode="decimal"
                  value={fmtPrice(form.state.compareAtPrice)}
                  onChange={(e) => {
                    const v = e.target.value.replace(/[^0-9]/g, '');
                    form.setField('compareAtPrice', v);
                  }}
                />
              </div>
            )}
          </section>

          {/* Submit section */}
          {submit.error && (
            <div className={styles.card} ref={errorRef}>
              <p className={styles.errorText}>
                {submit.error.code === 'MEDIA_PARTIAL_FAILURE'
                  ? `${submit.error.message} Вы можете отредактировать продукт позже.`
                  : submit.error.code === 'ZERO_SKUS'
                    ? 'Не удалось сгенерировать варианты (SKU). Проверьте выбранные атрибуты.'
                    : submit.error.code === 'TIMEOUT'
                      ? 'Сервер не отвечает. Проверьте соединение и попробуйте позже.'
                      : submit.error.code === 'RATE_LIMITED'
                        ? 'Слишком много запросов. Подождите и попробуйте снова.'
                        : `Ошибка: ${submit.error.message}`}
              </p>
              {submit.createdProductId && (
                <p className={styles.cardSubtitle}>
                  Продукт был создан. Вы можете отредактировать его позже.
                </p>
              )}
              <button
                type="button"
                className={styles.secondaryButton}
                onClick={submit.clearError}
                style={{ marginTop: 8 }}
              >
                Закрыть
              </button>
            </div>
          )}

          {submit.submitting && (
            <div className={styles.card}>
              <p className={styles.cardSubtitle}>{submit.progress}</p>
            </div>
          )}

          <div className={styles.actions}>
            <button
              type="button"
              className={styles.secondaryButton}
              disabled={
                !form.isValid ||
                submit.submitting ||
                uploadsInProgress ||
                hasFailedUploads
              }
              onClick={() => handleSubmit('draft')}
            >
              {submit.submitting
                ? submit.progress
                : uploadsInProgress
                  ? 'Загрузка фото...'
                  : hasFailedUploads
                    ? 'Есть ошибки загрузки'
                    : 'Сохранить черновик'}
            </button>
            <button
              type="button"
              className={styles.primaryButton}
              disabled={
                !form.isPublishable ||
                submit.submitting ||
                uploadsInProgress ||
                hasFailedUploads ||
                requiredAttrsMissing
              }
              onClick={() => handleSubmit('publish')}
            >
              {submit.submitting
                ? submit.progress
                : uploadsInProgress
                  ? 'Загрузка фото...'
                  : hasFailedUploads
                    ? 'Есть ошибки загрузки'
                    : requiredAttrsMissing
                      ? 'Заполните обязательные поля'
                      : 'На модерацию'}
            </button>
          </div>
        </div>
      </div>

      {/* Sidebar */}
      <aside className={styles.sidebar}>
        <ProductPreviewCard
          title={form.state.titleRu || leafLabel}
          brandName={form.state.brandName}
          price={form.state.priceAmount}
          images={form.state.images}
          uploads={imageUpload.uploads}
          isOriginal={form.state.isOriginal}
        />
      </aside>
    </div>
  );
}
