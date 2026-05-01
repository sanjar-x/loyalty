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

function rublesToKopecks(rubles) {
  const n = parseInt(rubles, 10);
  return isNaN(n) ? null : n * 100;
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
    async (form, imageUploads = {}) => {
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
          } catch (err) {
            if (err.message?.includes('409') || err.status === 409) {
              throw new Error(
                'Товар был изменён другим пользователем. Обновите страницу и попробуйте снова.',
              );
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
          for (const sku of variant.skus ?? []) {
            // Find corresponding price in form state
            let priceAmount = null;
            let compareAtAmount = null;

            if (variant.variablePricing) {
              // Find by matching valueId in perSkuPrices
              const skuPriceEntry = Object.entries(variant.perSkuPrices).find(
                ([, p]) => p.skuId === sku.id,
              );
              if (skuPriceEntry) {
                priceAmount = rublesToKopecks(skuPriceEntry[1].price);
                compareAtAmount = rublesToKopecks(skuPriceEntry[1].compareAt);
              }
            } else {
              priceAmount = rublesToKopecks(variant.priceAmount);
              compareAtAmount = rublesToKopecks(variant.compareAtPrice);
            }

            if (priceAmount != null) {
              try {
                await updateSku(productId, variant.serverId, sku.id, {
                  priceAmount,
                  compareAtPriceAmount: compareAtAmount,
                  version: sku.version,
                });
              } catch (err) {
                if (err.message?.includes('409') || err.status === 409) {
                  throw new Error(
                    'Товар был изменён другим пользователем. Обновите страницу и попробуйте снова.',
                  );
                }
                throw err;
              }
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

        // Upload new images (those without mediaId)
        for (const variant of s.variants) {
          const variantId = variant.serverId;
          if (!variantId) continue;

          const newImages = variant.images.filter((img) => !img.fromServer);
          for (let i = 0; i < newImages.length; i++) {
            const img = newImages[i];
            const upload = imageUploads[img.localId];
            if (!upload) continue;

            setProgress(`Привязка изображения ${i + 1}/${newImages.length}...`);

            try {
              let sid = upload.storageObjectId;

              // If useImageUpload already processed this image, just associate it
              if (upload.status === 'completed' && sid) {
                const role =
                  i === 0 && variant === s.variants[0] ? 'main' : 'gallery';
                await associateMedia(productId, {
                  storageObjectId: sid,
                  url: upload.url || upload.rawUrl || undefined,
                  variantId,
                  role,
                  sortOrder: i,
                  mediaType: 'image',
                  isExternal: false,
                });
                continue;
              }

              // Fallback: upload from scratch if file is available
              if (!upload.file) continue;

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
              const mediaUrl = metadata?.url || extractRawUrl(presignedUrl);

              const role =
                i === 0 && variant === s.variants[0] ? 'main' : 'gallery';
              await associateMedia(productId, {
                storageObjectId,
                url: mediaUrl || undefined,
                variantId,
                role,
                sortOrder: i,
                mediaType: 'image',
                isExternal: false,
              });
            } catch (err) {
              console.error('Media upload failed for image:', img.localId, err);
            }
          }
        }

        setStep('done');
        setProgress(STEPS.done);

        // Refresh server state for the affected product everywhere it's used:
        // detail page, edit page (which re-hydrates the form from these queries),
        // and the products list / status counts. Nested keys (completeness,
        // media) are invalidated through prefix-match on `detail(productId)`.
        await Promise.all([
          queryClient.invalidateQueries({
            queryKey: productKeys.detail(productId),
          }),
          queryClient.invalidateQueries({ queryKey: productKeys.lists() }),
          queryClient.invalidateQueries({ queryKey: productKeys.counts() }),
        ]);

        // Surface partial failures so the UI can show a non-blocking warning.
        // Product itself is saved at this point — only cleanup of attrs/media
        // is partially incomplete.
        const partialFailures = failedAttrDeletes + failedMediaDeletes;
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
          // Component unmounted mid-flight; do not surface state.
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
