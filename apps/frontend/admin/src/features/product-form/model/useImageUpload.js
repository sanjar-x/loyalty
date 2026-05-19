'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  reserveMediaUpload,
  uploadToS3,
  confirmMedia,
  subscribeMediaStatus,
  extractRawUrl,
  fetchImageAsFile,
  deleteMedia,
} from '@/entities/product';

/**
 * Eagerly uploads images to ImageBackend as they are added to the form.
 *
 * Flow per image:
 * - file:  reserveMediaUpload → uploadToS3 → confirmMedia → SSE (subscribeMediaStatus)
 * - url:   fetchImageAsFile (via BFF proxy) → same as file flow
 *
 * Returns storageObjectId per image for later association with product.
 *
 * Statuses: uploading → processing → completed | failed
 *
 * ──────────────────────────────────────────────────────────────────────
 * Smart re-upload audit — verified 2026-05-09 (F-2.3).
 *
 * Scenario A (happy path — crop → re-upload):
 *   1. addImage → startUpload (#1), storageObjectId = A, status = completed
 *   2. user crops → startUpload (#2) re-enters with the same localId
 *      - inflightRef gate is empty (#1 already completed); no abort
 *      - prevStorageObjectId = A captured from uploadsRef BEFORE the
 *        `update({ storageObjectId: null })` wipe
 *      - reserve / S3 / confirm / SSE → storageObjectId = B
 *      - terminal `update({ status: 'completed', storageObjectId: B })`
 *      - cleanup branch: prev (A) !== current (B) → fire-and-forget
 *        deleteMedia(A) so the orphan vanishes from ImageBackend
 *   ✅ A removed, B associated locally; user submits → associateMedia(B).
 *
 * Scenario B (browser crash mid-confirm of the cropped re-upload):
 *   1. A confirmed.
 *   2. crop → startUpload(#2): reserve / S3-upload (B uploaded), then
 *      browser tab crashes BEFORE confirmMedia(B) lands.
 *   3. On reload the form has no useImageUpload state (the hook is
 *      not persisted) so the previously displayed A is shown again
 *      (or the user re-uploads from scratch).
 *   4. B sits in S3 as PENDING_UPLOAD → backend `cleanup_orphans` cron
 *      (every 6h) reaps it within 24h.
 *   ✅ Acceptable degraded state — no client work needed.
 *
 * Scenario C (abort via removeUpload during the cropped re-upload):
 *   1. A confirmed.
 *   2. crop → startUpload(#2): reserve B, S3 OK, processing, SSE open.
 *   3. user clicks the close button → removeUpload(localId):
 *      - abort the SSE controller (B's processing watcher tears down)
 *      - read uploadsRef[localId].storageObjectId — at this point the
 *        ref already carries B (the `update({ storageObjectId: B })`
 *        in step "After S3 upload" landed before the SSE await), so
 *        deleteMedia(B) fires.
 *      - the local entry is dropped from the uploads map.
 *   4. A is NOT explicitly deleted by removeUpload. In CREATE mode A
 *      was never associated with a product, so it falls back to the
 *      `cleanup_orphans` cron. In EDIT mode A is a server-known
 *      media_asset (`mediaId` set), and `useUpdateProduct`'s media-
 *      diff phase deletes the old asset via DELETE /media/{id} on the
 *      next save. Either way no orphan accumulates server-side.
 *   ✅ Verified: removeUpload kills B, A is reclaimed by
 *      cleanup_orphans (create) or media-diff (edit). No additional
 *      mitigation needed in this hook.
 *
 * Tests: features/product-form/model/__tests__/useImageUpload.test.jsx
 * lock the cleanup branch (Scenario A) so a regression that drops the
 * `prevStorageObjectId !== storageObjectId` guard would be caught
 * before reaching ImageBackend.
 */
export default function useImageUpload() {
  // { [localId]: { status, storageObjectId, url, rawUrl, error } }
  const [uploads, setUploads] = useState({});
  // Authoritative source for cleanup paths — must be updated synchronously
  // alongside setUploads so back-to-back operations (e.g. crop → re-upload)
  // see the latest storageObjectId without waiting for a render cycle.
  const uploadsRef = useRef(uploads);
  const inflightRef = useRef(new Set());
  const abortRefs = useRef(new Map());

  // Cleanup SSE connections on unmount.
  // Snapshot the ref so the cleanup uses the same map that was active on mount,
  // which is the safe pattern recommended by the react-hooks lint.
  useEffect(() => {
    const aborts = abortRefs.current;
    return () => {
      for (const controller of aborts.values()) {
        controller.abort();
      }
      aborts.clear();
    };
  }, []);

  const update = useCallback((localId, patch) => {
    setUploads((prev) => {
      const next = {
        ...prev,
        [localId]: { ...(prev[localId] ?? {}), ...patch },
      };
      uploadsRef.current = next;
      return next;
    });
  }, []);

  const startUpload = useCallback(
    async (image) => {
      const { localId } = image;

      // Abort any existing upload for this image (e.g., after crop re-upload)
      if (inflightRef.current.has(localId)) {
        const controller = abortRefs.current.get(localId);
        if (controller) {
          controller.abort();
          abortRefs.current.delete(localId);
        }
        inflightRef.current.delete(localId);
      }

      // Check network connectivity
      if (typeof navigator !== 'undefined' && !navigator.onLine) {
        update(localId, {
          status: 'failed',
          error: 'Нет подключения к интернету',
        });
        return;
      }

      inflightRef.current.add(localId);

      // Track previous storageObjectId for cleanup after crop re-upload
      const prevStorageObjectId =
        uploadsRef.current[localId]?.storageObjectId || null;

      update(localId, {
        status: 'uploading',
        error: null,
        storageObjectId: null,
        rawUrl: null,
        url: null,
        progress: 0,
      });

      try {
        let storageObjectId = null;
        let mediaUrl = null;

        const file =
          image.file ||
          (image.source === 'url' ? await fetchImageAsFile(image.url) : null);

        if (file) {
          // Step 1: Reserve upload slot → presigned URL (~10% of progress)
          update(localId, { progress: 10 });
          const slot = await reserveMediaUpload({
            contentType: file.type || 'image/jpeg',
            filename: file.name,
          });

          const rawUrl = extractRawUrl(slot.presignedUrl);

          // Step 2: Upload file directly to S3/MinIO (~10-80% of progress)
          update(localId, { progress: 20 });
          await uploadToS3(slot.presignedUrl, file);
          update(localId, { progress: 80 });

          // After S3 upload: replace blob with raw S3 URL, switch to processing
          update(localId, {
            status: 'processing',
            storageObjectId: slot.storageObjectId,
            rawUrl,
            url: rawUrl,
            progress: 85,
          });

          // Step 3: Confirm upload → triggers worker
          await confirmMedia(slot.storageObjectId);
          update(localId, { progress: 90 });

          // Step 4: SSE — wait for processing to complete
          const controller = new AbortController();
          abortRefs.current.set(localId, controller);

          const metadata = await subscribeMediaStatus(slot.storageObjectId, {
            timeout: 120_000,
            signal: controller.signal,
          });

          abortRefs.current.delete(localId);
          storageObjectId = slot.storageObjectId;
          mediaUrl = metadata.url;
        }

        update(localId, {
          status: 'completed',
          storageObjectId,
          url: mediaUrl,
          progress: 100,
        });

        // Clean up previous image from S3 after successful crop re-upload
        if (prevStorageObjectId && prevStorageObjectId !== storageObjectId) {
          deleteMedia(prevStorageObjectId).catch(() => {});
        }
      } catch (err) {
        if (err.name === 'AbortError') return;
        // On failure, preserve rawUrl as fallback
        setUploads((prev) => {
          const current = prev[localId] ?? {};
          const next = {
            ...prev,
            [localId]: {
              ...current,
              status: 'failed',
              error: err.message || 'Ошибка загрузки',
              url: current.rawUrl || current.url,
            },
          };
          uploadsRef.current = next;
          return next;
        });
      } finally {
        inflightRef.current.delete(localId);
        abortRefs.current.delete(localId);
      }
    },
    [update],
  );

  const removeUpload = useCallback((localId) => {
    // Abort any in-flight SSE for this image
    const controller = abortRefs.current.get(localId);
    if (controller) {
      controller.abort();
      abortRefs.current.delete(localId);
    }
    // Clean up from S3
    const sid = uploadsRef.current[localId]?.storageObjectId;
    if (sid) {
      deleteMedia(sid).catch(() => {});
    }
    setUploads((prev) => {
      const next = { ...prev };
      delete next[localId];
      uploadsRef.current = next;
      return next;
    });
  }, []);

  return { uploads, startUpload, removeUpload };
}
