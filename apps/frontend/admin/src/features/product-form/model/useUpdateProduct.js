'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  updateProduct,
  bulkAssignAttrs,
  updateSku,
  reserveMediaUpload,
  uploadToS3,
  confirmMedia,
  subscribeMediaStatus,
  associateMedia,
  deleteMediaAsset,
  deleteProductAttribute,
  changeProductStatus,
  extractRawUrl,
  productKeys,
} from '@/entities/product';
import { buildI18nPayload } from '@/shared/lib/utils';
import { selectBgRemovedMedia } from './useBgRemoval';

/**
 * Submit hook for product editing.
 *
 * Performs diff-based PATCH — only sends changed fields.
 * Handles:
 * 1. Product-level field update (PATCH /products/{id})
 * 2. Attribute diff (bulk assign new + delete removed)
 * 3. SKU price updates
 * 4. Media diff (upload new + delete removed)
 * 5. Optional status transition
 */

const STEPS = {
  saving: 'Сохранение продукта...',
  attrs: 'Обновление атрибутов...',
  pricing: 'Обновление цен...',
  media: 'Обработка изображений...',
  status: 'Изменение статуса...',
  done: 'Готово',
};

/**
 * Audit 4.1: backend's optimistic-concurrency response is 409 today,
 * but the F-5 ETag interceptor (`apiClient`) maps a 412 Precondition
 * Failed onto `ApiError({ code: 'OPTIMISTIC_LOCK_FAILED', status: 412 })`
 * and ships a localized message — the legacy substring check
 * `err.message.includes('409')` no longer covers that case. Recognising
 * either status (and the dedicated code) keeps the user-facing
 * "запись изменилась" toast wired up once Sprint 4 turns on ETags
 * for product / variant / SKU.
 */
export function isConcurrencyConflict(err) {
  if (!err) return false;
  if (err.status === 409 || err.status === 412) return true;
  if (err.code === 'OPTIMISTIC_LOCK_FAILED') return true;
  if (typeof err.message === 'string' && err.message.includes('409')) {
    return true;
  }
  return false;
}

const CONCURRENCY_MESSAGE =
  'Товар был изменён другим пользователем. Обновите страницу и попробуйте снова.';

/**
 * Form state holds money in user-facing units; backend takes smallest units.
 * Returns either the canonical MoneySchema or `null` when the form value is
 * empty / unparseable.
 */
function toMoneyKopecks(money) {
  if (!money || money.amount == null || money.amount === '') return null;
  const amount = parseInt(money.amount, 10);
  if (Number.isNaN(amount)) return null;
  return { amount: amount * 100, currency: money.currency ?? 'RUB' };
}

export default function useUpdateProduct() {
  const queryClient = useQueryClient();
  const [submitting, setSubmitting] = useState(false);
  const [step, setStep] = useState(null);
  const [progress, setProgress] = useState('');
  const [error, setError] = useState(null);
  const lockRef = useRef(false);
  // Aborts long-running steps (SSE for media processing) on unmount.
  const abortRef = useRef(null);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      abortRef.current = null;
    };
  }, []);

  const execute = useCallback(
    async (form, imageUploads = {}, bgRemoval = null) => {
      if (lockRef.current) return;
      lockRef.current = true;
      setSubmitting(true);
      setError(null);

      const controller = new AbortController();
      abortRef.current?.abort();
      abortRef.current = controller;
      const { signal } = controller;

      const snapshot = form.state._serverSnapshot;
      if (!snapshot) {
        setError('Нет данных для обновления');
        setSubmitting(false);
        lockRef.current = false;
        return;
      }

      const productId = snapshot.productId;
      const serverProduct = snapshot.product;

      // Track whether the Step 1 PATCH already landed — controls the abort
      // message in the outer catch ("changes partially saved" vs nothing).
      let productPatchApplied = false;

      try {
        // Step 1: Product-level PATCH
        setStep('saving');
        setProgress(STEPS.saving);

        const patch = {};
        const s = form.state;

        // Compare and only send changed fields
        const newTitle = buildI18nPayload(s.titleRu, s.titleEn);
        if (
          s.titleRu !== (serverProduct.titleI18N?.ru ?? '') ||
          s.titleEn !== (serverProduct.titleI18N?.en ?? '')
        ) {
          patch.titleI18N = newTitle;
        }

        if (s.slug !== (serverProduct.slug ?? '')) {
          patch.slug = s.slug;
        }

        if (s.brandId !== serverProduct.brandId) {
          patch.brandId = s.brandId;
        }

        const newDesc = s.descriptionRu
          ? buildI18nPayload(s.descriptionRu, s.descriptionEn)
          : null;
        if (
          s.descriptionRu !== (serverProduct.descriptionI18N?.ru ?? '') ||
          s.descriptionEn !== (serverProduct.descriptionI18N?.en ?? '')
        ) {
          patch.descriptionI18N = newDesc ?? { ru: '', en: '' };
        }

        if (s.countryOfOrigin !== (serverProduct.countryOfOrigin ?? '')) {
          patch.countryOfOrigin = s.countryOfOrigin || null;
        }

        // primaryCategoryId — backend accepts it in ProductUpdateRequest
        // and recategorisation triggers attribute-template re-validation
        // on the server. Without this diff the form silently swallows the
        // operator's category change.
        if (s.categoryId && s.categoryId !== serverProduct.primaryCategoryId) {
          patch.primaryCategoryId = s.categoryId;
        }

        // supplierId — sourced from the first variant's `supplierId` (same
        // contract as create-flow productPayload in useProductForm). Backend
        // ProductUpdateRequest exposes it as a top-level field; without the
        // diff a supplier swap on an existing product is dropped.
        const formSupplierId = s.variants[0]?.supplierId ?? null;
        const serverSupplierId = serverProduct.supplierId ?? null;
        if (formSupplierId !== serverSupplierId) {
          patch.supplierId = formSupplierId;
        }

        const tagsChanged =
          JSON.stringify(s.tags) !== JSON.stringify(serverProduct.tags ?? []);
        if (tagsChanged) {
          patch.tags = s.tags;
        }

        // Include version for optimistic concurrency
        if (Object.keys(patch).length > 0) {
          patch.version = snapshot.version;
          try {
            await updateProduct(productId, patch);
            productPatchApplied = true;
          } catch (err) {
            if (isConcurrencyConflict(err)) {
              throw new Error(CONCURRENCY_MESSAGE);
            }
            throw err;
          }
        }

        // Step 2: Attributes diff
        setStep('attrs');
        setProgress(STEPS.attrs);

        const oldAttrs = {};
        for (const a of serverProduct.attributes ?? []) {
          oldAttrs[a.attributeId] = a.attributeValueId;
        }

        // Separate into: removed, changed (value differs), truly new
        const removedAttrIds = Object.keys(oldAttrs).filter(
          (attrId) => !s.productAttrs[attrId],
        );
        const changedAttrIds = Object.keys(s.productAttrs).filter(
          (attrId) =>
            s.productAttrs[attrId] &&
            oldAttrs[attrId] &&
            oldAttrs[attrId] !== s.productAttrs[attrId],
        );
        const newAttrs = Object.entries(s.productAttrs).filter(
          ([attrId, valueId]) => valueId && !oldAttrs[attrId],
        );

        // Delete removed + changed attributes (changed need re-assignment).
        // Run in parallel so a single failure doesn't strand the rest in a
        // half-applied state; aggregate the failure count for the final report.
        const toDelete = [...removedAttrIds, ...changedAttrIds];
        const attrDeleteResults = await Promise.allSettled(
          toDelete.map((attrId) => deleteProductAttribute(productId, attrId)),
        );
        const failedAttrDeletes = attrDeleteResults.filter(
          (r) => r.status === 'rejected',
        ).length;

        // Bulk assign new + changed attributes
        const toAssign = [
          ...newAttrs,
          ...changedAttrIds.map((attrId) => [attrId, s.productAttrs[attrId]]),
        ];
        if (toAssign.length > 0) {
          await bulkAssignAttrs(productId, {
            items: toAssign.map(([attributeId, attributeValueId]) => ({
              attributeId,
              attributeValueId,
            })),
          });
        }

        // Step 3: SKU price updates
        setStep('pricing');
        setProgress(STEPS.pricing);

        for (const variant of s.variants) {
          if (!variant.serverId) continue;
          // CAT-002: variant-level purchasePrice mirrors onto every SKU so the
          // pricing recompute pipeline (ADR-005) has the cost input.
          const variantPurchasePrice = toMoneyKopecks(variant.purchasePrice);

          for (const sku of variant.skus ?? []) {
            let price = null;
            let compareAtPrice = null;

            if (variant.variablePricing) {
              // Match by valueId via sku.variantAttributes — the entry
              // key in `perSkuPrices` is the attributeValueId, which is
              // the one stable handle between the form and the backend
              // SKU. The legacy `p.skuId === sku.id` lookup mis-matched
              // any SKU whose price was set after hydrate (setSkuPrice
              // doesn't populate skuId on new entries), so fresh prices
              // were silently dropped on save.
              const skuValueIds = (sku.variantAttributes ?? []).map(
                (va) => va.attributeValueId,
              );
              const matchedEntry = Object.entries(variant.perSkuPrices).find(
                ([valueId]) => skuValueIds.includes(valueId),
              );
              if (matchedEntry) {
                price = toMoneyKopecks(matchedEntry[1].price);
                compareAtPrice = toMoneyKopecks(matchedEntry[1].compareAt);
              }
            } else {
              price = toMoneyKopecks(variant.price);
              compareAtPrice = toMoneyKopecks(variant.compareAtPrice);
            }

            // Build the partial-update payload. Backend rejects compareAtPrice
            // without price; mirror that contract here by clearing
            // compareAtPrice whenever price is being cleared.
            const patch = { version: sku.version };
            if (price != null) {
              patch.price = price;
              if (compareAtPrice != null) patch.compareAtPrice = compareAtPrice;
            }
            if (variantPurchasePrice != null) {
              patch.purchasePrice = variantPurchasePrice;
            }

            // Skip if there's nothing to update (only `version` is set).
            if (Object.keys(patch).length === 1) continue;

            try {
              await updateSku(productId, variant.serverId, sku.id, patch);
            } catch (err) {
              if (isConcurrencyConflict(err)) {
                throw new Error(CONCURRENCY_MESSAGE);
              }
              throw err;
            }
          }
        }

        // Step 4: Media diff
        setStep('media');
        setProgress(STEPS.media);

        const oldMediaIds = new Set(
          (snapshot.mediaAssets ?? []).map((m) => m.id),
        );
        const currentMediaIds = new Set();

        for (const variant of s.variants) {
          for (const img of variant.images) {
            if (img.mediaId) currentMediaIds.add(img.mediaId);
          }
        }

        // Delete removed media — parallel + aggregate so one failure doesn't
        // block the rest.
        const removedMediaIds = [...oldMediaIds].filter(
          (id) => !currentMediaIds.has(id),
        );
        const mediaDeleteResults = await Promise.allSettled(
          removedMediaIds.map((mediaId) =>
            deleteMediaAsset(productId, mediaId),
          ),
        );
        const failedMediaDeletes = mediaDeleteResults.filter(
          (r) => r.status === 'rejected',
        ).length;

        // Upload new images (those without mediaId).
        // Mirror the create-flow contract from useSubmitProduct: count
        // failures and surface them at the end as MEDIA_PARTIAL_FAILURE so
        // the user sees what didn't land. A silent console.error here would
        // drop user uploads invisibly.
        let mediaUploadFailures = 0;
        let mediaUploadAttempted = 0;
        for (const variant of s.variants) {
          const variantId = variant.serverId;
          if (!variantId) continue;

          // sortOrder + role must reflect the image's slot in the full
          // gallery (fromServer + new combined), not its index among the
          // new uploads only. Without this, the first new image in a
          // variant whose first slot is still a fromServer photo would
          // be saved with sortOrder=0 and role='main' — colliding with
          // the existing main and breaking gallery order on next reload.
          const newImages = variant.images.filter((img) => !img.fromServer);
          for (let i = 0; i < newImages.length; i++) {
            const img = newImages[i];
            const upload = imageUploads[img.localId];
            if (!upload) continue;

            setProgress(`Привязка изображения ${i + 1}/${newImages.length}...`);
            mediaUploadAttempted++;

            try {
              let sid = upload.storageObjectId;
              let resolvedUrl = upload.url || upload.rawUrl || null;

              if (upload.status === 'completed' && sid) {
                // useImageUpload already processed this image — just
                // associate it. (Fallback path below handles the case
                // where the eager upload never landed.)
              } else if (upload.file) {
                const { presignedUrl, storageObjectId } =
                  await reserveMediaUpload({
                    contentType: upload.file.type || 'image/jpeg',
                    filename: upload.file.name || `image-${i}.jpg`,
                  });
                await uploadToS3(presignedUrl, upload.file);
                await confirmMedia(storageObjectId);
                const metadata = await subscribeMediaStatus(storageObjectId, {
                  timeout: 60_000,
                  signal,
                });
                sid = storageObjectId;
                resolvedUrl = metadata?.url || extractRawUrl(presignedUrl);
              } else {
                continue;
              }

              // Swap to the bg-removed derivation when the merchandiser
              // toggled this image to 'no-background' in the editor.
              // Without this swap the original would land on backend
              // even though the UI confirmed the cutout.
              const bgTarget = selectBgRemovedMedia(bgRemoval, img.localId);
              if (bgTarget) {
                sid = bgTarget.storageObjectId;
                resolvedUrl = bgTarget.url;
              }

              const slotIndex = variant.images.indexOf(img);
              const isFirstSlotInFirstVariant =
                slotIndex === 0 && variant === s.variants[0];
              const role = isFirstSlotInFirstVariant ? 'main' : 'gallery';
              await associateMedia(productId, {
                storageObjectId: sid,
                url: resolvedUrl || undefined,
                variantId,
                role,
                sortOrder: slotIndex >= 0 ? slotIndex : i,
                mediaType: 'image',
                isExternal: false,
              });
            } catch (err) {
              if (err?.name === 'AbortError' || signal.aborted) throw err;
              mediaUploadFailures++;
            }
          }
        }

        // Re-associate existing (fromServer) images when the merchandiser
        // applied bg-removal to them in this session. We delete + re-create
        // rather than PATCH because the media endpoint doesn't currently
        // accept a storageObjectId swap. Failures here are counted into
        // the same cleanup bucket as removed-media-delete misses — the
        // original asset is still live on backend, so the worst case is
        // "no-background didn't stick" rather than "image gone".
        let mediaSwapFailures = 0;
        if (bgRemoval) {
          for (const variant of s.variants) {
            const variantId = variant.serverId;
            if (!variantId) continue;
            for (const img of variant.images) {
              if (!img.fromServer || !img.mediaId) continue;
              const bgTarget = selectBgRemovedMedia(bgRemoval, img.localId);
              if (!bgTarget) continue;
              // Already applied earlier — server-side storageObjectId
              // matches the derivation, nothing to do.
              if (img.storageObjectId === bgTarget.storageObjectId) continue;
              try {
                await deleteMediaAsset(productId, img.mediaId);
                await associateMedia(productId, {
                  storageObjectId: bgTarget.storageObjectId,
                  url: bgTarget.url || undefined,
                  variantId,
                  role: img.role ?? 'gallery',
                  sortOrder: img.sortOrder ?? 0,
                  mediaType: 'image',
                  isExternal: false,
                });
              } catch (err) {
                if (err?.name === 'AbortError' || signal.aborted) throw err;
                mediaSwapFailures += 1;
              }
            }
          }
        }

        setStep('done');
        setProgress(STEPS.done);

        // Refresh server state for the affected product everywhere it's used:
        // detail page, edit page (which re-hydrates the form from these queries),
        // and the products list. Nested keys (completeness, media) are
        // invalidated through prefix-match on `detail(productId)`.
        await Promise.all([
          queryClient.invalidateQueries({
            queryKey: productKeys.detail(productId),
          }),
          queryClient.invalidateQueries({ queryKey: productKeys.lists() }),
        ]);

        // Surface media upload failures separately — these mean *new* images
        // didn't land on the product, which is a different user-facing outcome
        // than failed cleanup of removed items.
        if (mediaUploadFailures > 0) {
          throw Object.assign(
            new Error(
              `Сохранено, но ${mediaUploadFailures} из ${mediaUploadAttempted} новых изображений не загрузились. Откройте товар повторно и попробуйте снова.`,
            ),
            { code: 'MEDIA_PARTIAL_FAILURE' },
          );
        }

        // Surface cleanup failures (failed deletes of old attrs/media) +
        // bg-removal re-association failures so the UI can show a non-blocking
        // warning. Product itself is saved at this point — only cleanup /
        // bg-swap of stale items is partially incomplete.
        const partialFailures =
          failedAttrDeletes + failedMediaDeletes + mediaSwapFailures;
        if (partialFailures > 0) {
          throw Object.assign(
            new Error(
              `Сохранено, но ${partialFailures} элемент${
                partialFailures === 1 ? '' : 'ов'
              } не удалось очистить. Перезагрузите страницу.`,
            ),
            { code: 'PARTIAL_CLEANUP_FAILURE' },
          );
        }

        return productId;
      } catch (err) {
        if (signal.aborted || err?.name === 'AbortError') {
          // Step 1 (product PATCH) may already have landed before the abort.
          // Surface that explicitly so the user understands why we bounced
          // out — silent return left them staring at a frozen save button.
          if (productPatchApplied) {
            setError(
              'Операция отменена. Часть изменений уже сохранена — обновите страницу, чтобы увидеть актуальное состояние.',
            );
          }
          return;
        }
        const msg = err.message || 'Не удалось сохранить изменения';
        setError(msg);
        throw err;
      } finally {
        if (abortRef.current === controller) abortRef.current = null;
        setSubmitting(false);
        lockRef.current = false;
      }
    },
    [queryClient],
  );

  return { submitting, step, progress, error, setError, execute };
}
