'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  createProduct,
  createVariant,
  bulkAssignAttrs,
  generateSkus,
  listSkus,
  updateSku,
  reserveMediaUpload,
  uploadToS3,
  confirmMedia,
  subscribeMediaStatus,
  fetchImageAsFile,
  associateMedia,
  changeProductStatus,
  extractRawUrl,
  productKeys,
} from '@/entities/product';
import { buildI18nPayload } from '@/shared/lib/utils';

/**
 * Submit hook for product creation.
 *
 * Orchestrates the multi-step API chain:
 * 1. Create product → productId + defaultVariantId
 * 2. Bulk assign product-level attrs (skip if null)
 * 3. For each variant: create variant (if not default) → generate SKUs → pricing → upload media
 * 4. Change status (if publish mode)
 */

const STEPS = {
  creating: 'Создание продукта...',
  attrs: 'Назначение атрибутов...',
  variants: 'Создание вариантов...',
  skus: 'Генерация SKU...',
  pricing: 'Установка цен...',
  media: 'Загрузка и обработка изображений',
  status: 'Отправка на модерацию...',
  done: 'Готово',
};

export default function useSubmitProduct() {
  const queryClient = useQueryClient();
  const [submitting, setSubmitting] = useState(false);
  const [step, setStep] = useState(null);
  const [progress, setProgress] = useState('');
  const [error, setError] = useState(null);
  const [createdProductId, setCreatedProductId] = useState(null);
  const lockRef = useRef(false);
  // Aborts long-running steps (SSE for media processing, in-flight POSTs)
  // when the host component unmounts mid-submit.
  const abortRef = useRef(null);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      abortRef.current = null;
    };
  }, []);

  const execute = useCallback(
    async (form, mode = 'draft', imageUploads = {}) => {
      if (lockRef.current) return;
      lockRef.current = true;
      setSubmitting(true);
      setError(null);
      let currentStep = 'creating';
      setStep(currentStep);
      setProgress(STEPS.creating);

      const controller = new AbortController();
      abortRef.current?.abort();
      abortRef.current = controller;
      const { signal } = controller;

      let productId = null;
      let defaultVariantId = null;

      try {
        // ── Step 1: Create product ──
        const productResult = await createProduct(form.productPayload);
        productId = productResult.id;
        defaultVariantId = productResult.defaultVariantId;
        setCreatedProductId(productId);

        // ── Step 2: Bulk assign product attrs ──
        if (form.bulkAttrsPayload) {
          currentStep = 'attrs';
          setStep(currentStep);
          setProgress(STEPS.attrs);
          await bulkAssignAttrs(productId, form.bulkAttrsPayload);
        }

        // ── Step 3: Process each variant ──
        const variants = form.state.variants;
        const variantPayloads = form.variantPayloads;
        let totalMediaFailures = 0;
        let totalMediaCount = 0;

        for (let vi = 0; vi < variants.length; vi++) {
          const v = variants[vi];
          const vp = variantPayloads[vi];

          // Skip completely empty variants (no attrs, no images, no price)
          if (vi > 0) {
            const noAttrs = !Object.values(v.variantAttrs ?? {}).some(
              (ids) => ids.length > 0,
            );
            const noImages = (v.images ?? []).length === 0;
            const noPrice = !v.priceAmount;
            if (noAttrs && noImages && noPrice) continue;
          }

          let variantId;

          // First variant uses defaultVariantId, additional ones are created
          if (vi === 0) {
            variantId = defaultVariantId;
          } else {
            currentStep = 'variants';
            setStep(currentStep);
            setProgress(`${STEPS.variants} (${vi + 1}/${variants.length})`);
            const variantResult = await createVariant(productId, {
              nameI18N: buildI18nPayload(`Вариант ${vi + 1}`),
              sortOrder: vi,
            });
            variantId = variantResult.id;
          }

          // ── Step 3a: Generate SKU matrix for this variant ──
          if (vp?.skuGeneratePayload) {
            currentStep = 'skus';
            setStep(currentStep);
            setProgress(
              variants.length > 1
                ? `${STEPS.skus} (вариант ${vi + 1}/${variants.length})`
                : STEPS.skus,
            );
            const skuResult = await generateSkus(
              productId,
              variantId,
              vp.skuGeneratePayload,
            );

            if (
              (skuResult?.createdCount ?? 0) === 0 &&
              (skuResult?.skippedCount ?? 0) === 0
            ) {
              throw Object.assign(
                new Error(
                  'SKU не были сгенерированы. Проверьте выбранные атрибуты.',
                ),
                { code: 'ZERO_SKUS' },
              );
            }

            // ── Step 3b: Variable pricing ──
            if (vp.perSkuPriceUpdates.length > 0) {
              currentStep = 'pricing';
              setStep(currentStep);
              setProgress(STEPS.pricing);

              const skuList = await listSkus(productId, variantId);
              const skus = skuList.items ?? [];

              // Parallelize independent SKU price patches
              await Promise.all(
                vp.perSkuPriceUpdates.map((priceUpdate) => {
                  const sku = skus.find((s) =>
                    (s.variantAttributes ?? []).some(
                      (va) => va.attributeValueId === priceUpdate.valueId,
                    ),
                  );
                  if (!sku) return Promise.resolve();
                  return updateSku(productId, variantId, sku.id, {
                    priceAmount: priceUpdate.priceAmount,
                    compareAtPriceAmount: priceUpdate.compareAtPriceAmount,
                  });
                }),
              );
            }
          }

          // ── Step 3c: Upload media for this variant ──
          const images = v.images ?? [];
          if (images.length > 0) {
            totalMediaCount += images.length;
            currentStep = 'media';
            setStep(currentStep);
            let uploaded = 0;
            let mediaFailures = 0;
            const totalLabel =
              variants.length > 1
                ? `${STEPS.media} (вариант ${vi + 1})`
                : STEPS.media;
            setProgress(`${totalLabel} (${uploaded}/${images.length})...`);

            const uploadTasks = images.map((image, idx) => ({
              image,
              role: idx === 0 ? 'main' : 'gallery',
              sortOrder: idx,
              preUploaded: imageUploads[image.localId],
            }));

            for (let i = 0; i < uploadTasks.length; i += 3) {
              const chunk = uploadTasks.slice(i, i + 3);
              const results = await Promise.allSettled(
                chunk.map(async ({ image, role, sortOrder, preUploaded }) => {
                  let storageObjectId = null;
                  let mediaUrl = null;

                  if (
                    preUploaded?.status === 'completed' &&
                    preUploaded.storageObjectId
                  ) {
                    storageObjectId = preUploaded.storageObjectId;
                    mediaUrl = preUploaded.url || preUploaded.rawUrl || null;
                  } else {
                    const file =
                      image.file ||
                      (image.source === 'url'
                        ? await fetchImageAsFile(image.url)
                        : null);
                    if (file) {
                      const slot = await reserveMediaUpload({
                        contentType: file.type || 'image/jpeg',
                        filename: file.name,
                      });
                      await uploadToS3(slot.presignedUrl, file);
                      await confirmMedia(slot.storageObjectId);
                      const metadata = await subscribeMediaStatus(
                        slot.storageObjectId,
                        { signal },
                      );
                      storageObjectId = slot.storageObjectId;
                      mediaUrl =
                        metadata?.url || extractRawUrl(slot.presignedUrl);
                    }
                  }

                  if (storageObjectId) {
                    await associateMedia(productId, {
                      storageObjectId,
                      url: mediaUrl || undefined,
                      variantId,
                      role,
                      sortOrder,
                      mediaType: 'image',
                      isExternal: false,
                    });
                  }
                }),
              );

              for (const r of results) {
                if (r.status === 'fulfilled') uploaded++;
              }
              setProgress(`${totalLabel} (${uploaded}/${images.length})...`);

              const failures = results.filter((r) => r.status === 'rejected');
              mediaFailures += failures.length;
            }

            if (mediaFailures > 0) {
              totalMediaFailures += mediaFailures;
            }
          }

          // ── Step 3d: Upload size guide for this variant ──
          const sizeGuide = v.sizeGuide;
          if (sizeGuide) {
            try {
              let sgStorageObjectId = null;
              let sgUrl = null;

              const sgFile =
                sizeGuide.file ||
                (sizeGuide.source === 'url'
                  ? await fetchImageAsFile(sizeGuide.url)
                  : null);
              if (sgFile) {
                const slot = await reserveMediaUpload({
                  contentType: sgFile.type || 'image/jpeg',
                  filename: sgFile.name,
                });
                await uploadToS3(slot.presignedUrl, sgFile);
                await confirmMedia(slot.storageObjectId);
                const metadata = await subscribeMediaStatus(
                  slot.storageObjectId,
                  { signal },
                );
                sgStorageObjectId = slot.storageObjectId;
                sgUrl = metadata?.url || extractRawUrl(slot.presignedUrl);
              }

              if (sgStorageObjectId) {
                await associateMedia(productId, {
                  storageObjectId: sgStorageObjectId,
                  url: sgUrl || undefined,
                  variantId,
                  role: 'size_guide',
                  sortOrder: 0,
                  mediaType: 'image',
                  isExternal: false,
                });
              }
            } catch {
              throw Object.assign(
                new Error(
                  'Не удалось загрузить размерную сетку. Продукт создан как черновик.',
                ),
                { code: 'SIZE_GUIDE_FAILED' },
              );
            }
          }
        }

        // Report accumulated media failures (non-blocking — all variants were processed)
        if (totalMediaFailures > 0) {
          throw Object.assign(
            new Error(
              `${totalMediaFailures} из ${totalMediaCount} изображений не загрузились. Продукт создан как черновик.`,
            ),
            { code: 'MEDIA_PARTIAL_FAILURE' },
          );
        }

        // ── Step 4: Change status (publish mode only) ──
        if (mode === 'publish') {
          currentStep = 'status';
          setStep(currentStep);
          setProgress(STEPS.status);

          const statusSteps = ['enriching', 'ready_for_review', 'published'];
          for (const nextStatus of statusSteps) {
            try {
              await changeProductStatus(productId, nextStatus);
            } catch (err) {
              // Single retry for transient failures
              try {
                await changeProductStatus(productId, nextStatus);
              } catch {
                throw err; // Re-throw original error on second failure
              }
            }
          }
        }

        currentStep = 'done';
        setStep(currentStep);
        setProgress(STEPS.done);

        // New product is now part of the catalogue — refresh list/counts so
        // the products page reflects it without a full reload.
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: productKeys.lists() }),
          queryClient.invalidateQueries({ queryKey: productKeys.counts() }),
        ]);

        return { productId, defaultVariantId };
      } catch (err) {
        if (signal.aborted || err?.name === 'AbortError') {
          return productId
            ? { productId, defaultVariantId, error: true }
            : null;
        }
        setError({
          step: currentStep,
          message: err.message ?? 'Неизвестная ошибка',
          code: err.code,
        });
        if (productId) return { productId, defaultVariantId, error: true };
        return null;
      } finally {
        if (abortRef.current === controller) abortRef.current = null;
        lockRef.current = false;
        setSubmitting(false);
      }
    },
    [queryClient],
  );

  const clearError = useCallback(() => setError(null), []);

  return {
    submitting,
    step,
    progress,
    error,
    createdProductId,
    execute,
    clearError,
  };
}
