'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import useProductForm from '@/hooks/useProductForm';
import useImageUpload from '@/hooks/useImageUpload';
import useSubmitProduct from '@/hooks/useSubmitProduct';
import useUpdateProduct from '@/hooks/useUpdateProduct';
import { useToast } from '@/hooks/useToast';
import { i18n } from '@/lib/utils';
import { fetchFormAttributes } from '@/services/attributes';

import BrandSelect from './BrandSelect';
import ProductPreviewCard from './ProductPreviewCard';
import SupplierSection from './SupplierSection';
import DynamicAttributes from './DynamicAttributes';
import ImagesSection from './ImagesSection';
import SizeTableSection from './SizeTableSection';
import ToggleSwitch from './ToggleSwitch';
import VariantSelect from './VariantSelect';
import VariantTabs from './VariantTabs';
import { LockIcon } from './icons';
import styles from './page.module.css';

/**
 * Validate a single variant. Returns issues array (empty = OK).
 */
function getVariantIssues(variant) {
  const issues = [];
  if (!Object.values(variant.variantAttrs).some((ids) => ids.length > 0))
    issues.push({ key: 'variants', message: 'Выберите размеры' });
  if (variant.images.length === 0)
    issues.push({ key: 'images', message: 'Добавьте хотя бы одно фото' });
  if (variant.variablePricing) {
    const allPriced = Object.values(variant.variantAttrs)
      .flat()
      .every((vid) => {
        const p = variant.perSkuPrices[vid];
        return p?.price && parseInt(p.price, 10) > 0;
      });
    if (!allPriced)
      issues.push({ key: 'price', message: 'Укажите цены для всех размеров' });
    // Validate compareAt > price for each SKU in variable pricing
    const badCompare = Object.values(variant.variantAttrs)
      .flat()
      .some((vid) => {
        const p = variant.perSkuPrices[vid];
        if (!p?.compareAt || !p?.price) return false;
        const price = parseInt(p.price, 10) || 0;
        const compareAt = parseInt(p.compareAt, 10) || 0;
        return compareAt > 0 && price > 0 && compareAt <= price;
      });
    if (badCompare)
      issues.push({
        key: 'comparePrice',
        message: 'Цена до скидки должна быть выше цены продажи',
      });
  } else {
    if (!variant.priceAmount || parseInt(variant.priceAmount, 10) <= 0)
      issues.push({ key: 'price', message: 'Укажите цену' });
    // compareAtPrice must be > price (backend enforces this)
    const price = parseInt(variant.priceAmount, 10) || 0;
    const compareAt = parseInt(variant.compareAtPrice, 10) || 0;
    if (compareAt > 0 && price > 0 && compareAt <= price)
      issues.push({
        key: 'comparePrice',
        message: 'Цена до скидки должна быть выше цены продажи',
      });
  }
  return issues;
}

/**
 * Check if a variant is completely empty (user added but never filled).
 */
function isVariantEmpty(variant) {
  const noAttrs = !Object.values(variant.variantAttrs).some(
    (ids) => ids.length > 0,
  );
  const noImages = variant.images.length === 0;
  const noPrice = !variant.priceAmount;
  const noSkuPrices = Object.keys(variant.perSkuPrices).length === 0;
  return noAttrs && noImages && noPrice && noSkuPrices;
}

/**
 * Full validation: product-level + ALL variants.
 * Returns { productIssues, variantIssues: Map<index, issues[]>, firstBadVariant }
 */
function getFullValidation(form, requiredAttrsMissing) {
  const productIssues = [];
  if (!form.state.brandId)
    productIssues.push({ key: 'brand', message: 'Выберите бренд' });
  if (!form.state.titleRu.trim())
    productIssues.push({ key: 'title', message: 'Введите название товара' });
  if (requiredAttrsMissing)
    productIssues.push({
      key: 'attrs',
      message: 'Заполните обязательные атрибуты',
    });

  const variantIssuesMap = {};
  let firstBadVariant = -1;

  form.state.variants.forEach((v, idx) => {
    const issues = getVariantIssues(v);
    if (issues.length > 0) {
      variantIssuesMap[idx] = issues;
      if (firstBadVariant === -1) firstBadVariant = idx;
    }
  });

  return { productIssues, variantIssuesMap, firstBadVariant };
}

/**
 * Get active variant's inline issues (for showing field-level errors).
 * Product-level fields (brand, title, product attrs) are only editable on the
 * first variant — on subsequent variants those inputs are locked/disabled, so
 * showing inline errors there is a UX dead-end. Restrict product-level issues
 * to the first variant; variant-specific issues always apply.
 */
function getActiveVariantIssues(form, requiredAttrsMissing) {
  const issues = [];
  if (form.state.activeVariantIndex === 0) {
    if (!form.state.brandId)
      issues.push({ key: 'brand', message: 'Выберите бренд' });
    if (!form.state.titleRu.trim())
      issues.push({ key: 'title', message: 'Введите название товара' });
    if (requiredAttrsMissing)
      issues.push({ key: 'attrs', message: 'Заполните обязательные атрибуты' });
  }
  return [...issues, ...getVariantIssues(form.activeVariant)];
}

export default function ProductDetailsForm({
  leafLabel,
  categoryId,
  breadcrumbs,
  mode = 'create',
  initialProduct = null,
  initialMedia = null,
  productId: editProductId = null,
}) {
  const isEditMode = mode === 'edit';
  const router = useRouter();
  const toast = useToast();
  const form = useProductForm({ categoryId, defaultTitle: isEditMode ? '' : leafLabel });
  const imageUpload = useImageUpload();
  const createSubmit = useSubmitProduct();
  const editSubmit = useUpdateProduct();
  const submit = isEditMode ? editSubmit : createSubmit;

  // Hydrate form with server data in edit mode
  const hydratedProductIdRef = useRef(null);
  useEffect(() => {
    if (isEditMode && initialProduct) {
      const pid = initialProduct.id;
      if (hydratedProductIdRef.current !== pid) {
        hydratedProductIdRef.current = pid;
        form.hydrateFromProduct(initialProduct, initialMedia ?? []);
      }
    }
  }, [isEditMode, initialProduct, initialMedia, form.hydrateFromProduct]);

  // Track whether user attempted to submit (show inline errors after first attempt)
  const [attempted, setAttempted] = useState(false);
  // Slug edit mode
  const [slugEditing, setSlugEditing] = useState(false);

  // Shortcut to active variant state
  const av = form.activeVariant;
  const isNotFirstVariant = form.state.activeVariantIndex > 0;

  // Uploads in progress — block submit while images are being processed (any variant)
  const uploadsInProgress = form.state.variants.some((v) =>
    v.images.some((img) => {
      const s = imageUpload.uploads[img.localId]?.status;
      return s === 'uploading' || s === 'processing';
    }),
  );

  const hasFailedUploads = form.state.variants.some((v) =>
    v.images.some(
      (img) => imageUpload.uploads[img.localId]?.status === 'failed',
    ),
  );

  const errorRef = useRef(null);

  useEffect(() => {
    if (!submit.error) return;
    errorRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });

    // useUpdateProduct stores error as string; useSubmitProduct as { code, message }
    const err = submit.error;
    const msg = typeof err === 'string'
      ? err
      : err.code === 'MEDIA_PARTIAL_FAILURE'
        ? 'Некоторые изображения не загрузились. Вы можете отредактировать продукт позже.'
        : err.code === 'ZERO_SKUS'
          ? 'Ошибка: не удалось сгенерировать SKU. Проверьте размеры.'
          : err.code === 'TIMEOUT'
            ? 'Превышено время ожидания. Попробуйте снова.'
            : err.code === 'RATE_LIMITED'
              ? 'Слишком много запросов. Подождите и попробуйте снова.'
              : `Ошибка: ${err.message}`;
    toast.error(msg);
  }, [submit.error, toast]);

  // #10 — Unsaved changes protection
  const formHasChanges = useMemo(() => {
    if (isEditMode) {
      // In edit mode, compare against hydrated snapshot
      const snap = form.state._serverSnapshot;
      if (!snap) return false;
      const sp = snap.product;

      // Product-level fields
      if (
        form.state.titleRu !== (sp.titleI18N?.ru ?? '') ||
        form.state.titleEn !== (sp.titleI18N?.en ?? '') ||
        form.state.brandId !== sp.brandId ||
        form.state.slug !== (sp.slug ?? '') ||
        form.state.descriptionRu !== (sp.descriptionI18N?.ru ?? '') ||
        form.state.countryOfOrigin !== (sp.countryOfOrigin ?? '') ||
        JSON.stringify(form.state.tags) !== JSON.stringify(sp.tags ?? [])
      )
        return true;

      // Variant-level: prices, images, attributes
      for (const v of form.state.variants) {
        const sv = (sp.variants ?? []).find((sv) => sv.id === v.serverId);
        if (!sv) continue;
        const skus = sv.skus ?? [];
        const serverPrice =
          sv.defaultPrice?.amount ??
          (skus[0]?.resolvedPrice ?? skus[0]?.price)?.amount ??
          null;
        const serverPriceStr =
          serverPrice != null && serverPrice !== 0
            ? String(Math.round(serverPrice / 100))
            : '';
        if (v.priceAmount !== serverPriceStr) return true;

        const serverCompare = skus[0]?.compareAtPrice?.amount ?? null;
        const serverCompareStr =
          serverCompare != null && serverCompare !== 0
            ? String(Math.round(serverCompare / 100))
            : '';
        if (v.compareAtPrice !== serverCompareStr) return true;

        // Image count change
        const serverImageCount = (snap.mediaAssets ?? []).filter(
          (m) => m.mediaType === 'image' && m.variantId === v.serverId,
        ).length;
        if (v.images.length !== serverImageCount) return true;
      }

      return false;
    }
    return (
      form.state.brandId ||
      form.state.titleRu !== leafLabel ||
      form.state.descriptionRu ||
      form.state.countryOfOrigin ||
      Object.keys(form.state.productAttrs).length > 0 ||
      form.state.variants.some(
        (v) =>
          v.images.length > 0 ||
          v.sizeGuide !== null ||
          v.priceAmount ||
          v.supplierId ||
          v.sourceUrl ||
          Object.values(v.variantAttrs).some((ids) => ids.length > 0),
      )
    );
  }, [
    isEditMode,
    form.state.brandId,
    form.state.titleRu,
    form.state.titleEn,
    form.state.slug,
    form.state.descriptionRu,
    form.state.countryOfOrigin,
    form.state.productAttrs,
    form.state.variants,
    form.state.tags,
    form.state._serverSnapshot,
    leafLabel,
  ]);

  useEffect(() => {
    if (!formHasChanges || submit.submitting) return;
    function handleBeforeUnload(e) {
      e.preventDefault();
      e.returnValue = '';
    }
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [formHasChanges, submit.submitting]);

  async function handleSubmit(submitMode) {
    setAttempted(true);

    if (isEditMode) {
      // Edit mode — save changes
      if (!form.isValid) return;
      try {
        const result = await editSubmit.execute(form, imageUpload.uploads);
        if (result) {
          toast.success('Изменения сохранены');
          router.push('/admin/products');
        }
      } catch {
        // error is set inside the hook
      }
      return;
    }

    if (submitMode === 'publish') {
      if (hasAnyIssues) {
        toast.warning('Заполните все обязательные поля перед публикацией');
        // Product-level issues are only editable on variant 0 — jump there first.
        if (
          fullValidation.productIssues.length > 0 &&
          form.state.activeVariantIndex !== 0
        ) {
          form.switchVariant(0);
        } else if (
          fullValidation.firstBadVariant >= 0 &&
          fullValidation.firstBadVariant !== form.state.activeVariantIndex
        ) {
          form.switchVariant(fullValidation.firstBadVariant);
        }
        return;
      }
    }

    if (submitMode === 'draft') {
      if (!form.isValid) return;
    }

    const cleanVariants = submitMode === 'draft'
      ? form.state.variants.filter((v, i) => i === 0 || !isVariantEmpty(v))
      : form.state.variants;

    const formSnapshot = {
      ...form,
      state: { ...form.state, variants: cleanVariants },
      variantPayloads: form.variantPayloads.filter((_, i) =>
        submitMode === 'draft' ? (i === 0 || !isVariantEmpty(form.state.variants[i])) : true,
      ),
    };

    const result = await createSubmit.execute(formSnapshot, submitMode, imageUpload.uploads);
    if (result?.productId && !result.error) {
      toast.success(
        submitMode === 'publish'
          ? 'Продукт успешно создан и отправлен на модерацию'
          : 'Черновик продукта сохранён',
      );
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
      .catch(() => {
        setAttrsError(true);
        toast.error('Не удалось загрузить атрибуты. Попробуйте обновить страницу.');
      })
      .finally(() => setAttrsLoading(false));
  }, [categoryId, toast]);

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
    const selectedIds = av.variantAttrs[attr.attributeId] ?? [];
    return (attr.values ?? [])
      .filter((v) => selectedIds.includes(v.id))
      .map((v) => ({ ...v, attrName: i18n(attr.nameI18N, attr.code) }));
  });

  // Full cross-variant validation (for publish blocking and tab error indicators)
  const fullValidation = useMemo(
    () => getFullValidation(form, requiredAttrsMissing),
    [form, requiredAttrsMissing],
  );

  // Active variant issues (for inline field-level error indicators)
  const validationIssues = useMemo(
    () => getActiveVariantIssues(form, requiredAttrsMissing),
    [form, requiredAttrsMissing],
  );

  // Set of variant indices that have validation errors (for tab error dots)
  const variantErrorIndices = useMemo(
    () => new Set(Object.keys(fullValidation.variantIssuesMap).map(Number)),
    [fullValidation.variantIssuesMap],
  );

  // Are there ANY issues across all variants? (blocks publish)
  const hasAnyIssues =
    fullValidation.productIssues.length > 0 ||
    Object.keys(fullValidation.variantIssuesMap).length > 0;

  // #19 — Price comparison warning (compareAtPrice = "was" price, must be > selling price)
  const priceWarning = useMemo(() => {
    if (av.variablePricing) return null;
    const price = parseInt(av.priceAmount, 10) || 0;
    const compareAt = parseInt(av.compareAtPrice, 10) || 0;
    if (compareAt > 0 && price > 0 && compareAt <= price) {
      return 'Цена до скидки должна быть выше цены продажи';
    }
    return null;
  }, [av.priceAmount, av.compareAtPrice, av.variablePricing]);

  // Derive button labels cleanly (#2)
  function getDraftButtonLabel() {
    if (submit.submitting) return submit.progress;
    if (uploadsInProgress) return 'Загрузка фото...';
    if (hasFailedUploads) return 'Есть ошибки загрузки';
    return isEditMode ? 'Сохранить изменения' : 'Сохранить черновик';
  }

  function getPublishButtonLabel() {
    if (submit.submitting) return submit.progress;
    if (uploadsInProgress) return 'Загрузка фото...';
    if (hasFailedUploads) return 'Есть ошибки загрузки';
    if (hasAnyIssues) {
      // Show which variant has a problem, or a product-level issue
      if (fullValidation.productIssues.length > 0)
        return fullValidation.productIssues[0].message;
      const badIdx = fullValidation.firstBadVariant;
      if (badIdx >= 0) {
        const firstIssue = fullValidation.variantIssuesMap[badIdx][0];
        return `Вариант ${badIdx + 1}: ${firstIssue.message.toLowerCase()}`;
      }
    }
    return 'На модерацию';
  }

  // Show inline field errors only after first submission attempt
  const showErrors = attempted && !submit.submitting;
  const hasIssue = (key) => showErrors && validationIssues.some((i) => i.key === key);

  return (
    <div className={styles.layout}>
      <div className={styles.mainColumn}>
        {/* Variant tabs */}
        <VariantTabs
          variants={form.state.variants}
          activeIndex={form.state.activeVariantIndex}
          onSwitch={form.switchVariant}
          onAdd={form.addVariant}
          onRemove={form.removeVariant}
          uploads={imageUpload.uploads}
          errorIndices={attempted ? variantErrorIndices : null}
        />

        {breadcrumbs}

        {/* #4 — Submit overlay */}
        {submit.submitting && (
          <div className={styles.submitOverlay}>
            <div className={styles.submitOverlaySpinner} />
            <p className={styles.submitOverlayText}>{submit.progress}</p>
          </div>
        )}

        <div aria-busy={submit.submitting}>
          <section className={styles.card}>
            <h2 className={styles.cardTitle}>Основные данные</h2>
            <div className={styles.fieldGroup}>
              {/* #1 — error border on brand */}
              <div style={isNotFirstVariant ? { pointerEvents: 'none', opacity: 0.6 } : undefined}>
                <BrandSelect
                  value={form.state.brandId}
                  onChange={(brand) => form.setBrandId(brand.id, brand.name)}
                  hasError={hasIssue('brand')}
                />
                {isNotFirstVariant && (
                  <span className={styles.lockIcon}><LockIcon /> Наследуется</span>
                )}
                {hasIssue('brand') && (
                  <p className={styles.fieldErrorText}>Выберите бренд</p>
                )}
              </div>

              {/* #1 — error border on title */}
              <div
                className={`${styles.floatingField} ${hasIssue('title') ? styles.fieldError : ''}`}
              >
                <label className={styles.floatingLabel} htmlFor="product-title">
                  Название
                </label>
                <input
                  id="product-title"
                  className={styles.floatingInput}
                  value={form.state.titleRu}
                  onChange={(e) => form.setTitleRu(e.target.value)}
                  disabled={isNotFirstVariant}
                  style={isNotFirstVariant ? { opacity: 0.6 } : undefined}
                />
              </div>
              {hasIssue('title') && (
                <p className={styles.fieldErrorText}>Введите название товара</p>
              )}

              {/* #9 — Slug field */}
              <div className={styles.slugRow}>
                <div className={styles.floatingField}>
                  <span className={styles.slugPrefix}>URL-адрес (slug)</span>
                  <input
                    className={styles.floatingInput}
                    value={form.state.slug}
                    onChange={(e) => form.setField('slug', e.target.value)}
                    disabled={!slugEditing}
                    style={!slugEditing ? { opacity: 0.6 } : undefined}
                  />
                </div>
                <button
                  type="button"
                  className={styles.slugEditButton}
                  onClick={() => setSlugEditing((v) => !v)}
                  aria-label={slugEditing ? 'Зафиксировать slug' : 'Редактировать slug'}
                >
                  {slugEditing ? '✓' : '✎'}
                </button>
              </div>

              <VariantSelect
                attributes={variantAttrs}
                values={av.variantAttrs}
                onChange={(attrId, valueIds) =>
                  form.setVariantAttr(attrId, valueIds)
                }
                loading={attrsLoading}
              />
              {hasIssue('variants') && (
                <p className={styles.fieldErrorText}>Выберите хотя бы один размер</p>
              )}
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
            value={av.sizeGuide}
            onChange={(val) => form.setVariantField('sizeGuide', val)}
          />

          <ImagesSection
            images={av.images}
            onAdd={handleImageAdd}
            onRemove={handleImageRemove}
            onSet={form.setImages}
            uploads={imageUpload.uploads}
            onRetry={handleImageRetry}
            onImageCropped={handleImageCropped}
          />
          {hasIssue('images') && (
            <p className={styles.fieldErrorText} style={{ marginTop: -8 }}>
              Добавьте хотя бы одно изображение
            </p>
          )}

          {/* #17 — Original toggle with context */}
          <section className={styles.card}>
            <div className={styles.cardTitleRow}>
              <div>
                <h2 className={styles.cardTitle}>
                  Оригинал
                  {isNotFirstVariant && (
                    <span className={styles.lockIcon}><LockIcon /></span>
                  )}
                </h2>
                <p className={styles.cardHint}>
                  Товар является оригинальным (не копия и не реплика)
                </p>
              </div>
              <ToggleSwitch
                ariaLabel="Переключить оригинал"
                checked={form.state.isOriginal}
                onChange={(val) => form.setField('isOriginal', val)}
                disabled={isNotFirstVariant}
              />
            </div>
          </section>

          <SupplierSection
            deliveryMode={av.deliveryMode}
            onDeliveryModeChange={(val) => form.setVariantField('deliveryMode', val)}
            sourceUrl={av.sourceUrl}
            onSourceUrlChange={(val) => form.setVariantField('sourceUrl', val)}
            supplierId={av.supplierId}
            onSupplierChange={(val) => form.setVariantField('supplierId', val)}
          />

          {/* #6, #11, #19 — Price section with currency + validation */}
          <section className={styles.card}>
            <div className={styles.cardTitleRow}>
              <h2 className={styles.cardTitle}>Цена</h2>
              <div className={styles.toggleRow}>
                <span className={styles.toggleLabel}>Вариативная</span>
                <ToggleSwitch
                  ariaLabel="Переключить вариативную цену"
                  checked={av.variablePricing}
                  onChange={(val) => form.setVariantField('variablePricing', val)}
                />
              </div>
            </div>

            {av.variablePricing ? (
              <div className={styles.priceVariableList}>
                {selectedVariantValues.length > 0 ? (
                  selectedVariantValues.map((val) => (
                    <div key={val.id} className={styles.priceVariableRow}>
                      <div className={styles.priceSizeBadge}>
                        {i18n(val.valueI18N, val.code)}
                      </div>
                      <div className={styles.priceWrapper}>
                        <input
                          className={styles.priceVariableInput}
                          placeholder="Цена"
                          aria-label={`Цена ${i18n(val.valueI18N, val.code)}`}
                          inputMode="numeric"
                          value={av.perSkuPrices[val.id]?.price ?? ''}
                          onChange={(e) =>
                            form.setSkuPrice(val.id, {
                              price: e.target.value.replace(/[^0-9]/g, ''),
                            })
                          }
                          style={{ paddingRight: 36 }}
                        />
                        <span className={styles.currencySuffix}>₽</span>
                      </div>
                      <div className={styles.priceWrapper}>
                        <input
                          className={styles.priceVariableInput}
                          placeholder="До скидки"
                          aria-label={`Цена до скидки ${i18n(val.valueI18N, val.code)}`}
                          inputMode="numeric"
                          value={av.perSkuPrices[val.id]?.compareAt ?? ''}
                          onChange={(e) =>
                            form.setSkuPrice(val.id, {
                              compareAt: e.target.value.replace(/[^0-9]/g, ''),
                            })
                          }
                          style={{ paddingRight: 36 }}
                        />
                        <span className={styles.currencySuffix}>₽</span>
                      </div>
                    </div>
                  ))
                ) : (
                  /* #11 — Better guidance when no variants selected */
                  <p className={styles.cardSubtitle}>
                    ⚠ Сначала выберите размеры в разделе «Основные данные», чтобы задать цену для каждого варианта
                  </p>
                )}
              </div>
            ) : (
              <>
                <div className={styles.fieldRow}>
                  <div className={styles.priceWrapper}>
                    <div
                      className={`${styles.floatingField} ${hasIssue('price') ? styles.fieldError : ''}`}
                    >
                      <label className={styles.floatingLabel} htmlFor="product-price">
                        Цена
                      </label>
                      <input
                        id="product-price"
                        className={styles.floatingInput}
                        aria-label="Цена"
                        inputMode="numeric"
                        value={av.priceAmount}
                        onChange={(e) => {
                          const v = e.target.value.replace(/[^0-9]/g, '');
                          form.setVariantField('priceAmount', v);
                        }}
                        style={{ paddingRight: 36 }}
                      />
                    </div>
                    <span className={styles.currencySuffix}>₽</span>
                  </div>
                  <div className={styles.priceWrapper}>
                    <input
                      className={styles.input}
                      placeholder="Цена до скидки"
                      aria-label="Цена до скидки"
                      inputMode="numeric"
                      value={av.compareAtPrice}
                      onChange={(e) => {
                        const v = e.target.value.replace(/[^0-9]/g, '');
                        form.setVariantField('compareAtPrice', v);
                      }}
                      style={{ paddingRight: 36 }}
                    />
                    <span className={styles.currencySuffix}>₽</span>
                  </div>
                </div>
                {/* #19 — Price comparison warning */}
                {priceWarning && (
                  <p className={styles.warningText}>{priceWarning}</p>
                )}
              </>
            )}
            {hasIssue('price') && (
              <p className={styles.fieldErrorText}>Укажите цену товара</p>
            )}
          </section>

          {/* Submit section */}
          {submit.error && (
            <div className={styles.card} ref={errorRef}>
              <p className={styles.errorText}>
                {typeof submit.error === 'string'
                  ? submit.error
                  : submit.error.code === 'MEDIA_PARTIAL_FAILURE'
                    ? `${submit.error.message} Вы можете отредактировать продукт позже.`
                    : submit.error.code === 'ZERO_SKUS'
                      ? 'Не удалось сгенерировать варианты (SKU). Проверьте выбранные атрибуты.'
                      : submit.error.code === 'TIMEOUT'
                        ? 'Сервер не отвечает. Проверьте соединение и попробуйте позже.'
                        : submit.error.code === 'RATE_LIMITED'
                          ? 'Слишком много запросов. Подождите и попробуйте снова.'
                          : `Ошибка: ${submit.error.message}`}
              </p>
              {!isEditMode && submit.createdProductId && (
                <p className={styles.cardSubtitle}>
                  Продукт был создан. Вы можете отредактировать его позже.
                </p>
              )}
              <button
                type="button"
                className={styles.secondaryButton}
                onClick={() => isEditMode ? editSubmit.setError(null) : submit.clearError()}
                style={{ marginTop: 8 }}
              >
                Закрыть
              </button>
            </div>
          )}

          {/* #1 — Validation summary before buttons */}
          {attempted && hasAnyIssues && !submit.submitting && (
            <div className={styles.validationSummary}>
              {fullValidation.productIssues.map((issue) => (
                <div key={issue.key} className={styles.validationItem}>
                  <span className={styles.validationDot} />
                  <span>{issue.message}</span>
                </div>
              ))}
              {Object.entries(fullValidation.variantIssuesMap).map(
                ([idx, issues]) => (
                  <div key={`v${idx}`}>
                    {form.state.variants.length > 1 && (
                      <p
                        className={styles.validationVariantLabel}
                        role="button"
                        tabIndex={0}
                        onClick={() => form.switchVariant(Number(idx))}
                        onKeyDown={(e) =>
                          e.key === 'Enter' && form.switchVariant(Number(idx))
                        }
                      >
                        Вариант {Number(idx) + 1}:
                      </p>
                    )}
                    {issues.map((issue) => (
                      <div
                        key={`v${idx}-${issue.key}`}
                        className={styles.validationItem}
                      >
                        <span className={styles.validationDot} />
                        <span>{issue.message}</span>
                      </div>
                    ))}
                  </div>
                ),
              )}
            </div>
          )}

          <div className={styles.actions}>
            {isEditMode ? (
              <>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  disabled={submit.submitting}
                  onClick={() => router.push('/admin/products')}
                >
                  Отмена
                </button>
                <button
                  type="button"
                  className={styles.primaryButton}
                  disabled={
                    !form.isValid ||
                    submit.submitting ||
                    uploadsInProgress ||
                    hasFailedUploads
                  }
                  onClick={() => handleSubmit('edit')}
                >
                  {getDraftButtonLabel()}
                </button>
              </>
            ) : (
              <>
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
                  {getDraftButtonLabel()}
                </button>
                <button
                  type="button"
                  className={styles.primaryButton}
                  disabled={
                    submit.submitting ||
                    uploadsInProgress ||
                    hasFailedUploads
                  }
                  onClick={() => handleSubmit('publish')}
                >
                  {getPublishButtonLabel()}
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Sidebar */}
      <aside className={styles.sidebar}>
        <ProductPreviewCard
          title={form.state.titleRu || (isEditMode ? '' : leafLabel)}
          brandName={form.state.brandName}
          price={av.priceAmount}
          images={av.images}
          uploads={imageUpload.uploads}
          isOriginal={form.state.isOriginal}
        />
      </aside>
    </div>
  );
}
