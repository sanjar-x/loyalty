'use client';

import { useCallback, useState } from 'react';
import {
  createProduct,
  bulkAssignAttrs,
  generateSkus,
  listSkus,
  updateSku,
  reserveMediaUpload,
  uploadToS3,
  confirmMedia,
  addExternalMedia,
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
  media: 'Загрузка изображений',
  status: 'Публикация...',
  done: 'Готово',
};

export default function useSubmitProduct() {
  const [submitting, setSubmitting] = useState(false);
  const [step, setStep] = useState(null);        // current STEPS key
  const [progress, setProgress] = useState('');   // human-readable progress
  const [error, setError] = useState(null);       // { step, message }
  const [createdProductId, setCreatedProductId] = useState(null);

  const execute = useCallback(async (form, mode = 'draft') => {
    if (submitting) return;
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
        await generateSkus(productId, variantId, form.skuGeneratePayload);

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
      const images = form.state.images ?? [];
      if (images.length > 0) {
        currentStep = 'media';
        setStep(currentStep);
        let uploaded = 0;
        setProgress(`${STEPS.media} (${uploaded}/${images.length})...`);

        // Build upload tasks with pre-assigned roles by array index
        // images[0] = main, rest = gallery — determined BEFORE parallel execution
        const uploadTasks = images.map((image, idx) => ({
          image,
          role: idx === 0 ? 'main' : 'gallery',
          sortOrder: idx,
        }));

        // Process in chunks of 3 concurrent
        for (let i = 0; i < uploadTasks.length; i += 3) {
          const chunk = uploadTasks.slice(i, i + 3);
          const results = await Promise.allSettled(
            chunk.map(async ({ image, role, sortOrder }) => {
              if (image.source === 'url') {
                await addExternalMedia(productId, {
                  externalUrl: image.url,
                  mediaType: 'image',
                  role,
                  sortOrder,
                });
              } else if (image.file) {
                const slot = await reserveMediaUpload(productId, {
                  mediaType: 'image',
                  role,
                  contentType: image.file.type || 'image/jpeg',
                  sortOrder,
                });
                await uploadToS3(slot.presignedUploadUrl, image.file);
                await confirmMedia(productId, slot.id);
              }
            }),
          );

          for (const r of results) {
            if (r.status === 'fulfilled') uploaded++;
          }
          setProgress(`${STEPS.media} (${uploaded}/${images.length})...`);

          const failures = results.filter((r) => r.status === 'rejected');
          if (failures.length > 0) {
            console.warn('Media upload failures:', failures.map((f) => f.reason));
          }
        }
      }

      // ── Step 5b: Upload size guide ──
      const sizeGuide = form.state.sizeGuide;
      if (sizeGuide) {
        try {
          if (sizeGuide.source === 'url') {
            await addExternalMedia(productId, {
              externalUrl: sizeGuide.url,
              mediaType: 'image',
              role: 'size_guide',
              sortOrder: 0,
            });
          } else if (sizeGuide.file) {
            const slot = await reserveMediaUpload(productId, {
              mediaType: 'image',
              role: 'size_guide',
              contentType: sizeGuide.file.type || 'image/jpeg',
              sortOrder: 0,
            });
            await uploadToS3(slot.presignedUploadUrl, sizeGuide.file);
            await confirmMedia(productId, slot.id);
          }
        } catch (err) {
          console.warn('Size guide upload failed:', err);
        }
      }

      // ── Step 6: Change status (publish mode only) ──
      if (mode === 'publish') {
        currentStep = 'status';
        setStep(currentStep);
        setProgress(STEPS.status);
        await changeProductStatus(productId, 'enriching');
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
      setSubmitting(false);
    }
  }, [submitting]);

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
