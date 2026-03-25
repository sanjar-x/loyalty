'use client';

import { useCallback, useMemo, useReducer } from 'react';

/**
 * Unified state hook for the product creation form.
 *
 * Field naming follows openapi.json contracts (camelCase).
 * This hook manages form state only — no API calls.
 *
 * Usage:
 *   const form = useProductForm({ categoryId, defaultTitle });
 *   <BrandSelect value={form.state.brandId} onChange={form.setBrandId} />
 */

// ---------------------------------------------------------------------------
// Initial state
// ---------------------------------------------------------------------------

function buildInitialState({ categoryId = null, defaultTitle = '' } = {}) {
  return {
    // Step 1: Category (set from route, immutable within form)
    categoryId,

    // Step 3: Brand
    brandId: null,
    brandName: '', // display-only, not sent to API

    // Step 4: Core fields
    titleRu: defaultTitle,
    titleEn: '',
    slug: '',
    descriptionRu: '',
    descriptionEn: '',

    // Step 4: Product-level attributes (level: "product")
    // { [attributeId]: attributeValueId }
    productAttrs: {},

    // Step 4: Variant-level attributes (level: "variant")
    // { [attributeId]: [valueId, valueId, ...] }  — multi-select
    variantAttrs: {},

    // Delivery
    deliveryMode: 'china', // "china" | "stock"
    supplierId: null,
    sourceUrl: '',

    // Price
    priceAmount: '', // string for input, convert to int on submit
    compareAtPrice: '', // string for input
    priceCurrency: 'RUB',
    variablePricing: false,
    // { [sizeValueId]: { price: string, compareAt: string } }
    perSkuPrices: {},

    // Media (local state, uploaded after product create)
    images: [], // [{ localId, file?, url?, source: "file"|"url", alt }]
    sizeGuide: null, // { file?, url, source: "file"|"url" } or null

    // Tags
    tags: [],
    countryOfOrigin: '',
  };
}

// ---------------------------------------------------------------------------
// Reducer
// ---------------------------------------------------------------------------

function formReducer(state, action) {
  switch (action.type) {
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

    case 'SET_VARIANT_ATTR':
      return {
        ...state,
        variantAttrs: {
          ...state.variantAttrs,
          [action.attributeId]: action.valueIds,
        },
      };

    case 'TOGGLE_VARIANT_VALUE': {
      const current = state.variantAttrs[action.attributeId] ?? [];
      const has = current.includes(action.valueId);
      const next = has
        ? current.filter((id) => id !== action.valueId)
        : [...current, action.valueId];
      // Clean orphan price when removing a variant value
      let nextPrices = state.perSkuPrices;
      if (has && state.perSkuPrices[action.valueId]) {
        nextPrices = { ...state.perSkuPrices };
        delete nextPrices[action.valueId];
      }
      return {
        ...state,
        variantAttrs: { ...state.variantAttrs, [action.attributeId]: next },
        perSkuPrices: nextPrices,
      };
    }

    case 'SET_SKU_PRICE':
      return {
        ...state,
        perSkuPrices: {
          ...state.perSkuPrices,
          [action.valueId]: {
            ...(state.perSkuPrices[action.valueId] ?? {}),
            ...action.prices,
          },
        },
      };

    case 'ADD_IMAGE':
      return { ...state, images: [...state.images, action.image] };

    case 'REMOVE_IMAGE':
      return {
        ...state,
        images: state.images.filter((img) => img.localId !== action.localId),
      };

    case 'SET_IMAGES':
      return { ...state, images: action.images };

    case 'ADD_TAG':
      if (state.tags.includes(action.tag)) return state;
      return { ...state, tags: [...state.tags, action.tag] };

    case 'REMOVE_TAG':
      return { ...state, tags: state.tags.filter((t) => t !== action.tag) };

    case 'RESET':
      return buildInitialState(action.options);

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
    .replace(/^-+|-+$/g, '');
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

  // --- Field setters ---

  const setField = useCallback((field, value) => {
    dispatch({ type: 'SET_FIELD', field, value });
  }, []);

  const setBrandId = useCallback((brandId, brandName) => {
    dispatch({ type: 'SET_BRAND', brandId, brandName });
  }, []);

  const setTitleRu = useCallback((value) => {
    dispatch({ type: 'SET_FIELD', field: 'titleRu', value });
    // Auto-generate slug from title
    dispatch({ type: 'SET_FIELD', field: 'slug', value: transliterate(value) });
  }, []);

  const setProductAttr = useCallback((attributeId, valueId) => {
    dispatch({ type: 'SET_PRODUCT_ATTR', attributeId, valueId });
  }, []);

  const clearProductAttr = useCallback((attributeId) => {
    dispatch({ type: 'CLEAR_PRODUCT_ATTR', attributeId });
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

  const addTag = useCallback((tag) => {
    dispatch({ type: 'ADD_TAG', tag });
  }, []);

  const removeTag = useCallback((tag) => {
    dispatch({ type: 'REMOVE_TAG', tag });
  }, []);

  const resetForm = useCallback((options) => {
    dispatch({ type: 'RESET', options });
  }, []);

  // --- Derived / validation ---

  // Minimum required fields for product creation (draft save)
  const isValid = useMemo(() => {
    if (!state.categoryId) return false;
    if (!state.brandId) return false;
    if (!state.titleRu.trim()) return false;
    if (!state.slug.trim()) return false;
    return true;
  }, [state.categoryId, state.brandId, state.titleRu, state.slug]);

  // Stricter check: product can be published (has price + SKU attrs)
  const isPublishable = useMemo(() => {
    if (!isValid) return false;
    // Need at least one variant attr with values for SKU generation
    const hasVariantAttrs = Object.values(state.variantAttrs).some(
      (ids) => ids.length > 0,
    );
    if (!hasVariantAttrs) return false;
    // Need price
    if (state.variablePricing) {
      return Object.values(state.perSkuPrices).some(
        (p) => p.price && parseInt(p.price, 10) > 0,
      );
    }
    return state.priceAmount !== '' && parseInt(state.priceAmount, 10) > 0;
  }, [
    isValid,
    state.variantAttrs,
    state.variablePricing,
    state.priceAmount,
    state.perSkuPrices,
  ]);

  // Build API-ready payloads (no API calls — just data shaping)

  const productPayload = useMemo(
    () => ({
      titleI18N: {
        ru: state.titleRu,
        ...(state.titleEn ? { en: state.titleEn } : {}),
      },
      slug: state.slug,
      brandId: state.brandId,
      primaryCategoryId: state.categoryId,
      ...(state.descriptionRu
        ? {
            descriptionI18N: {
              ru: state.descriptionRu,
              ...(state.descriptionEn ? { en: state.descriptionEn } : {}),
            },
          }
        : {}),
      ...(state.supplierId ? { supplierId: state.supplierId } : {}),
      ...(state.sourceUrl ? { sourceUrl: state.sourceUrl } : {}),
      ...(state.countryOfOrigin
        ? { countryOfOrigin: state.countryOfOrigin }
        : {}),
      ...(state.tags.length ? { tags: state.tags } : {}),
    }),
    [
      state.titleRu,
      state.titleEn,
      state.slug,
      state.brandId,
      state.categoryId,
      state.descriptionRu,
      state.descriptionEn,
      state.supplierId,
      state.sourceUrl,
      state.countryOfOrigin,
      state.tags,
    ],
  );

  // null when empty — submit flow should skip the API call
  const bulkAttrsPayload = useMemo(() => {
    const items = Object.entries(state.productAttrs)
      .filter(([, valueId]) => valueId)
      .map(([attributeId, attributeValueId]) => ({
        attributeId,
        attributeValueId,
      }));
    return items.length > 0 ? { items } : null;
  }, [state.productAttrs]);

  // null when no variant attrs selected — submit flow should skip SKU generation
  const skuGeneratePayload = useMemo(() => {
    const attributeSelections = Object.entries(state.variantAttrs)
      .filter(([, valueIds]) => valueIds.length > 0)
      .map(([attributeId, valueIds]) => ({
        attributeId,
        valueIds,
      }));
    if (attributeSelections.length === 0) return null;

    // Variable pricing: generate SKUs with null price, then PATCH each individually
    // Flat pricing: generate all SKUs with the same price
    const useFlat = !state.variablePricing;

    return {
      attributeSelections,
      priceAmount: useFlat && state.priceAmount !== ''
        ? parseInt(state.priceAmount, 10)
        : null,
      priceCurrency: state.priceCurrency,
      compareAtPriceAmount: useFlat && state.compareAtPrice !== ''
        ? parseInt(state.compareAtPrice, 10)
        : null,
    };
  }, [
    state.variantAttrs,
    state.variablePricing,
    state.priceAmount,
    state.priceCurrency,
    state.compareAtPrice,
  ]);

  // Per-SKU price updates for variable pricing (used in submit flow Step 8)
  // Returns array of { valueId, priceAmount, compareAtPriceAmount } for PATCH calls
  const perSkuPriceUpdates = useMemo(() => {
    if (!state.variablePricing) return [];
    return Object.entries(state.perSkuPrices)
      .filter(([, p]) => p.price && p.price !== '')
      .map(([valueId, p]) => ({
        valueId,
        priceAmount: parseInt(p.price, 10),
        compareAtPriceAmount: p.compareAt && p.compareAt !== ''
          ? parseInt(p.compareAt, 10)
          : null,
      }));
  }, [state.variablePricing, state.perSkuPrices]);

  // --- Convenience: attribute handler for DynamicAttributes compatibility ---
  // DynamicAttributes passes values as arrays: { [attributeId]: [valueId, ...] }
  // This adapter maps between the two formats based on attribute level.
  //
  // Product-level: API contract (POST /products/{id}/attributes/bulk) accepts
  // exactly ONE attributeValueId per attributeId — so we take selectedValues[0].
  // DynamicAttributes enforces single-select UI for product-level attrs.

  const handleAttributeUpdate = useCallback(
    (attributeId, selectedValues, level) => {
      if (level === 'variant') {
        dispatch({
          type: 'SET_VARIANT_ATTR',
          attributeId,
          valueIds: selectedValues,
        });
      } else {
        // Product-level: strictly single value per attribute (API constraint)
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

  // Merge productAttrs + variantAttrs into one object for DynamicAttributes
  const allAttrValues = useMemo(() => {
    const merged = {};
    for (const [attrId, valueId] of Object.entries(state.productAttrs)) {
      merged[attrId] = valueId ? [valueId] : [];
    }
    for (const [attrId, valueIds] of Object.entries(state.variantAttrs)) {
      merged[attrId] = valueIds;
    }
    return merged;
  }, [state.productAttrs, state.variantAttrs]);

  return {
    state,
    isValid,
    isPublishable,

    // Field setters
    setField,
    setBrandId,
    setTitleRu,
    setProductAttr,
    clearProductAttr,
    setVariantAttr,
    toggleVariantValue,
    setSkuPrice,
    addImage,
    removeImage,
    setImages,
    addTag,
    removeTag,
    resetForm,

    // DynamicAttributes compatibility
    allAttrValues,
    handleAttributeUpdate,

    // API-ready payloads (read-only, for submit step)
    productPayload,
    bulkAttrsPayload,
    skuGeneratePayload,
    perSkuPriceUpdates,
  };
}
