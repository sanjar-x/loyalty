'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import { removeBackground, subscribeMediaStatus } from '@/entities/product';

/**
 * Resolve the bg-removed media target for an image, or null when the
 * original should be sent. Pure helper used by the submit pipeline
 * (useSubmitProduct / useUpdateProduct) — mirrors the same gate the
 * gallery thumbnail and preview card use to decide which URL to render,
 * so the asset that lands on backend matches what the merchandiser saw.
 */
export function selectBgRemovedMedia(bgRemoval, localId) {
  if (!bgRemoval || !localId) return null;
  const bgState = bgRemoval.stateByLocalId?.[localId];
  const bgVariant = bgRemoval.variantByLocalId?.[localId];
  if (
    bgState?.status === 'completed' &&
    bgVariant === 'no-background' &&
    bgState.derivedSid &&
    bgState.derivedUrl
  ) {
    return { storageObjectId: bgState.derivedSid, url: bgState.derivedUrl };
  }
  return null;
}

/**
 * Async, fire-and-forget background-removal state.
 *
 * Pre-fix the bg-removal logic lived inside <ImageViewer> — so closing
 * the modal aborted the SSE subscription and the merchandiser couldn't
 * keep working while the derivation ran. Lifting state to a hook that
 * <ImagesSection> owns lets the user kick off the removal, close the
 * editor, fill in other fields, and have the result waiting when they
 * come back. The thumbnail tracks `pending` status the same way upload
 * `processing` is rendered — a small badge, not a blocking spinner.
 *
 * Per-image state shape, keyed by `image.localId`:
 *   { status: 'idle' | 'pending' | 'completed' | 'failed',
 *     derivedSid, derivedUrl, error, code }
 *
 * Public API:
 *   requestRemoval(image, storageObjectId)   — start derivation
 *   toggleVariant(localId)                   — flip 'no-background' ↔ 'original'
 *   stateByLocalId                           — map for rendering
 *   variantByLocalId                         — map for editor toggle
 */
export function useBgRemoval() {
  const [stateByLocalId, setStateByLocalId] = useState({});
  const [variantByLocalId, setVariantByLocalId] = useState({});

  // SSE controllers keyed by localId so a new request on the same image
  // (e.g. user reopens after a failure) aborts the prior subscription
  // cleanly. Also aborted on unmount via the effect below.
  const abortRefs = useRef(new Map());

  useEffect(() => {
    const aborts = abortRefs.current;
    return () => {
      for (const controller of aborts.values()) controller.abort();
      aborts.clear();
    };
  }, []);

  const patch = useCallback((localId, next) => {
    setStateByLocalId((prev) => ({
      ...prev,
      [localId]: { ...(prev[localId] ?? {}), ...next },
    }));
  }, []);

  const requestRemoval = useCallback(
    async (image, storageObjectId) => {
      if (!image?.localId || !storageObjectId) return;
      const localId = image.localId;
      const current = stateByLocalId[localId];
      if (current?.status === 'pending') return;

      // Cancel any prior subscription for this image before starting fresh.
      const priorController = abortRefs.current.get(localId);
      if (priorController) priorController.abort();
      abortRefs.current.delete(localId);

      patch(localId, { status: 'pending', error: null, code: null });

      let response;
      try {
        response = await removeBackground(storageObjectId);
      } catch (err) {
        patch(localId, {
          status: 'failed',
          error: err?.message ?? 'Не удалось удалить фон',
          code: err?.code,
        });
        return;
      }

      const derivedSid = response.derivedStorageObjectId;
      // Idempotent backend: derivation already exists, fast-path to done.
      if (response.status === 'completed' && response.url) {
        patch(localId, {
          status: 'completed',
          derivedSid,
          derivedUrl: response.url,
          error: null,
        });
        setVariantByLocalId((prev) => ({
          ...prev,
          [localId]: 'no-background',
        }));
        return;
      }

      if (response.status === 'failed') {
        patch(localId, {
          status: 'failed',
          derivedSid,
          error:
            'Предыдущая попытка удалить фон завершилась ошибкой. Повторите.',
        });
        return;
      }

      // status === 'processing' — subscribe to the SSE stream of the
      // derived storage object until terminal state.
      const controller = new AbortController();
      abortRefs.current.set(localId, controller);
      patch(localId, { status: 'pending', derivedSid });

      try {
        const metadata = await subscribeMediaStatus(derivedSid, {
          signal: controller.signal,
        });
        abortRefs.current.delete(localId);
        patch(localId, {
          status: 'completed',
          derivedSid,
          derivedUrl: metadata?.url ?? null,
          error: null,
        });
        setVariantByLocalId((prev) => ({
          ...prev,
          [localId]: 'no-background',
        }));
      } catch (err) {
        abortRefs.current.delete(localId);
        if (err?.name === 'AbortError') return;
        patch(localId, {
          status: 'failed',
          derivedSid,
          error: err?.message ?? 'Обработка не удалась',
          code: err?.code,
        });
      }
    },
    [stateByLocalId, patch],
  );

  const toggleVariant = useCallback((localId) => {
    setVariantByLocalId((prev) => ({
      ...prev,
      [localId]:
        (prev[localId] ?? 'no-background') === 'no-background'
          ? 'original'
          : 'no-background',
    }));
  }, []);

  return {
    stateByLocalId,
    variantByLocalId,
    requestRemoval,
    toggleVariant,
  };
}
