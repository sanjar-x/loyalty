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
    setStep('creating');
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
        setStep('attrs');
        setProgress(STEPS.attrs);
        await bulkAssignAttrs(productId, form.bulkAttrsPayload);
      }

      // ── Step 3: Generate SKU matrix ──
      if (form.skuGeneratePayload) {
        setStep('skus');
        setProgress(STEPS.skus);
        await generateSkus(productId, variantId, form.skuGeneratePayload);

        // ── Step 4: Variable pricing ──
        if (form.perSkuPriceUpdates.length > 0) {
          setStep('pricing');
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
        setStep('media');
        let uploaded = 0;
        setProgress(`${STEPS.media} (${uploaded}/${images.length})...`);

        // Process images with max 3 concurrent
        const chunks = [];
        for (let i = 0; i < images.length; i += 3) {
          chunks.push(images.slice(i, i + 3));
        }

        for (const chunk of chunks) {
          const results = await Promise.allSettled(
            chunk.map(async (image) => {
              if (image.source === 'url') {
                // External URL → POST /media/external
                await addExternalMedia(productId, {
                  externalUrl: image.url,
                  mediaType: 'image',
                  role: uploaded === 0 ? 'main' : 'gallery',
                  sortOrder: uploaded,
                });
              } else if (image.file) {
                // File upload → 3-step presigned URL flow
                const slot = await reserveMediaUpload(productId, {
                  mediaType: 'image',
                  role: uploaded === 0 ? 'main' : 'gallery',
                  contentType: image.file.type || 'image/jpeg',
                  sortOrder: uploaded,
                });
                await uploadToS3(slot.presignedUploadUrl, image.file);
                await confirmMedia(productId, slot.id);
              }
            }),
          );

          // Count successes
          for (const r of results) {
            if (r.status === 'fulfilled') uploaded++;
          }
          setProgress(`${STEPS.media} (${uploaded}/${images.length})...`);

          // Log failures but don't stop
          const failures = results.filter((r) => r.status === 'rejected');
          if (failures.length > 0) {
            console.warn('Media upload failures:', failures.map((f) => f.reason));
          }
        }
      }

      // ── Step 6: Change status (publish mode only) ──
      if (mode === 'publish') {
        setStep('status');
        setProgress(STEPS.status);
        await changeProductStatus(productId, 'enriching');
      }

      setStep('done');
      setProgress(STEPS.done);

      return { productId, variantId };
    } catch (err) {
      setError({
        step: step,
        message: err.message ?? 'Неизвестная ошибка',
        code: err.code,
      });
      // Return partial result if product was created
      if (productId) return { productId, variantId, error: true };
      return null;
    } finally {
      setSubmitting(false);
    }
  }, [submitting, step]);

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
