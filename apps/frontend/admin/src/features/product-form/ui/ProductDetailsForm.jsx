'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import useProductForm, {
  purchaseCurrencyFromSupplierType,
  SLUG_RE,
} from '../model/useProductForm';
import useImageUpload from '../model/useImageUpload';
import useSubmitProduct from '../model/useSubmitProduct';
import useUpdateProduct from '../model/useUpdateProduct';
import { formatSubmitError } from '../model/formatSubmitError';
import { useToast } from '@/shared/hooks/useToast';
import { cn, i18n } from '@/shared/lib/utils';
import { useCategoryFormAttributes } from '@/entities/category';
import { useSuppliers } from '@/entities/supplier';

import { MoneyInput } from '@/shared/ui/MoneyInput/MoneyInput';

import BrandSelect from './BrandSelect';
import ProductPreviewCard from './ProductPreviewCard';
import SupplierSection from './SupplierSection';
import DynamicAttributes from './DynamicAttributes';
import ImagesSection from './ImagesSection';
import { useSellingPricePreview } from '../model/useSellingPricePreview';
import { useBgRemoval } from '../model/useBgRemoval';
import SizeTableSection from './SizeTableSection';
import ToggleSwitch from './ToggleSwitch';
import VariantSelect from './VariantSelect';
import VariantTabs from './VariantTabs';
import { LockIcon } from './icons';
import styles from './styles/productForm.module.css';

const SELLING_CURRENCIES = ['RUB'];
// Note: the purchasePrice currency is derived from the active variant's
// supplier — cross_border → CNY, local → RUB. MoneyInput renders a
// locked `<span>` (not a `<select>`) when the `currencies` prop has
// exactly one entry, which is what we want here.

/**
 * Read the integer amount from a form-state money object — returns 0 when the
 * field is empty so the validators below can keep using simple comparisons.
 */
function moneyAmount(money) {
  if (!money || money.amount == null || money.amount === '') return 0;
  const n = Number(money.amount);
  return Number.isFinite(n) ? n : 0;
}

/**
 * Compare a form-state money object (user-facing units) to a backend money
 * snapshot (smallest units). Returns true when the dirty-tracking diff should
 * mark the form as changed.
 */
function moneyChanged(formMoney, serverMoney) {
  const formAmount = moneyAmount(formMoney);
  const serverAmount =
    serverMoney?.amount != null ? Math.round(serverMoney.amount / 100) : 0;
  if (formAmount !== serverAmount) return true;
  if (formAmount === 0) return false;
  return (formMoney?.currency ?? 'RUB') !== (serverMoney?.currency ?? 'RUB');
}

/**
 * Validate a single variant. Returns issues array (empty = OK).
 *
 * CAT-008: manual `price` is no longer required — backend (CAT-009) accepts
 * publish when either a manual price or an autonomous `sellingPrice` is set,
 * and a positive variant-level `purchasePrice` will trigger that recompute.
 * The validators below keep mirroring backend rules but flip "missing price"
 * from a hard error to a guarded one ("missing price AND missing purchase
 * price").
 */
function getVariantIssues(variant) {
  const issues = [];
  if (!Object.values(variant.variantAttrs).some((ids) => ids.length > 0))
    issues.push({ key: 'variants', message: 'Выберите размеры' });
  if (variant.images.length === 0)
    issues.push({ key: 'images', message: 'Добавьте хотя бы одно фото' });

  const variantPurchase = moneyAmount(variant.purchasePrice);
  const hasPurchaseFallback = variantPurchase > 0;

  if (variant.variablePricing) {
    const allPriced = Object.values(variant.variantAttrs)
      .flat()
      .every((vid) => {
        const p = variant.perSkuPrices[vid];
        return moneyAmount(p?.price) > 0;
      });
    if (!allPriced && !hasPurchaseFallback)
      issues.push({
        key: 'price',
        message:
          'Укажите цены для всех размеров или общую закупочную цену для автоматического расчёта',
      });
    // Validate compareAt > price for each SKU in variable pricing
    const badCompare = Object.values(variant.variantAttrs)
      .flat()
      .some((vid) => {
        const p = variant.perSkuPrices[vid];
        const price = moneyAmount(p?.price);
        const compareAt = moneyAmount(p?.compareAt);
        if (price === 0 || compareAt === 0) return false;
        return compareAt <= price;
      });
    if (badCompare)
      issues.push({
        key: 'comparePrice',
        message: 'Цена до скидки должна быть выше цены продажи',
      });
    // Currency match across price ↔ compareAtPrice (backend rejects mixed)
    const badCurrency = Object.values(variant.variantAttrs)
      .flat()
      .some((vid) => {
        const p = variant.perSkuPrices[vid];
        if (!p?.price || !p?.compareAt) return false;
        return p.price.currency !== p.compareAt.currency;
      });
    if (badCurrency)
      issues.push({
        key: 'comparePrice',
        message: 'Валюта цены до скидки должна совпадать с валютой продажи',
      });
    // compareAtPrice без price → backend 422
    const orphanCompare = Object.values(variant.variantAttrs)
      .flat()
      .some((vid) => {
        const p = variant.perSkuPrices[vid];
        return moneyAmount(p?.compareAt) > 0 && moneyAmount(p?.price) <= 0;
      });
    if (orphanCompare)
      issues.push({
        key: 'comparePrice',
        message: 'Цена до скидки требует указания цены продажи',
      });
  } else {
    const price = moneyAmount(variant.price);
    if (price <= 0 && !hasPurchaseFallback) {
      issues.push({
        key: 'price',
        message:
          'Укажите цену продажи или закупочную цену для автоматического расчёта',
      });
    }
    const compareAt = moneyAmount(variant.compareAtPrice);
    if (compareAt > 0 && price <= 0)
      issues.push({
        key: 'comparePrice',
        message: 'Цена до скидки требует указания цены продажи',
      });
    if (compareAt > 0 && price > 0 && compareAt <= price)
      issues.push({
        key: 'comparePrice',
        message: 'Цена до скидки должна быть выше цены продажи',
      });
    if (
      variant.price &&
      variant.compareAtPrice &&
      variant.price.currency !== variant.compareAtPrice.currency
    )
      issues.push({
        key: 'comparePrice',
        message: 'Валюта цены до скидки должна совпадать с валютой продажи',
      });
  }
  // CAT-002 / ADR-005: purchasePrice — optional, but if set must be positive
  // and use one of the allowed currencies.
  if (variant.purchasePrice) {
    if (moneyAmount(variant.purchasePrice) <= 0) {
      issues.push({
        key: 'purchasePrice',
        message: 'Закупочная цена должна быть положительной',
      });
    }
    if (!['RUB', 'CNY'].includes(variant.purchasePrice.currency)) {
      issues.push({
        key: 'purchasePrice',
        message: 'Закупочная цена принимается только в RUB или CNY',
      });
    }
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
  const noPrice = moneyAmount(variant.price) === 0;
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
  if (form.state.slug && !SLUG_RE.test(form.state.slug))
    productIssues.push({
      key: 'slug',
      message:
        'URL-адрес может содержать только латиницу, цифры и дефисы (без пробелов и спец-символов)',
    });
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
    if (form.state.slug && !SLUG_RE.test(form.state.slug))
      issues.push({
        key: 'slug',
        message: 'Допустимы только латиница, цифры и дефис',
      });
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
}) {
  const isEditMode = mode === 'edit';
  const router = useRouter();
  const toast = useToast();
  const form = useProductForm({
    categoryId,
    defaultTitle: isEditMode ? '' : leafLabel,
  });
  const imageUpload = useImageUpload();
  const createSubmit = useSubmitProduct();
  const editSubmit = useUpdateProduct();
  const submit = isEditMode ? editSubmit : createSubmit;

  // Hydrate form with server data in edit mode.
  // Re-hydrates when product id OR version changes — a background refetch
  // (e.g. after invalidation from another tab) bumps `version`, and we want
  // the form to pick up the fresh snapshot. Without this, an in-flight
  // `useProduct` revalidation would silently give the user a stale
  // optimistic-concurrency token, leading to a 409 on save.
  const hydratedProductIdRef = useRef(null);
  const hydrateFnRef = useRef(form.hydrateFromProduct);
  useEffect(() => {
    hydrateFnRef.current = form.hydrateFromProduct;
  }, [form.hydrateFromProduct]);

  useEffect(() => {
    if (!isEditMode || !initialProduct) return;
    const pid = initialProduct.id;
    const ver = initialProduct.version ?? null;
    const prev = hydratedProductIdRef.current;
    if (prev && prev.id === pid && prev.version === ver) return;
    hydratedProductIdRef.current = { id: pid, version: ver };
    hydrateFnRef.current?.(initialProduct, initialMedia ?? []);
  }, [isEditMode, initialProduct, initialMedia]);

  // Track whether user attempted to submit (show inline errors after first attempt)
  const [attempted, setAttempted] = useState(false);
  // Slug edit mode
  const [slugEditing, setSlugEditing] = useState(false);
  // CAT-021 #5: opt-in to one-shot create + recompute-wait + publish.
  // Only meaningful in create mode — in edit mode publishing flows through
  // the product detail page's publish button.
  const [autoPublish, setAutoPublish] = useState(false);

  // Shortcut to active variant state
  const av = form.activeVariant;
  const isNotFirstVariant = form.state.activeVariantIndex > 0;
  // Resolve the selected supplier so we can derive the purchase-price
  // currency from its type. Suppliers list is cached by useSuppliers so
  // mounting this hook twice (here + inside SupplierSection) costs one
  // network round-trip total.
  const { data: suppliersData } = useSuppliers();
  const suppliers = useMemo(() => suppliersData?.items ?? [], [suppliersData]);
  const selectedSupplier = useMemo(() => {
    if (!av.supplierId) return null;
    return suppliers.find((s) => s.id === av.supplierId) ?? null;
  }, [av.supplierId, suppliers]);
  // `isOriginal` isn't a separate form field — it's just "the selected
  // supplier is Poizon" (the canonical Original marketplace). We derive
  // both the flag and the Poizon supplier id here so the toggle below
  // can flip the supplier choice directly.
  const POIZON_NAME = 'Poizon';
  const poizonSupplier = useMemo(
    () => suppliers.find((s) => s.name === POIZON_NAME) ?? null,
    [suppliers],
  );
  const isOriginal = Boolean(
    poizonSupplier && av.supplierId === poizonSupplier.id,
  );
  const toggleOriginal = useCallback(
    (next) => {
      if (next) {
        if (poizonSupplier) {
          form.setVariantField('supplierId', poizonSupplier.id);
        }
      } else if (isOriginal) {
        // Turning Оригинал off when Poizon was selected: clear the
        // supplier rather than pick an arbitrary other one. The user
        // chooses the next supplier explicitly.
        form.setVariantField('supplierId', null);
      }
    },
    [poizonSupplier, isOriginal, form],
  );
  // Lock the purchase-price currency to the supplier type — cross-border
  // pays in yuan, local pays in rubles. MoneyInput auto-collapses its
  // currency select into a read-only badge when this array has one entry.
  // Until a supplier is picked, default to RUB so the input stays editable.
  const purchaseCurrency = purchaseCurrencyFromSupplierType(
    selectedSupplier?.type,
  );

  // Keep the stored `purchasePrice` currency in lockstep with the
  // supplier-derived currency. Without this, switching the supplier
  // (cross-border → local or vice versa) would leave the cached money
  // object with its old currency until the next keystroke — and the
  // save payload would ship the stale currency.
  useEffect(() => {
    if (!av.purchasePrice) return;
    if (av.purchasePrice.currency === purchaseCurrency) return;
    form.setVariantField('purchasePrice', {
      ...av.purchasePrice,
      currency: purchaseCurrency,
    });
  }, [purchaseCurrency, av.purchasePrice, form]);
  // Surface the formula-derived selling price as the «Цена продажи»
  // placeholder + a small helper line (formula version / loading). Pre-fix
  // this lived in a standalone green card under the price row; the
  // merchandiser's eyes had to jump across the section to connect the
  // calculation to the field they were filling.
  const sellingPreview = useSellingPricePreview({
    productId: form.state._serverSnapshot?.productId ?? null,
    categoryId: form.state.categoryId,
    supplierId: av.supplierId,
    purchasePrice: av.purchasePrice,
  });

  // BG-removal state lifted to the form so both <ImagesSection> (gallery
  // thumbnails) and <ProductPreviewCard> (sidebar mockup) can read from
  // the same source — flipping «Без фона / С фоном» in the editor now
  // updates the right-hand preview as well.
  const bgRemoval = useBgRemoval();

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
    // Audit 2.4 — single source of truth for submit-error copy. Both this
    // toast and the inline error card below pull from formatSubmitError so
    // a wording change can't silently desync.
    const { short, isCancellation } = formatSubmitError(submit.error);
    if (isCancellation) toast.warning(short);
    else toast.error(short);
  }, [submit.error, toast]);

  // #10 — Unsaved changes protection
  const formHasChanges = useMemo(() => {
    if (isEditMode) {
      // In edit mode, compare against hydrated snapshot
      const snap = form.state._serverSnapshot;
      if (!snap) return false;
      const sp = snap.product;

      // Product-level fields. Element-wise tag compare avoids the double
      // JSON.stringify per render — admin typically holds <10 short tags,
      // so length+strict equality is dramatically cheaper than serialising
      // both sides on every keystroke.
      const serverTags = sp.tags ?? [];
      const tagsChanged =
        form.state.tags.length !== serverTags.length ||
        form.state.tags.some((t, i) => t !== serverTags[i]);

      if (
        form.state.titleRu !== (sp.titleI18N?.ru ?? '') ||
        form.state.titleEn !== (sp.titleI18N?.en ?? '') ||
        form.state.brandId !== sp.brandId ||
        form.state.slug !== (sp.slug ?? '') ||
        form.state.descriptionRu !== (sp.descriptionI18N?.ru ?? '') ||
        form.state.countryOfOrigin !== (sp.countryOfOrigin ?? '') ||
        tagsChanged
      )
        return true;

      // Variant-level: prices, images, attributes
      for (const v of form.state.variants) {
        const sv = (sp.variants ?? []).find((sv) => sv.id === v.serverId);
        if (!sv) continue;
        const skus = sv.skus ?? [];
        const serverPriceMoney =
          sv.defaultPrice ?? skus[0]?.resolvedPrice ?? skus[0]?.price ?? null;
        const serverCompareMoney = skus[0]?.compareAtPrice ?? null;
        const serverPurchaseMoney = skus[0]?.purchasePrice ?? null;
        if (moneyChanged(v.price, serverPriceMoney)) return true;
        if (moneyChanged(v.compareAtPrice, serverCompareMoney)) return true;
        if (moneyChanged(v.purchasePrice, serverPurchaseMoney)) return true;

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
          v.price != null ||
          v.purchasePrice != null ||
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
        const result = await editSubmit.execute(
          form,
          imageUpload.uploads,
          bgRemoval,
        );
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

    const cleanVariants =
      submitMode === 'draft'
        ? form.state.variants.filter((v, i) => i === 0 || !isVariantEmpty(v))
        : form.state.variants;

    const formSnapshot = {
      ...form,
      state: { ...form.state, variants: cleanVariants },
      variantPayloads: form.variantPayloads.filter((_, i) =>
        submitMode === 'draft'
          ? i === 0 || !isVariantEmpty(form.state.variants[i])
          : true,
      ),
    };

    const effectiveMode =
      submitMode === 'publish' && autoPublish ? 'auto-publish' : submitMode;
    const result = await createSubmit.execute(
      formSnapshot,
      effectiveMode,
      imageUpload.uploads,
      { bgRemoval },
    );
    if (result?.productId && !result.error) {
      // Auto-publish path can fall back to draft when the recompute SLA
      // expires — surface a different toast and route the user to the
      // detail page so they can finish manually instead of dumping them
      // onto the list with a misleading "published" message.
      if (effectiveMode === 'auto-publish') {
        if (result.autoPublishTimedOut) {
          toast.warning(
            'Цены не успели рассчитаться за 30 секунд. Сохранили как черновик — опубликуйте, когда статус SKU станет «Цена рассчитана».',
          );
          router.push(`/admin/products/${result.productId}`);
        } else {
          toast.success('Товар создан и опубликован');
          router.push(`/admin/products/${result.productId}`);
        }
      } else {
        toast.success(
          submitMode === 'publish'
            ? 'Продукт успешно создан и отправлен на модерацию'
            : 'Черновик продукта сохранён',
        );
        router.push('/admin/products');
      }
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
    [form, imageUpload],
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

  // Load form-attributes once, share between DynamicAttributes and VariantSelect.
  // Cached for REFERENCE_DATA_STALE_TIME_MS by `useCategoryFormAttributes`,
  // so re-mounting the form (e.g. navigating between products in the same
  // category) doesn't refetch.
  const {
    data: formData,
    isPending: attrsPending,
    isError: attrsError,
    refetch: refetchFormAttrs,
  } = useCategoryFormAttributes(categoryId);
  const attrsLoading = attrsPending && Boolean(categoryId);

  useEffect(() => {
    if (attrsError) {
      toast.error(
        'Не удалось загрузить атрибуты. Попробуйте обновить страницу.',
      );
    }
  }, [attrsError, toast]);

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

  // Variable pricing is only valid for single-dimension variants (e.g. only
  // size). With multiple dimensions (color × size) the per-SKU PATCH lookup
  // in useSubmitProduct uses .find() over variantAttributes by a single
  // valueId — it would only land the price on one of the matrix cells.
  // Detect the multi-dim case here so the toggle can be disabled and any
  // already-toggled-on state can be folded back to flat.
  const isMultiDimVariant = useMemo(
    () =>
      Object.keys(av.variantAttrs).filter(
        (attrId) => (av.variantAttrs[attrId] ?? []).length > 0,
      ).length > 1,
    [av.variantAttrs],
  );

  useEffect(() => {
    if (isMultiDimVariant && av.variablePricing) {
      form.setVariantField('variablePricing', false);
    }
  }, [isMultiDimVariant, av.variablePricing, form]);

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
  const hasIssue = (key) =>
    showErrors && validationIssues.some((i) => i.key === key);

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
              {/* Audit 2.2 — `inert` removes the wrapper from the tab order
                  AND blocks click events on every nested control, replacing
                  the brittle `pointer-events:none` + opacity hack that left
                  keyboard focus visiting an "unclickable" button. The
                  surrounding "Наследуется" badge stays outside the inert
                  region so SR users still hear why the field is locked. */}
              <div
                inert={isNotFirstVariant ? '' : undefined}
                aria-disabled={isNotFirstVariant || undefined}
                style={isNotFirstVariant ? { opacity: 0.6 } : undefined}
              >
                <BrandSelect
                  value={form.state.brandId}
                  onChange={(brand) => form.setBrandId(brand.id, brand.name)}
                  hasError={hasIssue('brand')}
                />
                {hasIssue('brand') && (
                  <p className={styles.fieldErrorText}>Выберите бренд</p>
                )}
              </div>
              {isNotFirstVariant && (
                <span className={styles.lockIcon}>
                  <LockIcon /> Наследуется
                </span>
              )}

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
                  <span className={styles.slugPrefix}>URL-адрес</span>
                  <input
                    className={styles.floatingInput}
                    value={form.state.slug}
                    onChange={(e) => form.setField('slug', e.target.value)}
                    disabled={!slugEditing}
                    aria-invalid={hasIssue('slug') || undefined}
                    style={!slugEditing ? { opacity: 0.6 } : undefined}
                  />
                </div>
                <button
                  type="button"
                  className={styles.slugEditButton}
                  onClick={() => setSlugEditing((v) => !v)}
                  aria-label={
                    slugEditing ? 'Зафиксировать slug' : 'Редактировать slug'
                  }
                >
                  {/* Audit 2.1 — glyph wrapped so SR reads the aria-label
                      ("Редактировать slug" / "Зафиксировать slug") instead
                      of announcing «галочка» / «перо». */}
                  <span aria-hidden="true">{slugEditing ? '✓' : '✎'}</span>
                </button>
              </div>
              {hasIssue('slug') && (
                <p className={styles.fieldErrorText}>
                  {validationIssues.find((i) => i.key === 'slug')?.message}
                </p>
              )}

              <VariantSelect
                attributes={variantAttrs}
                values={av.variantAttrs}
                onChange={(attrId, valueIds) =>
                  form.setVariantAttr(attrId, valueIds)
                }
                loading={attrsLoading}
              />
              {hasIssue('variants') && (
                <p className={styles.fieldErrorText}>
                  Выберите хотя бы один размер
                </p>
              )}
            </div>
          </section>

          {attrsError ? (
            <section className={styles.card}>
              <p className={styles.errorText}>Не удалось загрузить атрибуты</p>
              <button
                type="button"
                className={`${styles.secondaryButton} mt-2`}
                onClick={() => refetchFormAttrs()}
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
            // Edit mode → wire reorder mutation to the live product;
            // create mode → keep reorder local until submit.
            productId={
              isEditMode ? form.state._serverSnapshot?.productId : null
            }
            bgRemoval={bgRemoval}
          />
          {hasIssue('images') && (
            <p className={`${styles.fieldErrorText} -mt-2`}>
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
                    <span className={styles.lockIcon}>
                      <LockIcon />
                    </span>
                  )}
                </h2>
              </div>
              <ToggleSwitch
                ariaLabel="Переключить оригинал"
                checked={isOriginal}
                onChange={toggleOriginal}
                disabled={isNotFirstVariant || !poizonSupplier}
              />
            </div>
          </section>

          <SupplierSection
            sourceUrl={av.sourceUrl}
            onSourceUrlChange={(val) => form.setVariantField('sourceUrl', val)}
            supplierId={av.supplierId}
            onSupplierChange={(val) => form.setVariantField('supplierId', val)}
          />

          {/* #6, #11 — Combined price section: purchase price (drives the
              autonomous recompute via ADR-005) + selling price (manual or
              derived). Previously split into two cards «Цена» + «Закупка»;
              the user-facing flow is the same field in both — collapsing
              into one card mirrors how merchandisers actually fill it
              ("сначала закупка, потом цена продажи или оставить пусто"). */}
          <section className={styles.card}>
            <div className={styles.cardTitleRow}>
              <div>
                <h2 className={styles.cardTitle}>Цена</h2>
              </div>
              <div className={styles.toggleRow}>
                <span className={styles.toggleLabel}>Вариативная</span>
                <ToggleSwitch
                  ariaLabel="Переключить вариативную цену"
                  checked={av.variablePricing}
                  disabled={isMultiDimVariant}
                  onChange={(val) =>
                    form.setVariantField('variablePricing', val)
                  }
                />
              </div>
            </div>
            {isMultiDimVariant && (
              <p className={styles.cardSubtitle}>
                ⓘ Вариативная цена доступна только при одной оси (например,
                только размер). При нескольких атрибутах — задайте одну общую
                цену продажи или закупочную цену.
              </p>
            )}

            {av.variablePricing ? (
              <>
                {/* Variant-level purchase price (drives every SKU's recompute);
                    selling price is per-SKU below. */}
                <MoneyInput
                  label="Закупочная цена"
                  placeholder="0"
                  currencies={[purchaseCurrency]}
                  value={av.purchasePrice}
                  onChange={(money) =>
                    form.setVariantField('purchasePrice', money)
                  }
                  hasError={hasIssue('purchasePrice')}
                  errorText={
                    validationIssues.find((i) => i.key === 'purchasePrice')
                      ?.message
                  }
                />
                <div className={styles.priceVariableList}>
                  {selectedVariantValues.length > 0 ? (
                    selectedVariantValues.map((val) => {
                      const formulaSuggestion =
                        sellingPreview.value?.amount != null
                          ? String(sellingPreview.value.amount)
                          : '—';
                      return (
                        <div key={val.id} className={styles.priceVariableRow}>
                          <div className={styles.priceSizeBadge}>
                            {i18n(val.valueI18N, val.code)}
                          </div>
                          <MoneyInput
                            ariaLabel={`Цена продажи ${i18n(val.valueI18N, val.code)}`}
                            placeholder={formulaSuggestion}
                            currencies={SELLING_CURRENCIES}
                            value={av.perSkuPrices[val.id]?.price ?? null}
                            onChange={(money) =>
                              form.setSkuPrice(val.id, { price: money })
                            }
                          />
                        </div>
                      );
                    })
                  ) : (
                    /* #11 — Better guidance when no variants selected */
                    <p className={styles.cardSubtitle}>
                      ⚠ Сначала выберите размеры в разделе «Основные данные»,
                      чтобы задать цену для каждого варианта
                    </p>
                  )}
                </div>
              </>
            ) : (
              <div className={styles.fieldRow}>
                <MoneyInput
                  label="Закупочная цена"
                  placeholder="0"
                  currencies={[purchaseCurrency]}
                  value={av.purchasePrice}
                  onChange={(money) =>
                    form.setVariantField('purchasePrice', money)
                  }
                  hasError={hasIssue('purchasePrice')}
                  errorText={
                    validationIssues.find((i) => i.key === 'purchasePrice')
                      ?.message
                  }
                />
                <MoneyInput
                  label="Цена продажи"
                  placeholder={
                    sellingPreview.value?.amount != null
                      ? String(sellingPreview.value.amount)
                      : '—'
                  }
                  helperText={sellingPreview.helperText ?? undefined}
                  currencies={SELLING_CURRENCIES}
                  value={av.price}
                  onChange={(money) => form.setVariantField('price', money)}
                  hasError={hasIssue('price')}
                />
              </div>
            )}
            {hasIssue('price') && (
              <p className={styles.fieldErrorText}>
                {validationIssues.find((i) => i.key === 'price')?.message ??
                  'Укажите цену товара'}
              </p>
            )}
            {/* Variable mode: surface the formula status (loading /
                «Формула vN») once for the whole list, since every per-SKU
                row uses the same placeholder. Non-variable mode already
                renders this via the «Цена продажи» MoneyInput's
                helperText slot. */}
            {av.variablePricing && sellingPreview.helperText && (
              <p
                className="text-app-muted text-xs"
                role="status"
                aria-live="polite"
              >
                {sellingPreview.helperText}
              </p>
            )}

            {/* Step-by-step formula breakdown (AST v2 `componentsBreakdown`,
                with a derived view of the legacy `components` dict). Rows
                are pre-filtered by `isVisible`; the row marked `isFinal` is
                rendered bold so it reads as the headline. Hidden behind a
                <details> expander to keep the price card compact for the
                common path. */}
            {sellingPreview.breakdown.length > 0 && (
              <details className="text-app-muted text-xs">
                <summary className="hover:text-app-text-dark cursor-pointer font-medium select-none">
                  Показать расчёт по формуле
                </summary>
                <table className="mt-2 w-full border-separate border-spacing-y-0.5">
                  <tbody>
                    {sellingPreview.breakdown.map((row) => (
                      <tr key={row.code}>
                        <td
                          className={cn(
                            'pr-3 align-top',
                            row.isFinal && 'text-app-text-dark font-semibold',
                          )}
                        >
                          {row.name}
                        </td>
                        <td
                          className={cn(
                            'text-app-text-dark text-right font-mono',
                            row.isFinal && 'font-bold',
                          )}
                        >
                          {row.displayValue}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </details>
            )}
          </section>

          {/* Submit section */}
          {submit.error && (
            <div className={styles.card} ref={errorRef}>
              {/* Audit 2.4 — formatSubmitError keeps this card and the toast
                  in sync. `long` is the verbose variant for the inline card. */}
              <p className={styles.errorText}>
                {formatSubmitError(submit.error).long}
              </p>
              {!isEditMode && submit.createdProductId && (
                <p className={styles.cardSubtitle}>
                  Продукт был создан. Вы можете отредактировать его позже.
                </p>
              )}
              <button
                type="button"
                className={`${styles.secondaryButton} mt-2`}
                onClick={() =>
                  isEditMode ? editSubmit.setError(null) : submit.clearError()
                }
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
                      // Audit 2.3 — was <p role="button" tabIndex={0}>; native
                      // <button> activates on both Enter and Space and gets
                      // proper focus-visible rings without re-implementing
                      // them in JS.
                      <button
                        type="button"
                        className={styles.validationVariantLabel}
                        onClick={() => form.switchVariant(Number(idx))}
                      >
                        Вариант {Number(idx) + 1}:
                      </button>
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
                <label className="text-app-muted mr-auto inline-flex items-center gap-2 text-xs">
                  <input
                    type="checkbox"
                    checked={autoPublish}
                    onChange={(e) => setAutoPublish(e.target.checked)}
                    disabled={submit.submitting}
                    className="border-app-border h-3.5 w-3.5 rounded"
                  />
                  <span>
                    Опубликовать сразу{' '}
                    <span className="text-app-muted">
                      (дождёмся расчёта цен и автоматически опубликуем)
                    </span>
                  </span>
                </label>
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
                    submit.submitting || uploadsInProgress || hasFailedUploads
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
          // Mirror the disabled «Цена продажи» fallback: stored manual
          // price (edit-mode legacy) wins; otherwise the formula preview.
          price={av.price?.amount ?? sellingPreview.value?.amount ?? ''}
          images={av.images}
          uploads={imageUpload.uploads}
          isOriginal={isOriginal}
          bgRemovalStateByLocalId={bgRemoval.stateByLocalId}
          bgVariantByLocalId={bgRemoval.variantByLocalId}
        />
      </aside>
    </div>
  );
}
