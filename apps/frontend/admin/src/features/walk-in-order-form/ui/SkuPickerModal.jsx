'use client';

import { useQuery } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';

import { apiClient } from '@/shared/api/clientFetch';
import { Modal } from '@/shared/ui/Modal';
import { SearchInput } from '@/shared/ui/SearchInput';
import { cn, formatCurrency, i18n } from '@/shared/lib/utils';

// Two-step SKU picker:
//   Step 1 — debounced product search via /api/storefront/search (published
//            products only, which is exactly the gate walk-in needs).
//   Step 2 — drill into the chosen product via /api/catalog/products/:id and
//            render every SKU under every variant as a flat selectable row.
//
// SKUs that are inactive, unpriced, or priced in a non-RUB currency are
// rendered disabled — selecting them would trigger WALK_IN_SKU_NOT_USABLE
// on submit. Surfacing the constraint here keeps the 422 round-trip out
// of the happy path.

const SEARCH_DEBOUNCE_MS = 300;
const MIN_QUERY_LEN = 2;
// Backend caps `q` at 200 chars (storefront/search OpenAPI). Clamp on the
// client so a paste of a paragraph doesn't blow up as 414 URI Too Long
// without a useful error.
const MAX_QUERY_LEN = 200;

function useDebounced(value, delay) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const tid = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(tid);
  }, [value, delay]);
  return debounced;
}

function useProductSearch(query) {
  return useQuery({
    enabled: query.length >= MIN_QUERY_LEN,
    queryKey: ['walk-in', 'product-search', query],
    queryFn: () =>
      apiClient.get(
        `/api/storefront/search?q=${encodeURIComponent(query)}&limit=20`,
      ),
    staleTime: 30_000,
  });
}

function useProductDetail(productId) {
  return useQuery({
    enabled: Boolean(productId),
    queryKey: ['walk-in', 'product-detail', productId],
    queryFn: () => apiClient.get(`/api/catalog/products/${productId}`),
    staleTime: 30_000,
  });
}

// Translate a SKU + a product-level attribute lookup table into the flat
// row shape rendered in the picker. The lookup map maps attributeValueId
// → display label (RU); we build it from the product's `attributes`
// section because `SKUResponse.variantAttributes` only carries UUIDs.
function flattenSkus(product, valueLabelMap) {
  if (!product?.variants?.length) return [];
  const flat = [];
  for (const variant of product.variants) {
    for (const sku of variant.skus ?? []) {
      flat.push({
        skuId: sku.id,
        skuCode: sku.skuCode,
        // Resolve the size/color label by joining each variantAttribute's
        // resolved label. Falls back to skuCode in render if every label
        // resolves to empty.
        variantLabel: (sku.variantAttributes ?? [])
          .map((va) => valueLabelMap?.[va.attributeValueId] ?? '')
          .filter(Boolean)
          .join(' / '),
        sellingPriceAmount: sku.sellingPrice?.amount ?? null,
        currency: sku.sellingPrice?.currency ?? 'RUB',
        pricingStatus: sku.pricingStatus ?? null,
        // SKUResponse exposes `isActive: boolean` (required) — the legacy
        // `archivedAt` field was an admin-only audit timestamp that
        // didn't survive REFACT-001 wire normalisation.
        isActive: sku.isActive !== false,
      });
    }
  }
  return flat;
}

// Walk the product attribute tree to collect a {valueId → label} map.
// The catalog API returns attributes per-variant on `variant.attributes`
// in some endpoints and on `product.attributes` in others; cover both so
// the picker doesn't silently lose labels if the backend response shape
// changes between admin and storefront calls.
function buildValueLabelMap(product) {
  if (!product) return {};
  const map = {};
  const sources = [
    ...(Array.isArray(product.attributes) ? product.attributes : []),
    ...(product.variants ?? []).flatMap((v) =>
      Array.isArray(v.attributes) ? v.attributes : [],
    ),
  ];
  for (const attr of sources) {
    for (const value of attr.values ?? []) {
      const label = i18n(value.nameI18N, value.code ?? '');
      if (label) map[value.id] = label;
    }
  }
  return map;
}

function disabledReason(sku) {
  if (!sku.isActive) return 'Деактивирован';
  if (sku.sellingPriceAmount == null) return 'Цена не рассчитана';
  if (sku.currency !== 'RUB') return 'Валюта не RUB';
  return null;
}

export function SkuPickerModal({ open, onClose, onSelect }) {
  const [query, setQuery] = useState('');
  const [selectedProductId, setSelectedProductId] = useState(null);

  // Reset internal state every time the modal opens so the next session
  // doesn't see leftover search/product from the previous interaction.
  useEffect(() => {
    if (open) {
      setQuery('');
      setSelectedProductId(null);
    }
  }, [open]);

  const debouncedQuery = useDebounced(
    query.trim().slice(0, MAX_QUERY_LEN),
    SEARCH_DEBOUNCE_MS,
  );
  const search = useProductSearch(debouncedQuery);
  const detail = useProductDetail(selectedProductId);

  // Guard against the previous-product detail leaking into the current
  // SKU list while the new fetch is in flight. `detail.data` from product
  // A persists in the TanStack cache after switching to B until B
  // resolves — without this check, the picker would briefly show A's
  // SKUs under B's header.
  const detailMatchesSelection =
    !selectedProductId || detail.data?.id === selectedProductId;
  const product = detailMatchesSelection ? detail.data : null;

  const valueLabelMap = useMemo(() => buildValueLabelMap(product), [product]);
  const skus = useMemo(
    () => flattenSkus(product, valueLabelMap),
    [product, valueLabelMap],
  );

  const products = search.data?.items ?? [];

  return (
    <Modal open={open} onClose={onClose} title="Добавить товар" size="xl">
      <div className="mt-4 flex flex-col gap-4">
        <SearchInput
          value={query}
          onChange={(v) => setQuery(v.slice(0, MAX_QUERY_LEN))}
          placeholder="Поиск по названию товара..."
        />

        {selectedProductId == null ? (
          <ProductList
            query={debouncedQuery}
            isLoading={search.isFetching}
            error={search.error}
            products={products}
            onPick={setSelectedProductId}
          />
        ) : (
          <SkuList
            isLoading={detail.isFetching || !detailMatchesSelection}
            error={detail.error}
            product={product}
            skus={skus}
            onBack={() => setSelectedProductId(null)}
            onSelect={(sku) => {
              // Belt-and-braces: re-check the gate at click time. The
              // button is disabled when reason is set, but concurrent
              // rendering / extension click injection could fire.
              if (disabledReason(sku)) return;
              onSelect({
                skuId: sku.skuId,
                skuCode: sku.skuCode,
                productName: i18n(product?.titleI18N, product?.slug ?? ''),
                variantLabel: sku.variantLabel,
                sellingPriceAmount: sku.sellingPriceAmount,
                currency: sku.currency,
              });
              onClose();
            }}
          />
        )}
      </div>
    </Modal>
  );
}

function ProductList({ query, isLoading, error, products, onPick }) {
  if (query.length < MIN_QUERY_LEN) {
    return (
      <p className="text-app-muted py-8 text-center text-sm">
        Введите минимум {MIN_QUERY_LEN} символа для поиска товара
      </p>
    );
  }
  if (isLoading) {
    return <p className="text-app-muted py-8 text-center text-sm">Ищем…</p>;
  }
  if (error) {
    // Preserve the original ApiError message so retryAfter / 401 / 403
    // surface meaningfully instead of a one-size-fits-all string.
    const retry = error?.retryAfter
      ? ` (повторите через ${error.retryAfter} сек)`
      : '';
    return (
      <p className="text-app-danger py-8 text-center text-sm" role="alert">
        {error?.message ?? 'Не удалось загрузить результаты поиска'}
        {retry}
      </p>
    );
  }
  if (products.length === 0) {
    return (
      <p className="text-app-muted py-8 text-center text-sm">
        Ничего не найдено
      </p>
    );
  }
  return (
    <ul className="border-app-border divide-app-border bg-app-panel max-h-[420px] divide-y overflow-y-auto rounded-2xl border">
      {products.map((p) => {
        const brandName = p.brand?.name ?? null;
        return (
          <li key={p.id}>
            <button
              type="button"
              onClick={() => onPick(p.id)}
              className="hover:bg-app-card flex w-full items-center gap-3 px-4 py-3 text-left transition-colors"
            >
              <span className="text-app-text flex-1 truncate text-sm font-medium">
                {i18n(p.titleI18N, p.slug ?? p.id)}
              </span>
              {brandName && (
                <span className="text-app-muted text-xs">{brandName}</span>
              )}
            </button>
          </li>
        );
      })}
    </ul>
  );
}

function SkuList({ isLoading, error, product, skus, onBack, onSelect }) {
  return (
    <div className="flex flex-col gap-3">
      <button
        type="button"
        onClick={onBack}
        className="text-app-muted hover:text-app-text self-start text-sm"
      >
        ← К списку товаров
      </button>

      {product && (
        <div className="text-app-text text-base font-semibold">
          {i18n(product.titleI18N, product.slug)}
        </div>
      )}

      {isLoading && (
        <p className="text-app-muted py-6 text-center text-sm">
          Загружаем варианты…
        </p>
      )}
      {error && (
        <p className="text-app-danger py-6 text-center text-sm" role="alert">
          {error?.message ?? 'Не удалось загрузить варианты товара'}
        </p>
      )}

      {!isLoading && !error && skus.length === 0 && (
        <p className="text-app-muted py-6 text-center text-sm">
          У этого товара ещё нет SKU
        </p>
      )}

      {skus.length > 0 && (
        <ul className="border-app-border divide-app-border bg-app-panel max-h-[360px] divide-y overflow-y-auto rounded-2xl border">
          {skus.map((sku) => {
            const reason = disabledReason(sku);
            const disabled = Boolean(reason);
            return (
              <li key={sku.skuId}>
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => onSelect(sku)}
                  className={cn(
                    'flex w-full items-center gap-3 px-4 py-3 text-left transition-colors',
                    disabled
                      ? 'cursor-not-allowed opacity-60'
                      : 'hover:bg-app-card',
                  )}
                  title={reason ?? undefined}
                >
                  <span className="text-app-text flex-1 text-sm font-medium">
                    {sku.variantLabel || sku.skuCode || '—'}
                  </span>
                  {sku.variantLabel && (
                    <span className="text-app-muted font-mono text-xs">
                      {sku.skuCode}
                    </span>
                  )}
                  <span
                    className={cn(
                      'text-app-text text-sm font-semibold',
                      disabled && 'text-app-muted',
                    )}
                  >
                    {sku.sellingPriceAmount != null
                      ? formatCurrency(sku.sellingPriceAmount / 100)
                      : '—'}
                  </span>
                  {reason && (
                    <span className="text-app-danger text-xs">{reason}</span>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
