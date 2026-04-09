'use client';

import { useCallback, useRef, useState } from 'react';
import {
  createProduct,
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
} from '@/services/products';

/**
 * Submit hook for product creation.
 *
 * Orchestrates the multi-step API chain:
 * 1. Create product → productId + defaultVariantId
 * 2. Bulk assign product-level attrs (skip if null)
 * 3. Generate SKU matrix (skip if null)
 * 4. Variable pricing: list SKUs → map → PATCH each
 * 5. Upload media (parallel, 3 concurrent)
 * 6. Change status (if publish mode)
 *
 * Usage:
 *   const submit = useSubmitProduct();
 *   <button onClick={() => submit.execute(form, 'publish')} disabled={submit.submitting}>
 */

const STEPS = {
  creating: 'Создание продукта...',
  attrs: 'Назначение атрибутов...',
  skus: 'Генерация SKU...',
  pricing: 'Установка цен...',
  media: 'Загрузка и обработка изображений',
  status: 'Отправка на модерацию...',
  done: 'Готово',
};

export default function useSubmitProduct() {
  const [submitting, setSubmitting] = useState(false);
  const [step, setStep] = useState(null);        // current STEPS key
  const [progress, setProgress] = useState('');   // human-readable progress
  const [error, setError] = useState(null);       // { step, message }
  const [createdProductId, setCreatedProductId] = useState(null);
  const lockRef = useRef(false);

  const execute = useCallback(async (form, mode = 'draft', imageUploads = {}) => {
    if (lockRef.current) return;
    lockRef.current = true;
    setSubmitting(true);
    setError(null);
    let currentStep = 'creating';
    setStep(currentStep);
    setProgress(STEPS.creating);

    let productId = null;
    let variantId = null;

    try {
      // ── Step 1: Create product ──
      const productResult = await createProduct(form.productPayload);
      productId = productResult.id;
      variantId = productResult.defaultVariantId;
      setCreatedProductId(productId);

      // ── Step 2: Bulk assign product attrs ──
      if (form.bulkAttrsPayload) {
        currentStep = 'attrs';
        setStep(currentStep);
        setProgress(STEPS.attrs);
        await bulkAssignAttrs(productId, form.bulkAttrsPayload);
      }

      // ── Step 3: Generate SKU matrix ──
      if (form.skuGeneratePayload) {
        currentStep = 'skus';
        setStep(currentStep);
        setProgress(STEPS.skus);
        const skuResult = await generateSkus(productId, variantId, form.skuGeneratePayload);

        // Validate SKUs were actually generated
        if ((skuResult?.createdCount ?? 0) === 0 && (skuResult?.skippedCount ?? 0) === 0) {
          throw Object.assign(
            new Error('SKU не были сгенерированы. Проверьте выбранные атрибуты.'),
            { code: 'ZERO_SKUS' },
          );
        }

        // ── Step 4: Variable pricing ──
        if (form.perSkuPriceUpdates.length > 0) {
          currentStep = 'pricing';
          setStep(currentStep);
          setProgress(STEPS.pricing);

          // Get SKUs to map valueId → skuId
          const skuList = await listSkus(productId, variantId);
          const skus = skuList.items ?? [];

          for (const priceUpdate of form.perSkuPriceUpdates) {
            // Find SKU that has this valueId in its variantAttributes
            const sku = skus.find((s) =>
              (s.variantAttributes ?? []).some(
                (va) => va.attributeValueId === priceUpdate.valueId,
              ),
            );
            if (sku) {
              await updateSku(productId, variantId, sku.id, {
                priceAmount: priceUpdate.priceAmount,
                compareAtPriceAmount: priceUpdate.compareAtPriceAmount,
              });
            }
          }
        }
      }

      // ── Step 5: Upload media ──
      // Uses pre-uploaded storageObjectIds from useImageUpload when available,
      // falls back to full upload (reserve → S3 → confirm → poll) otherwise.
      const images = form.state.images ?? [];
      if (images.length > 0) {
        currentStep = 'media';
        setStep(currentStep);
        let uploaded = 0;
        let mediaFailures = 0;
        setProgress(`${STEPS.media} (${uploaded}/${images.length})...`);

        // Build upload tasks with pre-assigned roles by array index
        // images[0] = main, rest = gallery — determined BEFORE parallel execution
        const uploadTasks = images.map((image, idx) => ({
          image,
          role: idx === 0 ? 'main' : 'gallery',
          sortOrder: idx,
          preUploaded: imageUploads[image.localId],
        }));

        // Process in chunks of 3 concurrent
        for (let i = 0; i < uploadTasks.length; i += 3) {
          const chunk = uploadTasks.slice(i, i + 3);
          const results = await Promise.allSettled(
            chunk.map(async ({ image, role, sortOrder, preUploaded }) => {
              let storageObjectId = null;

              // Use pre-uploaded storageObjectId if available
              if (preUploaded?.status === 'completed' && preUploaded.storageObjectId) {
                storageObjectId = preUploaded.storageObjectId;
              } else {
                const file = image.file || (image.source === 'url' ? await fetchImageAsFile(image.url) : null);
                if (file) {
                  const slot = await reserveMediaUpload({
                    contentType: file.type || 'image/jpeg',
                    filename: file.name,
                  });
                  await uploadToS3(slot.presignedUrl, file);
                  await confirmMedia(slot.storageObjectId);
                  await subscribeMediaStatus(slot.storageObjectId);
                  storageObjectId = slot.storageObjectId;
                }
              }

              if (storageObjectId) {
                await associateMedia(productId, {
                  storageObjectId,
                  variantId,
                  role,
                  sortOrder,
                  mediaType: 'image',
                });
              }
            }),
          );

          for (const r of results) {
            if (r.status === 'fulfilled') uploaded++;
          }
          setProgress(`${STEPS.media} (${uploaded}/${images.length})...`);

          const failures = results.filter((r) => r.status === 'rejected');
          mediaFailures += failures.length;
        }

        if (mediaFailures > 0) {
          throw Object.assign(
            new Error(
              `${mediaFailures} из ${images.length} изображений не загрузились. Продукт создан как черновик.`,
            ),
            { code: 'MEDIA_PARTIAL_FAILURE' },
          );
        }
      }

      // ── Step 5b: Upload size guide ──
      const sizeGuide = form.state.sizeGuide;
      if (sizeGuide) {
        try {
          let sgStorageObjectId = null;

          const sgFile = sizeGuide.file || (sizeGuide.source === 'url' ? await fetchImageAsFile(sizeGuide.url) : null);
          if (sgFile) {
            const slot = await reserveMediaUpload({
              contentType: sgFile.type || 'image/jpeg',
              filename: sgFile.name,
            });
            await uploadToS3(slot.presignedUrl, sgFile);
            await confirmMedia(slot.storageObjectId);
            await subscribeMediaStatus(slot.storageObjectId);
            sgStorageObjectId = slot.storageObjectId;
          }

          if (sgStorageObjectId) {
            await associateMedia(productId, {
              storageObjectId: sgStorageObjectId,
              variantId,
              role: 'size_guide',
              sortOrder: 0,
              mediaType: 'image',
            });
          }
        } catch (err) {
          throw Object.assign(
            new Error('Не удалось загрузить размерную сетку. Продукт создан как черновик.'),
            { code: 'SIZE_GUIDE_FAILED' },
          );
        }
      }

      // ── Step 6: Change status (publish mode only) ──
      // FSM: draft → enriching → ready_for_review → published
      if (mode === 'publish') {
        currentStep = 'status';
        setStep(currentStep);
        setProgress(STEPS.status);
        await changeProductStatus(productId, 'enriching');
        await changeProductStatus(productId, 'ready_for_review');
        await changeProductStatus(productId, 'published');
      }

      currentStep = 'done';
      setStep(currentStep);
      setProgress(STEPS.done);

      return { productId, variantId };
    } catch (err) {
      setError({
        step: currentStep,
        message: err.message ?? 'Неизвестная ошибка',
        code: err.code,
      });
      if (productId) return { productId, variantId, error: true };
      return null;
    } finally {
      lockRef.current = false;
      setSubmitting(false);
    }
  }, []);

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
