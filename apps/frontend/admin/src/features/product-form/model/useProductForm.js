'use client';

import { useCallback, useMemo, useReducer } from 'react';
import { PRICING_FAILURE_STATUSES, skuPublishable } from '@/entities/product';
import { buildI18nPayload } from '@/shared/lib/utils';
import { genId } from '@/shared/lib/genId';

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
// Cross-field invariants
// ---------------------------------------------------------------------------

/**
 * Maps the backend supplier type to the only currency we accept for the
 * variant's `purchasePrice`. Backend SupplierResponse.type is the
 * source of truth — there's no separate "delivery mode" field on the
 * domain model; cross-border vs local pricing currency follows from
 * the supplier directly.
 *
 *  - `cross_border` → CNY (paid in yuan to upstream broker)
 *  - `local`        → RUB (already on the warehouse)
 *  - missing/unknown supplier → RUB (sensible default so the input
 *    stays editable before a supplier is picked)
 */
export function purchaseCurrencyFromSupplierType(supplierType) {
  return supplierType === 'cross_border' ? 'CNY' : 'RUB';
}

// ---------------------------------------------------------------------------
// Initial state helpers
// ---------------------------------------------------------------------------

const VARIANT_LOCAL_ID_PREFIX = 'v';

function genLocalId() {
  return genId(VARIANT_LOCAL_ID_PREFIX);
}

function buildVariantState() {
  return {
    localId: genLocalId(),
    variantAttrs: {},
    images: [],
    sizeGuide: null,
    supplierId: null,
    sourceUrl: '',
    // Money fields use the canonical { amount, currency } shape consumed by
    // <MoneyInput> and the catalog API builders (CAT-002). `amount` is held in
    // user-facing units (rubles, yuans, …) and converted to the backend's
    // smallest-unit representation at submit time.
    price: null,
    compareAtPrice: null,
    // ADR-005: purchasePrice drives the autonomous pricing recompute pipeline.
    // It is variant-level today (one value applied to every SKU under the
    // variant); per-SKU purchase prices may follow as a separate ticket.
    purchasePrice: null,
    variablePricing: false,
    // perSkuPrices[valueId] = { price: money|null, compareAt: money|null, skuId }
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
 * Backend money helpers (CAT-002).
 *
 * Backend stores `MoneySchema.amount` in smallest currency units (kopecks for
 * RUB, fen for CNY, …). The form keeps `amount` in user-facing units (rubles,
 * yuans, …) so <MoneyInput> binds 1:1 to what the user types.
 *
 * `fromMoneyKopecks` is intentionally lossy below 1 user-unit (truncates the
 * fractional part) — admin pricing is integer-only by product convention.
 */
function fromMoneyKopecks(money) {
  if (!money || money.amount == null) return null;
  return {
    amount: Math.round(money.amount / 100),
    currency: money.currency ?? 'RUB',
  };
}

function toMoneyKopecks(money) {
  if (!money || money.amount == null || money.amount === '') return null;
  const amount = parseInt(money.amount, 10);
  if (Number.isNaN(amount)) return null;
  return { amount: amount * 100, currency: money.currency ?? 'RUB' };
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

  // Collect ALL product-level attribute assignments into a multi-value map
  // first — during creation, variant attr values are also bulk-assigned at
  // product level, so the same attributeId can appear with several values
  // (one per chosen variant value). If some SKUs weren't generated, this
  // map serves as the authoritative source for variantAttrs below.
  const productAttrMulti = {};
  for (const attr of product.attributes ?? []) {
    if (!productAttrMulti[attr.attributeId])
      productAttrMulti[attr.attributeId] = [];
    if (!productAttrMulti[attr.attributeId].includes(attr.attributeValueId)) {
      productAttrMulti[attr.attributeId].push(attr.attributeValueId);
    }
  }

  // `productAttrs` is the form's single-value view of *true* product-level
  // attributes — attributes whose backend record has exactly one value. A
  // multi-value entry (e.g. 5 sizes) is a variant-level attribute that was
  // also bulk-assigned at product scope; it must NOT be diffed through the
  // product-attribute API on save (useUpdateProduct) or all-but-one of the
  // values get torn down on each edit. Variant-level attributes flow
  // through `variant.variantAttrs` → SKU.variantAttributes instead.
  const productAttrs = {};
  for (const [attrId, valueIds] of Object.entries(productAttrMulti)) {
    if (valueIds.length === 1) {
      productAttrs[attrId] = valueIds[0];
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
      .filter((s) => s.isActive && (s.resolvedPrice ?? s.price)?.amount != null)
      .map((s) => (s.resolvedPrice ?? s.price).amount);
    const allSamePrice =
      activePrices.length > 0 &&
      activePrices.every((p) => p === activePrices[0]);
    const variablePricing = activePrices.length > 1 && !allSamePrice;

    // Uniform money objects: prefer variant.defaultPrice (carries currency),
    // fall back to the first SKU's resolved/compare price.
    const firstSkuPriceMoney = skus[0]?.resolvedPrice ?? skus[0]?.price ?? null;
    const uniformPriceMoney =
      variant.defaultPrice ??
      (allSamePrice && firstSkuPriceMoney
        ? { ...firstSkuPriceMoney, amount: activePrices[0] }
        : null) ??
      firstSkuPriceMoney;
    const uniformCompareMoney = skus[0]?.compareAtPrice ?? null;
    // Variant-level mirror of the SKU purchasePrice (CAT-002): all SKUs of a
    // variant currently share one purchasePrice, so the first SKU's value is
    // representative for prefill purposes.
    const uniformPurchaseMoney = skus[0]?.purchasePrice ?? null;

    // Per-SKU prices for variable pricing (use resolvedPrice for display)
    const perSkuPrices = {};
    if (variablePricing) {
      for (const sku of skus) {
        // Use first variantAttribute valueId as key (matches creation form convention)
        const valueId = sku.variantAttributes?.[0]?.attributeValueId;
        if (valueId) {
          const effectivePriceMoney = sku.resolvedPrice ?? sku.price ?? null;
          perSkuPrices[valueId] = {
            price: fromMoneyKopecks(effectivePriceMoney),
            compareAt: fromMoneyKopecks(sku.compareAtPrice),
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
      supplierId: product.supplierId ?? null,
      sourceUrl: product.sourceUrl ?? '',
      price: fromMoneyKopecks(uniformPriceMoney),
      compareAtPrice: fromMoneyKopecks(uniformCompareMoney),
      purchasePrice: fromMoneyKopecks(uniformPurchaseMoney),
      variablePricing,
      perSkuPrices,
      // CAT-012: skus carry the pricing-pipeline FSM (sellingPrice, status,
      // failureReason) so `isPublishable` can gate the publish button on
      // recompute readiness, and the SSE consumer (CAT-005) can merge live
      // pricing events into form state by `id`.
      skus: skus.map((s) => ({
        id: s.id,
        skuCode: s.skuCode,
        version: s.version,
        // Money fields stay in backend smallest units (kopecks) here — the
        // form does not bind these to user inputs, only reads them for
        // gating + display in the parent <SkuPricingTable>.
        price: s.price ?? null,
        purchasePrice: s.purchasePrice ?? null,
        sellingPrice: s.sellingPrice ?? null,
        pricingStatus: s.pricingStatus ?? null,
        pricedAt: s.pricedAt ?? null,
        pricedFailureReason: s.pricedFailureReason ?? null,
      })),
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
      const updated = { ...v, [action.field]: action.value };
      // purchasePrice currency follows supplier.type now — there's no
      // dedicated cross-field invariant here because ProductDetailsForm
      // re-derives `purchaseCurrency` from the selected supplier on
      // every render and feeds it back through MoneyInput's
      // `currencies` prop, which auto-rewrites the stored value when
      // the single allowed option changes.
      return {
        ...state,
        variants: state.variants.map((item, i) => (i === vi ? updated : item)),
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

    case 'MERGE_SKU_PRICING_EVENT': {
      // SSE push from /skus/pricing-events — merge the new pricing FSM fields
      // onto whichever variant.skus row matches by id. Other fields
      // (price/purchasePrice/version) are deliberately left alone — they
      // belong to the SKU edit flow, not the recompute pipeline.
      //
      // Track the touched flag *per variant* so we don't hand a fresh
      // identity to every variant after the matched one (would defeat
      // React.memo / effect-deps downstream). Use undefined-checks for every
      // field (including pricingStatus) so backend `null` actually clears
      // stale state — `??` would silently keep the prior value.
      const e = action.event;
      if (!e?.skuId) return state;
      let anyTouched = false;
      const variants = state.variants.map((v) => {
        if (!v.skus?.length) return v;
        let variantTouched = false;
        const skus = v.skus.map((s) => {
          if (s.id !== e.skuId) return s;
          variantTouched = true;
          return {
            ...s,
            pricingStatus:
              e.pricingStatus !== undefined ? e.pricingStatus : s.pricingStatus,
            sellingPrice:
              e.sellingPrice !== undefined ? e.sellingPrice : s.sellingPrice,
            pricedAt: e.pricedAt !== undefined ? e.pricedAt : s.pricedAt,
            pricedFailureReason:
              e.pricedFailureReason !== undefined
                ? e.pricedFailureReason
                : s.pricedFailureReason,
          };
        });
        if (!variantTouched) return v;
        anyTouched = true;
        return { ...v, skus };
      });
      return anyTouched ? { ...state, variants } : state;
    }

    default:
      return state;
  }
}

// ---------------------------------------------------------------------------
// Slug generation helper
// ---------------------------------------------------------------------------

// Lowercase ASCII letters/digits with single hyphens, 1+ chars. Mirrors the
// backend slug invariant; exported so the UI can show an inline error before
// submit instead of waiting for a 422.
export const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

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
  const activeVariant =
    state.variants[state.activeVariantIndex] ?? state.variants[0];

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
    // Manual slug edits must match the backend pattern (see SLUG_RE above)
    // — guard here so invalid input fails locally instead of via 422.
    if (!SLUG_RE.test(state.slug)) return false;
    return true;
  }, [state.categoryId, state.brandId, state.titleRu, state.slug]);

  const isEditMode = state._serverSnapshot != null;

  // Aggregated pricing-pipeline state across every SKU on the product (edit
  // mode only — create mode has no SKUs yet). Drives the publish button hint
  // text in <ProductDetailsForm>.
  const pricingState = useMemo(() => {
    const skus = state.variants.flatMap((v) => v.skus ?? []);
    const autonomous = skus.filter((s) => s.purchasePrice && !s.price);
    const allSkusPending =
      autonomous.length > 0 &&
      autonomous.every((s) => s.pricingStatus === 'pending');
    const anyFailure = skus.some((s) =>
      PRICING_FAILURE_STATUSES.includes(s.pricingStatus),
    );
    const failureSku = skus.find((s) =>
      PRICING_FAILURE_STATUSES.includes(s.pricingStatus),
    );
    return {
      allSkusPending,
      anyFailure,
      failureReason: failureSku?.pricedFailureReason ?? null,
      failureStatus: failureSku?.pricingStatus ?? null,
    };
  }, [state.variants]);

  // Check that every variant has the minimum requirements for publishing.
  //
  // CAT-008 / backend CAT-009: backend now accepts publish when *either* a
  // manual `sku.price` *or* an autonomous `sku.sellingPrice` is set.
  // CAT-012 / backend CAT-011: in edit mode, the autonomous fallback only
  // counts when the recompute pipeline has actually landed a result for the
  // SKU — `pricingStatus === 'priced'`. While we are still waiting on the
  // recompute (`pending`) or it failed (`formula_error` / `stale_fx` /
  // `missing_purchase_price`), publish stays gated so the user does not get
  // a 422 from backend.
  const isPublishable = useMemo(() => {
    if (!isValid) return false;
    return state.variants.every((v) => {
      const hasVariantAttrs = Object.values(v.variantAttrs).some(
        (ids) => ids.length > 0,
      );
      if (!hasVariantAttrs) return false;
      if (v.images.length === 0) return false;

      // Edit mode: gate at the SKU level using the pricing FSM the server
      // attached to each row. Every SKU must be individually publishable.
      if (isEditMode && v.skus?.length) {
        return v.skus.every(skuPublishable);
      }

      // Create mode: no SKUs exist yet. Fall back to the form-level fields
      // (CAT-008 logic) since there is no pricingStatus to consult.
      const variantPurchaseAmount = Number(v.purchasePrice?.amount ?? 0);
      const hasPurchaseFallback = variantPurchaseAmount > 0;
      if (v.variablePricing) {
        const requiredValueIds = Object.values(v.variantAttrs).flat();
        if (requiredValueIds.length === 0) return false;
        return requiredValueIds.every((valueId) => {
          const p = v.perSkuPrices[valueId];
          if (p?.price?.amount != null && Number(p.price.amount) > 0)
            return true;
          return hasPurchaseFallback;
        });
      }
      const flatPriceAmount = Number(v.price?.amount ?? 0);
      return flatPriceAmount > 0 || hasPurchaseFallback;
    });
  }, [isValid, isEditMode, state.variants]);

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

  // Per-variant SKU payloads — array indexed by variant index.
  // After CAT-002 the catalog write API takes nested MoneySchema objects
  // (`price`, `compareAtPrice`, `purchasePrice`); the legacy split-amount /
  // split-currency fields are no longer accepted.
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
          return {
            skuGeneratePayload: null,
            perSkuPriceUpdates: [],
            variantPurchasePrice: null,
          };

        const useFlat = !v.variablePricing;
        const skuGeneratePayload = {
          attributeSelections,
          price: useFlat ? toMoneyKopecks(v.price) : null,
          compareAtPrice: useFlat ? toMoneyKopecks(v.compareAtPrice) : null,
        };

        const perSkuPriceUpdates = v.variablePricing
          ? Object.entries(v.perSkuPrices)
              .filter(
                ([, p]) => p?.price?.amount != null && p.price.amount !== '',
              )
              .map(([valueId, p]) => ({
                valueId,
                price: toMoneyKopecks(p.price),
                compareAtPrice: toMoneyKopecks(p.compareAt),
              }))
          : [];

        // Variant-level purchasePrice — applied to every SKU during the
        // post-generate PATCH step (see useSubmitProduct).
        const variantPurchasePrice = toMoneyKopecks(v.purchasePrice);

        return {
          skuGeneratePayload,
          perSkuPriceUpdates,
          variantPurchasePrice,
        };
      }),
    [state.variants],
  );

  // Backward-compat: first variant's payloads as top-level. Wrapped in useMemo
  // so identity stays stable when variantPayloads doesn't change — otherwise
  // they'd be fresh references every render and bust the useMemo at the
  // bottom of the hook (which lists them as deps).
  const skuGeneratePayload = useMemo(
    () => variantPayloads[0]?.skuGeneratePayload ?? null,
    [variantPayloads],
  );
  const perSkuPriceUpdates = useMemo(
    () => variantPayloads[0]?.perSkuPriceUpdates ?? [],
    [variantPayloads],
  );

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

  // CAT-012: SSE consumer feeds events here. Merges pricing FSM fields onto
  // the matching variant.skus[].
  const mergeSkuPricingEvent = useCallback((event) => {
    dispatch({ type: 'MERGE_SKU_PRICING_EVENT', event });
  }, []);

  // Edit mode helpers
  const serverSnapshot = state._serverSnapshot;

  // Stable identity for the returned object — without this, every render of
  // useProductForm produces a fresh object literal, defeating useMemo deps
  // in ProductDetailsForm (`useMemo(() => ..., [form, ...])`).
  return useMemo(
    () => ({
      state,
      activeVariant,
      isValid,
      isPublishable,
      pricingState,

      setField,
      setBrandId,
      setTitleRu,
      setProductAttr,
      clearProductAttr,
      addTag,
      removeTag,
      resetForm,

      switchVariant,
      addVariant,
      removeVariant,

      setVariantField,
      setVariantAttr,
      toggleVariantValue,
      setSkuPrice,
      addImage,
      removeImage,
      setImages,

      allAttrValues,
      handleAttributeUpdate,

      productPayload,
      bulkAttrsPayload,
      skuGeneratePayload,
      perSkuPriceUpdates,
      variantPayloads,

      hydrateFromProduct,
      mergeSkuPricingEvent,
      isEditMode,
      serverSnapshot,
    }),
    [
      state,
      activeVariant,
      isValid,
      isPublishable,
      pricingState,
      setField,
      setBrandId,
      setTitleRu,
      setProductAttr,
      clearProductAttr,
      addTag,
      removeTag,
      resetForm,
      switchVariant,
      addVariant,
      removeVariant,
      setVariantField,
      setVariantAttr,
      toggleVariantValue,
      setSkuPrice,
      addImage,
      removeImage,
      setImages,
      allAttrValues,
      handleAttributeUpdate,
      productPayload,
      bulkAttrsPayload,
      skuGeneratePayload,
      perSkuPriceUpdates,
      variantPayloads,
      hydrateFromProduct,
      mergeSkuPricingEvent,
      isEditMode,
      serverSnapshot,
    ],
  );
}
