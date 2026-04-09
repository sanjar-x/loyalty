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
} from '@/services/products';

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
 */
export default function useImageUpload() {
  // { [localId]: { status, storageObjectId, url, rawUrl, error } }
  const [uploads, setUploads] = useState({});
  const uploadsRef = useRef(uploads);
  uploadsRef.current = uploads;
  const inflightRef = useRef(new Set());
  const abortRefs = useRef(new Map());

  // Cleanup SSE connections on unmount
  useEffect(() => {
    return () => {
      for (const controller of abortRefs.current.values()) {
        controller.abort();
      }
      abortRefs.current.clear();
    };
  }, []);

  const update = useCallback((localId, patch) => {
    setUploads((prev) => ({
      ...prev,
      [localId]: { ...(prev[localId] ?? {}), ...patch },
    }));
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
      const prevStorageObjectId = uploadsRef.current[localId]?.storageObjectId || null;

      update(localId, { status: 'uploading', error: null, storageObjectId: null, rawUrl: null, url: null });

      try {
        let storageObjectId = null;
        let mediaUrl = null;

        const file = image.file || (image.source === 'url' ? await fetchImageAsFile(image.url) : null);

        if (file) {
          // Step 1: Reserve upload slot → presigned URL
          const slot = await reserveMediaUpload({
            contentType: file.type || 'image/jpeg',
            filename: file.name,
          });

          // Compute raw public URL from presigned URL
          const rawUrl = extractRawUrl(slot.presignedUrl);

          // Step 2: Upload file directly to S3/MinIO
          await uploadToS3(slot.presignedUrl, file);

          // After S3 upload: replace blob with raw S3 URL, switch to processing
          update(localId, {
            status: 'processing',
            storageObjectId: slot.storageObjectId,
            rawUrl,
            url: rawUrl,
          });

          // Step 3: Confirm upload → triggers worker
          await confirmMedia(slot.storageObjectId);

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

        update(localId, { status: 'completed', storageObjectId, url: mediaUrl });

        // Clean up previous image from S3 after successful crop re-upload
        if (prevStorageObjectId && prevStorageObjectId !== storageObjectId) {
          deleteMedia(prevStorageObjectId).catch(() => {});
        }
      } catch (err) {
        if (err.name === 'AbortError') return;
        // On failure, preserve rawUrl as fallback
        setUploads((prev) => {
          const current = prev[localId] ?? {};
          return {
            ...prev,
            [localId]: {
              ...current,
              status: 'failed',
              error: err.message || 'Upload failed',
              url: current.rawUrl || current.url,
            },
          };
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
      return next;
    });
  }, []);

  return { uploads, startUpload, removeUpload };
}
