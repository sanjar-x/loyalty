'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import {
  associateMedia,
  bulkAssignAttrs,
  changeProductStatus,
  confirmMedia,
  createProduct,
  createVariant,
  extractRawUrl,
  fetchImageAsFile,
  generateSkus,
  listSkus,
  reserveMediaUpload,
  subscribeMediaStatus,
  updateSku,
  uploadToS3,
  waitForAllSkusPriced,
} from '@/entities/product';

import { executeSubmit } from './submit/orchestrator.js';
import { AbortError, SUBMIT_STEP_LABELS, SubmitError } from './submit/state.js';

// Default API surface wired against entities/product. Tests / future
// orchestrator drivers can pass an alternative implementation through
// `execute(form, mode, imageUploads, { api })`.
const defaultApi = {
  createProduct,
  bulkAssignAttrs,
  createVariant,
  generateSkus,
  listSkus,
  updateSku,
  reserveMediaUpload,
  uploadToS3,
  confirmMedia,
  subscribeMediaStatus,
  fetchImageAsFile,
  extractRawUrl,
  associateMedia,
  waitForAllSkusPriced,
  changeProductStatus,
};

/**
 * Thin React glue around the submit-state-machine orchestrator. Exposes
 * the same external contract as the legacy `useSubmitProduct`:
 *
 *   { submitting, step, progress, error, createdProductId, execute,
 *     abort, clearError }
 *
 * The orchestrator + per-step modules live under `./submit/*` and are
 * unit-tested in isolation.
 */
export default function useSubmitProduct() {
  const queryClient = useQueryClient();
  const [submitting, setSubmitting] = useState(false);
  const [step, setStep] = useState(null);
  const [progress, setProgress] = useState('');
  const [error, setError] = useState(null);
  const [createdProductId, setCreatedProductId] = useState(null);

  const lockRef = useRef(false);
  const abortRef = useRef(null);
  // Mirrored synchronously alongside `setCreatedProductId` so the catch
  // block can read the latest productId without waiting for a render.
  const createdProductIdRef = useRef(null);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      abortRef.current = null;
    };
  }, []);

  const execute = useCallback(
    async (form, mode = 'draft', imageUploads = {}, overrides = {}) => {
      if (lockRef.current) return null;
      lockRef.current = true;
      setSubmitting(true);
      setError(null);
      setStep('creating');
      setProgress(SUBMIT_STEP_LABELS.creating);
      createdProductIdRef.current = null;

      const controller = new AbortController();
      abortRef.current?.abort();
      abortRef.current = controller;

      const onProductCreated = (productId) => {
        createdProductIdRef.current = productId;
        setCreatedProductId(productId);
      };

      try {
        return await executeSubmit(form, mode, imageUploads, {
          api: overrides.api ?? defaultApi,
          queryClient,
          signal: controller.signal,
          onStep: setStep,
          onProgress: setProgress,
          onProductCreated,
          // Optional: when present, the uploadMedia step swaps the
          // associated storage object for the bg-removed derivation
          // for any image the merchandiser flipped to 'no-background'.
          bgRemoval: overrides.bgRemoval ?? null,
        });
      } catch (err) {
        const productId = createdProductIdRef.current;

        if (err instanceof AbortError || err?.name === 'AbortError') {
          if (productId) {
            setError({
              step: 'unknown',
              code: 'ABORTED_AFTER_CREATE',
              message: 'Операция была отменена. Продукт сохранён как черновик.',
            });
            return { productId, defaultVariantId: null, error: true };
          }
          return null;
        }

        if (err instanceof SubmitError) {
          setError({
            step: err.step,
            code: err.code,
            message: err.message,
          });
          if (productId) {
            return { productId, defaultVariantId: null, error: true };
          }
          return null;
        }

        setError({
          step: 'unknown',
          code: err?.code ?? 'UNKNOWN',
          message: err?.message ?? 'Неизвестная ошибка',
        });
        if (productId) {
          return { productId, defaultVariantId: null, error: true };
        }
        return null;
      } finally {
        if (abortRef.current === controller) abortRef.current = null;
        lockRef.current = false;
        setSubmitting(false);
      }
    },
    [queryClient],
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const clearError = useCallback(() => setError(null), []);

  return {
    submitting,
    step,
    progress,
    error,
    createdProductId,
    execute,
    abort,
    clearError,
  };
}
