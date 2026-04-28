'use client';

import { useCallback, useMemo, useReducer } from 'react';
import { buildI18nPayload } from '@/lib/utils';

/**
 * Unified state hook for the product creation and editing form.
 *
 * Supports multiple variants (tabs). Product-level fields are shared,
 * variant-level fields (images, sizes, prices, delivery) are per-variant.
 *
 * Field naming follows openapi.json contracts (camelCase).
 * This hook manages form state only — no API calls.
 *
 * Edit mode: call hydrateFromProduct(product, mediaAssets) to populate
 * form state from a backend ProductResponse + media list.
 */

// ---------------------------------------------------------------------------
// Initial state helpers
// ---------------------------------------------------------------------------

let _nextLocalId = 0;
function genLocalId() {
  return `v-${++_nextLocalId}-${Date.now().toString(36)}`;
}

function buildVariantState() {
  return {
    localId: genLocalId(),
    variantAttrs: {},
    images: [],
    sizeGuide: null,
    deliveryMode: 'china',
    supplierId: null,
    sourceUrl: '',
    priceAmount: '',
    compareAtPrice: '',
    priceCurrency: 'RUB',
    variablePricing: false,
    perSkuPrices: {},
  };
}

function buildInitialState({ categoryId = null, defaultTitle = '' } = {}) {
  return {
    // Product-level (shared across variants)
    categoryId,
    brandId: null,
    brandName: '',
    titleRu: defaultTitle,
    titleEn: '',
    slug: defaultTitle ? transliterate(defaultTitle) : '',
    descriptionRu: '',
    descriptionEn: '',
    productAttrs: {},
    isOriginal: false,
    tags: [],
    countryOfOrigin: '',

    // Variant management
    activeVariantIndex: 0,
    variants: [buildVariantState()],

    // Edit mode metadata (null in create mode)
    _serverSnapshot: null,
  };
}

// ---------------------------------------------------------------------------
// Backend → Form state mapping (edit mode hydration)
// ---------------------------------------------------------------------------

/**
 * Convert kopecks (integer) to rubles (string) for form display.
 * Backend stores amounts in smallest currency unit (kopecks for RUB).
 */
function kopecksToRubles(amount) {
  if (amount == null || amount === 0) return '';
  return String(Math.round(amount / 100));
}

/**
 * Map a backend ProductResponse + media assets to form state.
 *
 * @param {Object} product - Backend ProductResponse
 * @param {Object[]} mediaAssets - Array of MediaAssetResponse with resolved URLs
 * @returns {Object} Form state compatible with useProductForm reducer
 */
function mapProductToFormState(product, mediaAssets = []) {
  // Group media by variantId
  const mediaByVariant = {};
  for (const asset of mediaAssets) {
    const vid = asset.variantId ?? '_product';
    if (!mediaByVariant[vid]) mediaByVariant[vid] = [];
    mediaByVariant[vid].push(asset);
  }
  // Sort each group by sortOrder
  for (const vid of Object.keys(mediaByVariant)) {
    mediaByVariant[vid].sort((a, b) => a.sortOrder - b.sortOrder);
  }

  // Collect ALL product-level attribute assignments (multi-value map)
  // During creation, variant attr values are also bulk-assigned at product level.
  // If some SKUs weren't generated, this map serves as the authoritative source.
  const productAttrMulti = {};
  const productAttrs = {};
  for (const attr of product.attributes ?? []) {
    // Single-value map for product-level attrs (brand, etc.)
    productAttrs[attr.attributeId] = attr.attributeValueId;
    // Multi-value map for supplementing variant attrs
    if (!productAttrMulti[attr.attributeId])
      productAttrMulti[attr.attributeId] = [];
    if (!productAttrMulti[attr.attributeId].includes(attr.attributeValueId)) {
      productAttrMulti[attr.attributeId].push(attr.attributeValueId);
    }
  }

  // Map variants
  const variants = (product.variants ?? []).map((variant) => {
    const skus = variant.skus ?? [];

    // Build variantAttrs: {[attributeId]: [valueId1, valueId2, ...]}
    // Primary source: SKU variantAttributes
    const variantAttrs = {};
    for (const sku of skus) {
      for (const va of sku.variantAttributes ?? []) {
        if (!variantAttrs[va.attributeId]) variantAttrs[va.attributeId] = [];
        if (!variantAttrs[va.attributeId].includes(va.attributeValueId)) {
          variantAttrs[va.attributeId].push(va.attributeValueId);
        }
      }
    }

    // Supplement: merge product-level attribute values that SKUs may be missing
    // (e.g. color assigned at product level but SKU generation was partial)
    // Heuristic: if product-level has multiple values for one attribute, it's
    // variant-level (product-level attrs are single-select)
    for (const [attrId, valueIds] of Object.entries(productAttrMulti)) {
      if (!variantAttrs[attrId] && valueIds.length <= 1) continue;
      if (!variantAttrs[attrId]) variantAttrs[attrId] = [];
      for (const vid of valueIds) {
        if (!variantAttrs[attrId].includes(vid)) {
          variantAttrs[attrId].push(vid);
        }
      }
    }

    // Determine pricing mode — use resolvedPrice (cascade SKU→Variant→Product)
    // with fallback to direct price, matching the BFF enrichment logic
    const activePrices = skus
      .filter(
        (s) => s.isActive && (s.resolvedPrice ?? s.price)?.amount != null,
      )
      .map((s) => (s.resolvedPrice ?? s.price).amount);
    const allSamePrice =
      activePrices.length > 0 &&
      activePrices.every((p) => p === activePrices[0]);
    const variablePricing = activePrices.length > 1 && !allSamePrice;

    // Uniform price (from variant defaultPrice or first SKU's resolved price)
    const firstSkuPrice =
      (skus[0]?.resolvedPrice ?? skus[0]?.price)?.amount ?? null;
    const uniformPrice =
      variant.defaultPrice?.amount ??
      (allSamePrice ? activePrices[0] : null) ??
      firstSkuPrice;
    const uniformCompare =
      skus[0]?.compareAtPrice?.amount ?? null;

    // Per-SKU prices for variable pricing (use resolvedPrice for display)
    const perSkuPrices = {};
    if (variablePricing) {
      for (const sku of skus) {
        // Use first variantAttribute valueId as key (matches creation form convention)
        const valueId = sku.variantAttributes?.[0]?.attributeValueId;
        if (valueId) {
          const effectivePrice = (sku.resolvedPrice ?? sku.price)?.amount;
          perSkuPrices[valueId] = {
            price: kopecksToRubles(effectivePrice),
            compareAt: kopecksToRubles(sku.compareAtPrice?.amount),
            skuId: sku.id,
          };
        }
      }
    }

    // Map media assets for this variant
    const variantMedia = mediaByVariant[variant.id] ?? [];
    const images = variantMedia
      .filter((m) => m.mediaType === 'image')
      .map((m) => ({
        localId: `server-${m.id}`,
        url: m._resolvedUrl ?? m.url ?? null,
        alt: 'Изображение товара',
        mediaId: m.id,
        storageObjectId: m.storageObjectId,
        role: m.role,
        sortOrder: m.sortOrder,
        fromServer: true,
      }));

    return {
      localId: genLocalId(),
      serverId: variant.id,
      variantAttrs,
      images,
      sizeGuide: null,
      deliveryMode: product.supplierId ? 'china' : 'china',
      supplierId: product.supplierId ?? null,
      sourceUrl: product.sourceUrl ?? '',
      priceAmount: kopecksToRubles(uniformPrice),
      compareAtPrice: kopecksToRubles(uniformCompare),
      priceCurrency: variant.defaultPrice?.currency ?? product.priceCurrency ?? 'RUB',
      variablePricing,
      perSkuPrices,
      skus: skus.map((s) => ({ id: s.id, skuCode: s.skuCode, version: s.version })),
    };
  });

  // Fallback: if no variants, create an empty one
  if (variants.length === 0) {
    variants.push(buildVariantState());
  }

  const state = {
    categoryId: product.primaryCategoryId,
    brandId: product.brandId,
    brandName: '',
    titleRu: product.titleI18N?.ru ?? '',
    titleEn: product.titleI18N?.en ?? '',
    slug: product.slug ?? '',
    descriptionRu: product.descriptionI18N?.ru ?? '',
    descriptionEn: product.descriptionI18N?.en ?? '',
    productAttrs,
    isOriginal: false,
    tags: product.tags ?? [],
    countryOfOrigin: product.countryOfOrigin ?? '',
    activeVariantIndex: 0,
    variants,
    // Snapshot of server state for diffing on submit
    _serverSnapshot: {
      productId: product.id,
      version: product.version,
      status: product.status,
      product,
      mediaAssets,
    },
  };

  return state;
}

// ---------------------------------------------------------------------------
// Reducer
// ---------------------------------------------------------------------------

function formReducer(state, action) {
  switch (action.type) {
    // ── Product-level fields ──
    case 'SET_FIELD':
      return { ...state, [action.field]: action.value };

    case 'SET_BRAND':
      return {
        ...state,
        brandId: action.brandId,
        brandName: action.brandName ?? '',
      };

    case 'SET_PRODUCT_ATTR':
      return {
        ...state,
        productAttrs: {
          ...state.productAttrs,
          [action.attributeId]: action.valueId,
        },
      };

    case 'CLEAR_PRODUCT_ATTR': {
      const next = { ...state.productAttrs };
      delete next[action.attributeId];
      return { ...state, productAttrs: next };
    }

    case 'ADD_TAG':
      if (state.tags.includes(action.tag)) return state;
      return { ...state, tags: [...state.tags, action.tag] };

    case 'REMOVE_TAG':
      return { ...state, tags: state.tags.filter((t) => t !== action.tag) };

    // ── Variant management ──
    case 'SWITCH_VARIANT':
      if (action.index < 0 || action.index >= state.variants.length)
        return state;
      return { ...state, activeVariantIndex: action.index };

    case 'ADD_VARIANT': {
      const first = state.variants[0];
      const newVariant = {
        ...buildVariantState(),
        // Inherit sizes from first variant
        variantAttrs: { ...first.variantAttrs },
      };
      return {
        ...state,
        variants: [...state.variants, newVariant],
        activeVariantIndex: state.variants.length,
      };
    }

    case 'REMOVE_VARIANT': {
      if (state.variants.length <= 1) return state;
      const idx = action.index;
      const next = state.variants.filter((_, i) => i !== idx);
      let nextActive = state.activeVariantIndex;
      if (nextActive >= next.length) nextActive = next.length - 1;
      else if (nextActive > idx) nextActive--;
      return {
        ...state,
        variants: next,
        activeVariantIndex: nextActive,
      };
    }

    // ── Per-variant fields (operate on active variant) ──
    case 'SET_VARIANT_FIELD': {
      const vi = state.activeVariantIndex;
      const v = state.variants[vi];
      if (!v) return state;
      return {
        ...state,
        variants: state.variants.map((item, i) =>
          i === vi ? { ...item, [action.field]: action.value } : item,
        ),
      };
    }

    case 'SET_VARIANT_ATTR': {
      const vi = state.activeVariantIndex;
      return {
        ...state,
        variants: state.variants.map((item, i) =>
          i === vi
            ? {
                ...item,
                variantAttrs: {
                  ...item.variantAttrs,
                  [action.attributeId]: action.valueIds,
                },
              }
            : item,
        ),
      };
    }

    case 'TOGGLE_VARIANT_VALUE': {
      const vi = state.activeVariantIndex;
      const v = state.variants[vi];
      if (!v) return state;
      const current = v.variantAttrs[action.attributeId] ?? [];
      const has = current.includes(action.valueId);
      const nextValues = has
        ? current.filter((id) => id !== action.valueId)
        : [...current, action.valueId];
      let nextPrices = v.perSkuPrices;
      if (has && v.perSkuPrices[action.valueId]) {
        nextPrices = { ...v.perSkuPrices };
        delete nextPrices[action.valueId];
      }
      return {
        ...state,
        variants: state.variants.map((item, i) =>
          i === vi
            ? {
                ...item,
                variantAttrs: {
                  ...item.variantAttrs,
                  [action.attributeId]: nextValues,
                },
                perSkuPrices: nextPrices,
              }
            : item,
        ),
      };
    }

    case 'SET_SKU_PRICE': {
      const vi = state.activeVariantIndex;
      const v = state.variants[vi];
      if (!v) return state;
      return {
        ...state,
        variants: state.variants.map((item, i) =>
          i === vi
            ? {
                ...item,
                perSkuPrices: {
                  ...item.perSkuPrices,
                  [action.valueId]: {
                    ...(item.perSkuPrices[action.valueId] ?? {}),
                    ...action.prices,
                  },
                },
              }
            : item,
        ),
      };
    }

    case 'ADD_IMAGE': {
      const vi = state.activeVariantIndex;
      return {
        ...state,
        variants: state.variants.map((item, i) =>
          i === vi ? { ...item, images: [...item.images, action.image] } : item,
        ),
      };
    }

    case 'REMOVE_IMAGE': {
      const vi = state.activeVariantIndex;
      return {
        ...state,
        variants: state.variants.map((item, i) =>
          i === vi
            ? {
                ...item,
                images: item.images.filter(
                  (img) => img.localId !== action.localId,
                ),
              }
            : item,
        ),
      };
    }

    case 'SET_IMAGES': {
      const vi = state.activeVariantIndex;
      return {
        ...state,
        variants: state.variants.map((item, i) =>
          i === vi ? { ...item, images: action.images } : item,
        ),
      };
    }

    case 'RESET':
      return buildInitialState(action.options);

    case 'HYDRATE':
      return mapProductToFormState(action.product, action.mediaAssets);

    default:
      return state;
  }
}

// ---------------------------------------------------------------------------
// Slug generation helper
// ---------------------------------------------------------------------------

function transliterate(text) {
  const map = {
    а: 'a',
    б: 'b',
    в: 'v',
    г: 'g',
    д: 'd',
    е: 'e',
    ё: 'yo',
    ж: 'zh',
    з: 'z',
    и: 'i',
    й: 'y',
    к: 'k',
    л: 'l',
    м: 'm',
    н: 'n',
    о: 'o',
    п: 'p',
    р: 'r',
    с: 's',
    т: 't',
    у: 'u',
    ф: 'f',
    х: 'kh',
    ц: 'ts',
    ч: 'ch',
    ш: 'sh',
    щ: 'shch',
    ъ: '',
    ы: 'y',
    ь: '',
    э: 'e',
    ю: 'yu',
    я: 'ya',
  };
  return text
    .toLowerCase()
    .split('')
    .map((c) => map[c] ?? c)
    .join('')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 255);
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export default function useProductForm({ categoryId, defaultTitle = '' } = {}) {
  const [state, dispatch] = useReducer(
    formReducer,
    { categoryId, defaultTitle },
    buildInitialState,
  );

  // --- Active variant shortcut ---
  const activeVariant = state.variants[state.activeVariantIndex] ?? state.variants[0];

  // --- Product-level setters ---

  const setField = useCallback((field, value) => {
    dispatch({ type: 'SET_FIELD', field, value });
  }, []);

  const setBrandId = useCallback((brandId, brandName) => {
    dispatch({ type: 'SET_BRAND', brandId, brandName });
  }, []);

  const setTitleRu = useCallback((value) => {
    dispatch({ type: 'SET_FIELD', field: 'titleRu', value });
    dispatch({ type: 'SET_FIELD', field: 'slug', value: transliterate(value) });
  }, []);

  const setProductAttr = useCallback((attributeId, valueId) => {
    dispatch({ type: 'SET_PRODUCT_ATTR', attributeId, valueId });
  }, []);

  const clearProductAttr = useCallback((attributeId) => {
    dispatch({ type: 'CLEAR_PRODUCT_ATTR', attributeId });
  }, []);

  const addTag = useCallback((tag) => {
    dispatch({ type: 'ADD_TAG', tag });
  }, []);

  const removeTag = useCallback((tag) => {
    dispatch({ type: 'REMOVE_TAG', tag });
  }, []);

  const resetForm = useCallback((options) => {
    dispatch({ type: 'RESET', options });
  }, []);

  // --- Variant management ---

  const switchVariant = useCallback((index) => {
    dispatch({ type: 'SWITCH_VARIANT', index });
  }, []);

  const addVariant = useCallback(() => {
    dispatch({ type: 'ADD_VARIANT' });
  }, []);

  const removeVariant = useCallback((index) => {
    dispatch({ type: 'REMOVE_VARIANT', index });
  }, []);

  // --- Per-variant field setters ---

  const setVariantField = useCallback((field, value) => {
    dispatch({ type: 'SET_VARIANT_FIELD', field, value });
  }, []);

  const setVariantAttr = useCallback((attributeId, valueIds) => {
    dispatch({ type: 'SET_VARIANT_ATTR', attributeId, valueIds });
  }, []);

  const toggleVariantValue = useCallback((attributeId, valueId) => {
    dispatch({ type: 'TOGGLE_VARIANT_VALUE', attributeId, valueId });
  }, []);

  const setSkuPrice = useCallback((valueId, prices) => {
    dispatch({ type: 'SET_SKU_PRICE', valueId, prices });
  }, []);

  const addImage = useCallback((image) => {
    dispatch({ type: 'ADD_IMAGE', image });
  }, []);

  const removeImage = useCallback((localId) => {
    dispatch({ type: 'REMOVE_IMAGE', localId });
  }, []);

  const setImages = useCallback((images) => {
    dispatch({ type: 'SET_IMAGES', images });
  }, []);

  // --- Derived / validation ---

  const isValid = useMemo(() => {
    if (!state.categoryId) return false;
    if (!state.brandId) return false;
    if (!state.titleRu.trim()) return false;
    if (!state.slug.trim()) return false;
    return true;
  }, [state.categoryId, state.brandId, state.titleRu, state.slug]);

  // Check that every variant has the minimum requirements for publishing
  const isPublishable = useMemo(() => {
    if (!isValid) return false;
    return state.variants.every((v) => {
      const hasVariantAttrs = Object.values(v.variantAttrs).some(
        (ids) => ids.length > 0,
      );
      if (!hasVariantAttrs) return false;
      if (v.images.length === 0) return false;
      if (v.variablePricing) {
        const requiredValueIds = Object.values(v.variantAttrs).flat();
        if (requiredValueIds.length === 0) return false;
        return requiredValueIds.every((valueId) => {
          const p = v.perSkuPrices[valueId];
          return p?.price && parseInt(p.price, 10) > 0;
        });
      }
      return v.priceAmount !== '' && parseInt(v.priceAmount, 10) > 0;
    });
  }, [isValid, state.variants]);

  // Build API-ready payloads

  const productPayload = useMemo(
    () => ({
      titleI18N: buildI18nPayload(state.titleRu, state.titleEn),
      slug: state.slug,
      brandId: state.brandId,
      primaryCategoryId: state.categoryId,
      ...(state.descriptionRu
        ? {
            descriptionI18N: buildI18nPayload(
              state.descriptionRu,
              state.descriptionEn,
            ),
          }
        : {}),
      ...(state.countryOfOrigin
        ? { countryOfOrigin: state.countryOfOrigin }
        : {}),
      ...(state.tags.length ? { tags: state.tags } : {}),
      // Use first variant's supplier for the product-level supplierId
      ...(state.variants[0]?.supplierId
        ? { supplierId: state.variants[0].supplierId }
        : {}),
      ...(state.variants[0]?.sourceUrl
        ? { sourceUrl: state.variants[0].sourceUrl }
        : {}),
    }),
    [
      state.titleRu,
      state.titleEn,
      state.slug,
      state.brandId,
      state.categoryId,
      state.descriptionRu,
      state.descriptionEn,
      state.countryOfOrigin,
      state.tags,
      state.variants,
    ],
  );

  const bulkAttrsPayload = useMemo(() => {
    const items = Object.entries(state.productAttrs)
      .filter(([, valueId]) => valueId)
      .map(([attributeId, attributeValueId]) => ({
        attributeId,
        attributeValueId,
      }));
    return items.length > 0 ? { items } : null;
  }, [state.productAttrs]);

  // Per-variant SKU payloads — array indexed by variant index
  const variantPayloads = useMemo(
    () =>
      state.variants.map((v) => {
        const attributeSelections = Object.entries(v.variantAttrs)
          .filter(([, valueIds]) => valueIds.length > 0)
          .map(([attributeId, valueIds]) => ({
            attributeId,
            valueIds,
          }));
        if (attributeSelections.length === 0)
          return { skuGeneratePayload: null, perSkuPriceUpdates: [] };

        // Form stores prices in rubles; backend expects kopecks (×100)
        const toKopecks = (rub) => {
          const n = parseInt(rub, 10);
          return isNaN(n) ? null : n * 100;
        };

        const useFlat = !v.variablePricing;
        const skuGeneratePayload = {
          attributeSelections,
          priceAmount:
            useFlat && v.priceAmount !== ''
              ? toKopecks(v.priceAmount)
              : null,
          priceCurrency: v.priceCurrency,
          compareAtPriceAmount:
            useFlat && v.compareAtPrice !== ''
              ? toKopecks(v.compareAtPrice)
              : null,
        };

        const perSkuPriceUpdates = v.variablePricing
          ? Object.entries(v.perSkuPrices)
              .filter(([, p]) => p.price && p.price !== '')
              .map(([valueId, p]) => ({
                valueId,
                priceAmount: toKopecks(p.price),
                compareAtPriceAmount:
                  p.compareAt && p.compareAt !== ''
                    ? toKopecks(p.compareAt)
                    : null,
              }))
          : [];

        return { skuGeneratePayload, perSkuPriceUpdates };
      }),
    [state.variants],
  );

  // Backward-compat: first variant's payloads as top-level
  const skuGeneratePayload = variantPayloads[0]?.skuGeneratePayload ?? null;
  const perSkuPriceUpdates = variantPayloads[0]?.perSkuPriceUpdates ?? [];

  // --- DynamicAttributes compatibility ---
  const handleAttributeUpdate = useCallback(
    (attributeId, selectedValues, level) => {
      if (level === 'variant') {
        dispatch({
          type: 'SET_VARIANT_ATTR',
          attributeId,
          valueIds: selectedValues,
        });
      } else {
        const valueId = selectedValues[0] ?? null;
        if (valueId) {
          dispatch({ type: 'SET_PRODUCT_ATTR', attributeId, valueId });
        } else {
          dispatch({ type: 'CLEAR_PRODUCT_ATTR', attributeId });
        }
      }
    },
    [],
  );

  const allAttrValues = useMemo(() => {
    const merged = {};
    for (const [attrId, valueId] of Object.entries(state.productAttrs)) {
      merged[attrId] = valueId ? [valueId] : [];
    }
    const v = activeVariant;
    for (const [attrId, valueIds] of Object.entries(v.variantAttrs)) {
      merged[attrId] = valueIds;
    }
    return merged;
  }, [state.productAttrs, activeVariant]);

  // --- Edit mode: hydrate from server data ---

  const hydrateFromProduct = useCallback((product, mediaAssets = []) => {
    dispatch({ type: 'HYDRATE', product, mediaAssets });
  }, []);

  // Edit mode helpers
  const isEditMode = state._serverSnapshot != null;
  const serverSnapshot = state._serverSnapshot;

  return {
    state,
    activeVariant,
    isValid,
    isPublishable,

    // Product-level setters
    setField,
    setBrandId,
    setTitleRu,
    setProductAttr,
    clearProductAttr,
    addTag,
    removeTag,
    resetForm,

    // Variant management
    switchVariant,
    addVariant,
    removeVariant,

    // Per-variant setters
    setVariantField,
    setVariantAttr,
    toggleVariantValue,
    setSkuPrice,
    addImage,
    removeImage,
    setImages,

    // DynamicAttributes compatibility
    allAttrValues,
    handleAttributeUpdate,

    // API-ready payloads
    productPayload,
    bulkAttrsPayload,
    skuGeneratePayload,
    perSkuPriceUpdates,
    variantPayloads,

    // Edit mode
    hydrateFromProduct,
    isEditMode,
    serverSnapshot,
  };
}
