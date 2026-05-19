'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import {
  changeProductStatus,
  CompletenessPanel,
  computePublishGate,
  PRICING_FAILURE_STATUSES,
  PRODUCT_STATUS_LABELS,
  PRODUCT_STATUS_TONES,
  ProductDetailSkeleton,
  productKeys,
  SkuPricingTable,
  useProduct,
  useProductCompleteness,
  useSkuPricingEvents,
  useValidatePublish,
} from '@/entities/product';
import { useBrand } from '@/entities/brand';
import {
  categoryLabel,
  findCategoryById,
  useCategoryTree,
} from '@/entities/category';
import {
  PublishGateBlocker,
  StatusTransitionBar,
  usePublishProduct,
} from '@/features/product-status-change';
import { BulkPurchasePriceModal } from '@/features/sku-bulk-pricing';
import { ApiErrorState } from '@/shared/ui/ApiErrorState';
import { i18n } from '@/shared/lib/utils';
import { useToast } from '@/shared/hooks/useToast';
import styles from './page.module.css';

/**
 * Flatten ProductResponse → flat SKU list with the variant attribute info each
 * row needs. Backend lays SKUs out as `product.variants[].skus[]`; the pricing
 * table renders one row per SKU regardless of variant grouping.
 */
function flattenSkus(product) {
  if (!product?.variants) return [];
  const out = [];
  for (const variant of product.variants) {
    for (const sku of variant.skus ?? []) out.push(sku);
  }
  return out;
}

/**
 * SKU pricing surface — table + bulk modal trigger. Pure presentation: the
 * live state lives in the parent so the publish gate (in <StatusTransitionBar>)
 * and <SkuPricingTable> stay in sync. Bulk modal state was lifted out of this
 * component so PublishGateBlocker can drive it too (CAT-020).
 */
function PricingSurface({ pricingSkus, onOpenBulk }) {
  return (
    <section className={styles.skuSection}>
      <div className={styles.skuHeader}>
        <h2 className={styles.skuTitle}>Цены SKU</h2>
        <button
          type="button"
          onClick={() => onOpenBulk(null)}
          disabled={pricingSkus.length === 0}
          className="bg-app-text-dark rounded-lg px-3 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Закупочные цены — массово
        </button>
      </div>
      <SkuPricingTable skus={pricingSkus} />
    </section>
  );
}

export default function ProductDetailPage() {
  const { productId } = useParams();
  const queryClient = useQueryClient();
  const [transitionError, setTransitionError] = useState(null);
  // CAT-019/CAT-020: when backend rejects publish with PRODUCT_NOT_READY it
  // attaches a per-SKU diagnostics array. We surface that as a blocker panel
  // instead of a generic toast.
  const [publishDiagnostics, setPublishDiagnostics] = useState(null);
  // Bulk modal state lifted from <PricingSurface> so the blocker can
  // open it focused on a specific SKU.
  const [bulkOpen, setBulkOpen] = useState(false);
  const [bulkHighlightSkuId, setBulkHighlightSkuId] = useState(null);

  const {
    data: product,
    isPending: productLoading,
    error: productError,
    refetch: refetchProduct,
  } = useProduct(productId);

  const { data: completeness } = useProductCompleteness(productId);

  // Brand/category readable labels. Backend `ProductResponse` only ships
  // ids — the list endpoint denormalises brandName/categoryI18N but the
  // detail endpoint doesn't, so we lookup against the cached reference
  // catalogues. Both `useBrand` and `useCategoryTree` carry a 5-minute
  // staleTime and are typically already hot from the products list page.
  const { data: brand } = useBrand(product?.brandId);
  const { data: categoryTree = [] } = useCategoryTree();
  const categoryNode = useMemo(
    () => findCategoryById(categoryTree, product?.primaryCategoryId),
    [categoryTree, product?.primaryCategoryId],
  );

  // CAT-C1.1 / F-3: proactive publish-gate verdict. Backend returns
  // `{ ok, gateFailures, skuDiagnostics }` without raising 4xx — we render
  // the blocker live whenever ok=false, instead of waiting for a failed
  // PATCH /status to surface 422 PRODUCT_NOT_READY. SSE pricing events
  // already invalidate productKeys.detail(...), which cascades into the
  // validatePublish key (nested), so the verdict refreshes in real-time
  // as recompute lands.
  const validateEnabled = Boolean(
    product && product.status !== 'published' && product.status !== 'archived',
  );
  const { data: publishVerdict } = useValidatePublish(productId, {
    enabled: validateEnabled,
  });

  const initialSkus = useMemo(() => flattenSkus(product), [product]);

  // CAT-012: pricing state hoisted to the page level so both <PricingSurface>
  // (table + bulk modal) and <StatusTransitionBar> (publish gate) read from
  // the same source of truth. SSE events (CAT-005) merge in here.
  //
  // React 19 idiom for "reseed local state when an identity changes" — uses
  // a setState during render guarded by a stored seed key, instead of the
  // useEffect → setState antipattern flagged by react-hooks/no-deriving-...
  const [pricingSkus, setPricingSkus] = useState(initialSkus);
  const [seedKey, setSeedKey] = useState(product?.version ?? null);
  if (product && seedKey !== product.version) {
    setSeedKey(product.version);
    setPricingSkus(initialSkus);
  }

  const handlePricingEvent = useCallback(
    (event) => {
      if (!event?.skuId) return;
      setPricingSkus((prev) =>
        prev.map((sku) =>
          sku.id === event.skuId
            ? {
                ...sku,
                pricingStatus:
                  event.pricingStatus !== undefined
                    ? event.pricingStatus
                    : sku.pricingStatus,
                // Use undefined-check (not ??) so a backend null actually
                // clears the previous value — when recompute recovers from
                // a failure, pricedAt + pricedFailureReason must reset.
                sellingPrice:
                  event.sellingPrice !== undefined
                    ? event.sellingPrice
                    : sku.sellingPrice,
                pricedAt:
                  event.pricedAt !== undefined ? event.pricedAt : sku.pricedAt,
                pricedFailureReason:
                  event.pricedFailureReason !== undefined
                    ? event.pricedFailureReason
                    : sku.pricedFailureReason,
              }
            : sku,
        ),
      );
      // CAT-021 #1: when an SKU lands in a terminal state, drop any cached
      // queries showing it so the products list / detail / completeness
      // surfaces refetch with the fresh sellingPrice. We only invalidate on
      // terminal events (priced + failures) — intermediate `pending` events
      // are noisy and the optimistic merge above keeps the UI in sync until
      // the final state lands.
      const terminal =
        event.pricingStatus === 'priced' ||
        PRICING_FAILURE_STATUSES.includes(event.pricingStatus);
      if (terminal) {
        queryClient.invalidateQueries({
          queryKey: productKeys.detail(productId),
        });
        queryClient.invalidateQueries({ queryKey: productKeys.lists() });
      }
    },
    [productId, queryClient],
  );
  useSkuPricingEvents(productId, handlePricingEvent);

  const publishGate = useMemo(
    () => computePublishGate(pricingSkus),
    [pricingSkus],
  );

  const toast = useToast();

  // CAT-019 envelope handler — shared by both the single-step transition
  // mutation (for non-publish FSM moves) and the chained publish mutation.
  const handleStatusError = useCallback((err) => {
    if (err?.code === 'PRODUCT_NOT_READY' && err?.details?.skuDiagnostics) {
      setPublishDiagnostics(err.details.skuDiagnostics);
      setTransitionError(null);
      return;
    }
    setPublishDiagnostics(null);
    setTransitionError(err?.message ?? 'Не удалось изменить статус');
  }, []);

  const transitionMutation = useMutation({
    mutationFn: (targetStatus) => changeProductStatus(productId, targetStatus),
    onSuccess: () => {
      setPublishDiagnostics(null);
      queryClient.invalidateQueries({
        queryKey: productKeys.detail(productId),
      });
      queryClient.invalidateQueries({ queryKey: productKeys.lists() });
    },
    onError: handleStatusError,
  });

  // CAT-021 #4: chains DRAFT → ENRICHING → READY_FOR_REVIEW → PUBLISHED so
  // a single click handles the FSM ladder. Re-uses the same diagnostic
  // envelope handler so the publish-gate blocker still appears on 422.
  const publishMutation = usePublishProduct(productId);
  const publishMutate = publishMutation.mutate;

  const handleOpenBulk = useCallback((highlightId) => {
    setBulkHighlightSkuId(highlightId ?? null);
    setBulkOpen(true);
  }, []);

  const handlePublish = useCallback(() => {
    setTransitionError(null);
    setPublishDiagnostics(null);
    publishMutate(undefined, {
      onSuccess: () => {
        toast.success('Товар опубликован');
      },
      onError: (err) => {
        if (err?.code !== 'PRODUCT_NOT_READY') {
          toast.error(err?.message ?? 'Не удалось опубликовать');
        }
        handleStatusError(err);
      },
    });
  }, [publishMutate, handleStatusError, toast]);

  // CAT-021 #2: when the blocker is open and every previously-pending SKU
  // has reached `priced`, auto-retry the publish chain. Guard with a ref
  // keyed on the diagnostic snapshot so a second 422 (e.g. user changed
  // something else and pressed publish again) can re-trigger auto-retry.
  const autoRetryGuardRef = useRef(null);
  useEffect(() => {
    if (!publishDiagnostics) {
      autoRetryGuardRef.current = null;
      return;
    }
    if (publishMutation.isPending) return;
    const blockingSkuIds = publishDiagnostics
      .filter((d) => d.pricingStatus === 'pending')
      .map((d) => d.skuId);
    if (blockingSkuIds.length === 0) return;

    const allPriced = blockingSkuIds.every((skuId) => {
      const sku = pricingSkus.find((s) => s.id === skuId);
      return sku?.pricingStatus === 'priced';
    });
    if (!allPriced) return;

    // Use the diagnostics array reference as the guard key. A fresh
    // PRODUCT_NOT_READY response produces a new array, so a second cycle
    // is allowed. setPublishDiagnostics(null) on success resets the ref.
    if (autoRetryGuardRef.current === publishDiagnostics) return;
    autoRetryGuardRef.current = publishDiagnostics;
    toast.info('Цены рассчитаны, публикуем…');
    handlePublish();
  }, [
    publishDiagnostics,
    pricingSkus,
    publishMutation.isPending,
    handlePublish,
    toast,
  ]);

  const handleRetryPublish = handlePublish;

  if (productLoading && !product) {
    return <ProductDetailSkeleton />;
  }

  if (productError && !product) {
    return (
      <div className={styles.errorState}>
        <ApiErrorState
          error={productError}
          onRetry={() => refetchProduct()}
          homeHref="/admin/products"
          homeLabel="К списку товаров"
        />
      </div>
    );
  }

  // No loading, no error, but product is still missing — happens when the
  // browser returns to this page after a soft-navigation while the React
  // Query cache for `productKeys.detail(productId)` was invalidated and the
  // refetch hasn't resolved yet (race). Show a recoverable fallback with a
  // back link instead of `return null`, which would render a blank screen
  // and leave the merchandiser stranded.
  if (!product) {
    return (
      <div className={styles.errorState}>
        <ApiErrorState
          error={{ status: 404 }}
          onRetry={() => refetchProduct()}
          homeHref="/admin/products"
          homeLabel="К списку товаров"
        />
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <Link href="/admin/products" className={styles.backLink}>
          ← Товары
        </Link>
        <div className={styles.titleRow}>
          <h1 className={styles.title}>{i18n(product.titleI18N)}</h1>
          <span
            className={styles.statusBadge}
            style={(() => {
              // Audit 1.7 — FSM colour map. Inline style is the cleanest
              // path because the badge already lives in a CSS-Module
              // file and we don't want to leak Tailwind tokens through
              // a module shell. The hex pairs are WCAG-AA on white.
              const tone = PRODUCT_STATUS_TONES[product.status];
              return tone ? { background: tone.bg, color: tone.fg } : undefined;
            })()}
          >
            {PRODUCT_STATUS_LABELS[product.status] ?? product.status}
          </span>
          <span className={styles.versionTag}>v{product.version}</span>
          <Link
            href={`/admin/products/${productId}/edit`}
            className={styles.editButton}
          >
            Редактировать
          </Link>
        </div>
        <p className="text-app-muted text-sm">{product.slug}</p>
      </div>

      <div className={styles.transitionSection}>
        <StatusTransitionBar
          status={product.status}
          loading={transitionMutation.isPending || publishMutation.isPending}
          onTransition={(targetStatus) => {
            setTransitionError(null);
            // Route the "published" target through the chain mutation so a
            // click from any pre-publish status walks the FSM ladder in one
            // shot. Other transitions (back to draft, archive, etc.) keep
            // using the single-step mutation.
            if (targetStatus === 'published') {
              handlePublish();
            } else {
              transitionMutation.mutate(targetStatus);
            }
          }}
          publishGate={publishGate}
        />
        {/* Standalone publish button removed — StatusTransitionBar already
            exposes the same `published` target, and rendering both made the
            primary action ambiguous (two buttons for one operation, mixed
            visual weight + emoji vs text). The bar's `published` button
            walks the same FSM ladder via handlePublish when chained. */}
      </div>

      {transitionError && (
        <div role="alert" aria-live="polite" className={styles.errorBanner}>
          <span>{transitionError}</span>
          <button
            type="button"
            onClick={() => setTransitionError(null)}
            className="ml-2 font-medium underline"
          >
            Скрыть
          </button>
        </div>
      )}

      {(() => {
        // 422 path snapshot (after a failed publish click) takes precedence
        // — its diagnostics array is bound to the exact transition the
        // user just attempted. When no 422 has fired we fall back to the
        // live verdict from useValidatePublish. Either path renders the
        // same PublishGateBlocker, so the user has one consistent surface.
        const liveDiagnostics =
          publishDiagnostics ??
          (publishVerdict && !publishVerdict.ok
            ? publishVerdict.skuDiagnostics
            : null);
        if (!liveDiagnostics?.length) return null;
        return (
          <PublishGateBlocker
            diagnostics={liveDiagnostics}
            retrying={transitionMutation.isPending}
            onRetry={handleRetryPublish}
            onSetPurchasePrice={(skuId) => handleOpenBulk(skuId)}
          />
        );
      })()}

      {publishVerdict &&
        !publishVerdict.ok &&
        publishVerdict.skuDiagnostics.length === 0 &&
        publishVerdict.gateFailures.length > 0 && (
          <section
            role="alert"
            className="border-app-danger rounded-xl border bg-red-50/40 p-4 text-sm"
          >
            <p className="text-app-danger font-semibold">
              Публикация заблокирована
            </p>
            <ul className="text-app-text-dark mt-2 list-disc pl-5">
              {publishVerdict.gateFailures.map((g, idx) => (
                <li key={`${g.code}-${idx}`}>{g.code}</li>
              ))}
            </ul>
          </section>
        )}

      <div className={styles.content}>
        <div className={styles.mainCard}>
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Название</span>
            <span className={styles.infoValue}>{i18n(product.titleI18N)}</span>
          </div>
          {product.descriptionI18N && (
            <div className={styles.infoRow}>
              <span className={styles.infoLabel}>Описание</span>
              <span className={styles.infoValue}>
                {i18n(product.descriptionI18N)}
              </span>
            </div>
          )}
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Бренд</span>
            <span className={styles.infoValue}>
              {brand?.name ?? (
                <code className="text-app-muted text-xs">
                  {product.brandId}
                </code>
              )}
            </span>
          </div>
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Категория</span>
            <span className={styles.infoValue}>
              {categoryNode ? (
                categoryLabel(categoryNode)
              ) : (
                <code className="text-app-muted text-xs">
                  {product.primaryCategoryId}
                </code>
              )}
            </span>
          </div>
          {product.countryOfOrigin && (
            <div className={styles.infoRow}>
              <span className={styles.infoLabel}>Страна</span>
              <span className={styles.infoValue}>
                {product.countryOfOrigin}
              </span>
            </div>
          )}
          <div className={styles.infoRow}>
            <span className={styles.infoLabel}>Статус</span>
            <span className={styles.infoValue}>
              {PRODUCT_STATUS_LABELS[product.status] ?? product.status}
            </span>
          </div>
        </div>

        <div className={styles.sidebar}>
          <CompletenessPanel completeness={completeness} />
        </div>
      </div>

      <PricingSurface pricingSkus={pricingSkus} onOpenBulk={handleOpenBulk} />

      <BulkPurchasePriceModal
        open={bulkOpen}
        onClose={() => {
          setBulkOpen(false);
          setBulkHighlightSkuId(null);
        }}
        productId={productId}
        skus={pricingSkus}
        highlightSkuId={bulkHighlightSkuId}
        onApplied={() => {
          // Refresh the cached product so the next render seeds purchasePrice
          // from the fresh server snapshot. The SSE stream will deliver the
          // recompute results separately as they land.
          queryClient.invalidateQueries({
            queryKey: productKeys.detail(productId),
          });
        }}
      />
    </div>
  );
}
